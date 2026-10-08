"""End-to-end pipeline: extract -> internship ML -> company -> contact -> aggregate -> explain.

The existing ML model (inference.predict) is used unchanged. Company and contact
layers are independent and can only *adjust* the final score within documented rules.
"""
import config
from company_utils import (JOB_BOARDS, URL_SHORTENERS, email_domain, extract_company, extract_emails,
                           extract_urls, get_domain, is_free_email_domain, normalize_url,
                           registrable_domain, validate_email)
from company_investigation import InvestigationInput, guess_job_title, investigate
from company_providers import KnownCompanyProvider
from company_verification import make_signal, verify_company
import logging

log = logging.getLogger("internshield.pipeline")

HIGH_RISK_KEYS = {"fee_flag", "high_amount_flag"}


def analyze_internship(text, **kw):
    """Run the existing ML pipeline. Returns dict(label, probability, score, confidence, indicators, raw)."""
    from inference import predict
    raw = predict(text, **kw)
    score = float(raw["risk_score"])
    return {
        "label": config.risk_level(score), "probability": round(score / 100, 3), "score": round(score, 1),
        "confidence": round(max(30, min(90, abs(float(raw["raw_ml_score"]) - 50) * 2 + 30))),
        "indicators": raw["indicators"], "vectors": raw["vectors"], "raw": raw,
    }


def analyze_contact(company, email=None, job_url=None, text_features=None, extra_emails=None):
    """Analyse recruiter email / job URL against the verified company. Returns dict with
    email, domain, risk_score, confidence, domain_match, provider_type, impersonation, signals."""
    sigs, risk, conf = [], 20.0, 15.0
    edom = email_domain(email) if email else ""
    out = {"email": email or None, "domain": edom or None, "domain_match": "unknown", "provider_type": None,
           "impersonation": False}
    official = company.get("official_domain")
    if email:
        free = is_free_email_domain(edom)
        out["provider_type"] = "Free/personal provider" if free else "Custom/corporate domain"
        conf += 25
        if free:
            risk += 25
            sigs.append(make_signal("free_email_used", True, "low",
                                    "Recruiter email uses a free provider (Gmail/Yahoo etc.)."))
        if official:
            if registrable_domain(edom) == registrable_domain(official):
                out["domain_match"] = "official_domain_match"; risk -= 15; conf += 20
                sigs.append(make_signal("official_domain_match", True, "positive",
                                        "Recruiter email domain matches the company domain."))
            else:
                out["domain_match"] = "free_email_provider" if free else "domain_mismatch"
                risk += 15 if free else 35; conf += 15
                sigs.append(make_signal("domain_mismatch", True, "high" if company.get("impersonation_suspected") else "medium",
                                        f"Email domain ({edom}) differs from company domain ({official})."))
        elif not free:
            sigs.append(make_signal("email_domain_unverified", True, "info",
                                    "Corporate-style email domain could not be compared with a known company domain."))
    else:
        sigs.append(make_signal("email_missing", True, "info", "No recruiter email was provided or found."))
        risk = 30
    if company.get("impersonation_suspected"):
        out["impersonation"] = True; risk = max(risk, 85)
        sigs.append(make_signal("possible_company_impersonation", True, "high",
                                "Possible company impersonation: well-known name with unrelated contact details."))
    if job_url:
        host = get_domain(job_url); reg = registrable_domain(host)
        if reg in URL_SHORTENERS:
            risk += 15; sigs.append(make_signal("shortened_job_url", True, "medium", "Job link uses a URL shortener that hides the destination."))
        elif reg in JOB_BOARDS:
            sigs.append(make_signal("job_board_url", True, "info", f"Listing is hosted on a job board ({reg})."))
        elif official and reg == registrable_domain(official):
            risk -= 5; conf += 10; sigs.append(make_signal("job_url_matches_company", True, "positive", "Job link is on the company's domain."))
        elif official:
            risk += 10; sigs.append(make_signal("job_url_mismatch", True, "low", f"Job link domain ({reg}) differs from company domain."))
    tf = text_features or {}
    if tf.get("whatsapp_flag"):
        risk += 12; sigs.append(make_signal("messaging_app_contact", True, "low", "Listing asks to contact via WhatsApp rather than a formal channel."))
    out.update(risk_score=round(max(0, min(100, risk))), confidence=round(max(0, min(100, conf))), signals=sigs)
    return out


def calculate_overall_risk(internship, company, contact, weights=None):
    """Confidence-weighted aggregation. Returns dict(risk_score, risk_level, confidence, weights_used, notes).

    Company/contact weights are scaled by their confidence (floor MIN_CONFIDENCE_INFLUENCE) so thin evidence
    has little pull. Strong ML evidence cannot be diluted by a legitimate company, and detected impersonation
    sets a minimum score.
    """
    w = weights or {"i": config.INTERNSHIP_WEIGHT, "c": config.COMPANY_WEIGHT, "k": config.CONTACT_WEIGHT}
    floor = config.MIN_CONFIDENCE_INFLUENCE
    scale = lambda conf: max(floor, conf / 100.0)
    wi = w["i"]
    wc = w["c"] * scale(company["confidence"]) if company.get("verification_ran", True) else 0.0
    wk = w["k"] * scale(contact["confidence"])
    total = wi + wc + wk or 1.0
    score = (wi * internship["score"] + wc * company["risk_score"] + wk * contact["risk_score"]) / total
    notes = []
    if internship["score"] >= config.STRONG_EVIDENCE_THRESHOLD:
        floor_score = internship["score"] - config.STRONG_EVIDENCE_MAX_DISCOUNT
        if score < floor_score:
            score = floor_score; notes.append("strong_content_evidence_floor")
    if company.get("impersonation_suspected") or contact.get("impersonation"):
        if score < config.IMPERSONATION_MIN_OVERALL:
            score = config.IMPERSONATION_MIN_OVERALL; notes.append("impersonation_floor")
    high_layers = sum(x >= 60 for x in (internship["score"], company["risk_score"] if wc else 0, contact["risk_score"]))
    if high_layers >= 2:
        score += 5; notes.append("multiple_independent_warnings")
    score = max(0, min(100, score))
    conf = (wi * internship["confidence"] + wc * company["confidence"] + wk * contact["confidence"]) / total
    return {"risk_score": round(score), "risk_level": config.risk_level(score), "confidence": round(conf),
            "weights_used": {"internship": round(wi / total, 2), "company": round(wc / total, 2), "contact": round(wk / total, 2)},
            "notes": notes}


def generate_explanation(internship, company, contact, overall):
    """Build human-readable positive / warning / high-risk groups plus a headline summary."""
    pos, warn, high = [], [], []
    for it in internship["indicators"]:
        item = {"title": it["title"], "detail": "The description contains patterns commonly associated with suspicious internship listings."}
        if it["key"] in HIGH_RISK_KEYS:
            item["title"] = "Payment requested" if it["key"] == "fee_flag" else it["title"]
            high.append(item)
        else:
            item["detail"] = it["explanation"]; warn.append(item)
    if internship["score"] < 20 and not internship["indicators"]:
        pos.append({"title": "Listing text looks typical", "detail": "No common scam patterns were detected in the description."})
    seen = set()
    for grp, bucket in (("positive_evidence", pos), ("warning_signals", warn), ("high_risk_signals", high)):
        for e in company.get(grp, []):
            if e["title"] not in seen:
                seen.add(e["title"]); bucket.append(e)
    for s in contact["signals"]:
        if s["name"] in seen or s["name"].replace("_", " ").capitalize() in seen:
            continue
        seen.add(s["name"])
        e = {"title": s["name"].replace("_", " ").capitalize(), "detail": s["explanation"]}
        {"positive": pos, "low": warn, "medium": warn, "high": high}.get(s["severity"], []).append(e)
    if "multiple_independent_warnings" in overall["notes"]:
        high.append({"title": "Multiple independent warning signals", "detail": "Content, company and contact checks each raised concerns."})
    return {"positive": pos, "warnings": warn, "high_risk": high, "summary": _summary(internship, company, contact)}


def _summary(internship, company, contact):
    st, ilvl = company["status"], internship["label"]
    if company.get("impersonation_suspected") or contact.get("impersonation"):
        return ("Possible company impersonation: the company name looks well-known but the contact details do not match it. "
                "This does not mean the real company is involved in fraud.")
    if st == "VERIFIED" and ilvl in ("HIGH RISK", "VERY HIGH RISK", "SUSPICIOUS"):
        return "The company appears legitimate, but this specific internship listing contains multiple warning signals."
    if st in ("UNVERIFIED", "UNAVAILABLE") and ilvl in ("LOW RISK", "CAUTION"):
        return ("There is currently insufficient public evidence to verify the company. "
                "This does not by itself mean the internship is fraudulent.")
    if st == "VERIFIED" and ilvl == "LOW RISK":
        return "Both the company and the listing look consistent with a legitimate opportunity, based on available evidence."
    return "Review the evidence below and verify the opportunity through official channels before sharing personal data or money."


def _run_investigation(company, email, website, job_url, recruiter_name, recruiter_linkedin, job_title, text, toolkit, online, use_cache):
    """Run the live investigation; never raises (returns None on failure)."""
    if not company:
        return None
    try:
        return investigate(InvestigationInput(company, website, recruiter_name, email, recruiter_linkedin, job_url,
                                              job_title or guess_job_title(text)), toolkit, online, use_cache)
    except Exception as e:
        log.warning("investigation failed: %s", type(e).__name__)
        return None


def _merge_investigation(company, contact, inv):
    """Fold the investigation into the existing company/contact layers (company != recruiter/job)."""
    if not inv:
        return
    ident = inv["identity"]
    if ident.get("official_domain"):
        company["official_domain"], company["official_website"] = ident["official_domain"], ident["official_website"]
    if inv["flags"]["company_verified"]:
        auth = inv["scores"]["company_authenticity"]
        company.update(risk_score=round(100 - auth), risk_level=config.risk_level(100 - auth), confidence=ident["confidence"],
                       status="VERIFIED" if (inv["live"] and auth >= 80) else "PARTIALLY VERIFIED", company_found=True,
                       impersonation_suspected=False, verification_ran=True)
        company["signals"] = [x for x in company["signals"] if x["name"] != "possible_company_impersonation"]
        company["high_risk_signals"] = [x for x in company["high_risk_signals"] if "impersonation" not in x["title"].lower()]
    if inv["flags"]["possible_impersonation"] and inv["flags"]["company_verified"]:
        contact["impersonation"] = True
        contact["risk_score"] = max(contact["risk_score"], 85)
        contact["signals"].append(make_signal("possible_company_impersonation", True, "high",
                                              "Possible company impersonation (see verification details)."))
    if inv["flags"]["lookalike_domain"]:
        contact["risk_score"] = max(contact["risk_score"], 80)
        contact["signals"].append(make_signal("lookalike_domain", True, "high", "A supplied domain closely resembles the official domain but is not official."))
    contact["confidence"] = max(contact["confidence"], min(90, inv["confidence"]))


def verify_only(company_name, email=None, website=None, job_url=None, recruiter_name=None, recruiter_linkedin=None,
                job_title=None, toolkit=None, online=None, use_cache=True):
    """Company/recruiter verification without any listing text (ML layer skipped)."""
    return investigate(InvestigationInput(company_name, normalize_url(website)[0], recruiter_name, (email or "").strip().lower() or None,
                                          recruiter_linkedin, normalize_url(job_url)[0], job_title), toolkit, online, use_cache)


def analyze_listing(text, company_name=None, email=None, website=None, job_url=None,
                    providers=None, use_cache=True, online=None, recruiter_name=None, recruiter_linkedin=None,
                    job_title=None, toolkit=None, **ml_kwargs):
    """Full analysis. Never raises on bad optional input; returns the unified result dict
    (adds `investigation` with identity, domain, recruiter, job evidence, graph and verdict)."""
    issues = []
    text = text or ""
    email = (email or "").strip().lower() or None
    if email and not validate_email(email):
        issues.append(f"'{email}' is not a valid email address; it was ignored."); email = None
    website, err = normalize_url(website)
    if err: issues.append(f"Company website ignored: {err}.")
    job_url, err = normalize_url(job_url)
    if err: issues.append(f"Job URL ignored: {err}.")
    if not email:
        found = extract_emails(text)
        email = found[0] if found else None
    ext = extract_company(text, company_name)
    internship = analyze_internship(text, **ml_kwargs)
    inv = _run_investigation(ext["display_name"], email, website, job_url, recruiter_name, recruiter_linkedin, job_title, text, toolkit, online, use_cache)
    if providers is None and inv and inv["live"]:
        providers = [KnownCompanyProvider()]   # web/search evidence already gathered by the investigation
    try:
        company = verify_company(ext["display_name"], email=email, website=website,
                                 providers=providers, use_cache=use_cache, online=online)
    except Exception as e:  # last-resort guard: verification must never break ML result
        company = {"company_name": ext["display_name"], "normalized_name": ext["normalized_name"], "company_found": False,
                   "official_website": None, "official_domain": None, "email_domain": None, "risk_score": 40,
                   "risk_level": "CAUTION", "confidence": 0, "status": "UNAVAILABLE", "verification_ran": False,
                   "impersonation_suspected": False, "signals": [], "positive_evidence": [], "warning_signals": [],
                   "high_risk_signals": [], "sources": [], "limitations": [f"Company verification failed ({type(e).__name__})."]}
    contact = analyze_contact(company, email, job_url, internship["raw"].get("raw_features"))
    _merge_investigation(company, contact, inv)
    overall = calculate_overall_risk(internship, company, contact)
    expl = generate_explanation(internship, company, contact, overall)
    overall["reasons"] = [e["title"] for e in expl["high_risk"] + expl["warnings"]][:6]
    return {
        "internship_prediction": {"label": internship["label"], "probability": internship["probability"],
                                  "risk_score": internship["score"], "confidence": internship["confidence"],
                                  "indicators": internship["indicators"], "vectors": internship["vectors"]},
        "company_verification": company, "contact_analysis": contact, "overall_assessment": overall,
        "explanation": expl, "extraction": ext, "input_issues": issues, "investigation": inv,
    }
