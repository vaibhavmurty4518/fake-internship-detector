"""Company verification: evidence collection -> structured signals -> risk + confidence.

Risk (0-100) says how concerning the evidence is. Confidence (0-100) says how
much evidence we actually have. They are deliberately independent. Nothing here
asserts that a company "is fake"; absence of data raises uncertainty, not guilt.
"""
import hashlib
import json
import os
import time

import config
from cache_store import cache_get, cache_put
from company_providers import (default_providers, is_online, lookup_known_company)
from company_utils import (SUSPICIOUS_TLDS, URL_SHORTENERS, email_domain, extract_company,
                           get_domain, is_free_email_domain, name_domain_relationship,
                           normalize_name, registrable_domain)

VERIFICATION_LIMITATIONS = (
    "Automated checks cannot confirm legal registration or the authenticity of a specific job offer.",
)


def make_signal(name, value, severity, explanation, source=None):
    """Build a structured signal. severity: positive | info | low | medium | high."""
    return {"name": name, "value": value, "severity": severity,
            "explanation": explanation, "source": source}


# ----------------------------------------------------------------- cache
def _cache_key(normalized, website, edomain):
    return hashlib.sha256(f"{normalized}|{get_domain(website or '')}|{edomain}".encode()).hexdigest()[:24]


def _cache_get(key):
    hit = cache_get(key)
    return hit[0] if hit else None


def _cache_put(key, result):
    cache_put(key, result)


# ------------------------------------------------------------- main API
def verify_company(company_name, email=None, website=None, providers=None,
                   use_cache=True, online=None):
    """Verify a company and return the structured evidence result.

    Args:
        company_name: display name as entered/extracted (may be empty).
        email: optional recruiter email (used for domain comparison).
        website: optional website URL claimed for the company.
        providers: optional list of CompanyVerificationProvider (default set used if None).
        use_cache: reuse cached provider evidence for the same company/website.
        online: override connectivity detection (tests).

    Returns dict with company_name, normalized_name, company_found, official_website,
    official_domain, email_domain, risk_score, risk_level, confidence, status,
    impersonation_suspected, verification_ran, signals, positive_evidence,
    warning_signals, high_risk_signals, sources, limitations.
    """
    display = (company_name or "").strip()
    norm = normalize_name(display)
    edomain = email_domain(email) if email else ""
    result = {
        "company_name": display, "normalized_name": norm, "company_found": False,
        "official_website": None, "official_domain": None, "email_domain": edomain or None,
        "risk_score": 50, "risk_level": "SUSPICIOUS", "confidence": 5, "status": "UNVERIFIED",
        "impersonation_suspected": False, "verification_ran": True,
        "signals": [], "positive_evidence": [], "warning_signals": [], "high_risk_signals": [],
        "sources": [], "limitations": list(VERIFICATION_LIMITATIONS),
    }
    sig = result["signals"]

    if not norm:
        sig.append(make_signal("insufficient_public_information", True, "info",
                               "No company name was provided or could be extracted."))
        result.update(risk_score=40, risk_level=config.risk_level(40), confidence=5, status="UNVERIFIED")
        result["limitations"].append("Company identity could not be established from the input.")
        return _finalise(result)

    online = is_online() if online is None else online
    key = _cache_key(norm, website, edomain)
    cached = _cache_get(key) if use_cache and online else None
    if cached:
        cached["limitations"] = list(set(cached.get("limitations", []) + ["Result served from cache."]))
        return cached

    provs = providers if providers is not None else default_providers()
    results = []
    known = lookup_known_company(norm)
    ext_known = known is not None
    for p in provs:
        try:
            # website provider: prefer user-supplied site, else the known official one
            if p.name == "website-check":
                site = website or (("https://www." + known[1]) if known else None)
                results.append(p.verify(display, norm, site))
            else:
                results.append(p.verify(display, norm, website))
        except Exception as e:  # a broken provider must never break analysis
            result["limitations"].append(f"Provider {getattr(p, 'name', '?')} failed ({type(e).__name__}).")
    by = {r.provider: r for r in results}
    for r in results:
        result["sources"] += [s for s in r.sources if s.get("url")]
        if not r.available and r.provider != "web-search":
            result["limitations"].append(r.notes[0] if r.notes else f"{r.provider} unavailable.")
    if "web-search" in by and not by["web-search"].available:
        result["limitations"].append("External search not configured/available; used limited sources.")
    result["verification_ran"] = any(r.available for r in results) or ext_known

    risk, conf = 35.0, 10.0
    kb, web, srch = by.get("offline-knowledge"), by.get("website-check"), by.get("web-search")

    # official domain candidates
    official = None
    if kb and kb.found:
        official = kb.official_domain
        result["official_website"] = kb.website
    claimed_domain = registrable_domain(get_domain(website)) if website else None
    if web and web.found and web.official_domain:
        result["official_website"] = web.website
        if not official:
            official = web.official_domain
    elif website and not official:
        official = claimed_domain
        result["official_website"] = website
    result["official_domain"] = official

    # --- company identity
    if kb and kb.found:
        sig.append(make_signal("company_found", True, "positive",
                               "Company matches a well-known organisation.", "offline-knowledge"))
        risk -= 15; conf += 35
        if kb.facts.get("alias_match"):
            sig.append(make_signal("company_name_match", "alias", "positive",
                                   "Entered name is a recognised variant of the organisation.", "offline-knowledge"))
    else:
        sig.append(make_signal("company_found", False, "info", "Company not independently recognised."))

    # --- website
    if claimed_domain and kb and kb.found and claimed_domain != registrable_domain(kb.official_domain):
        sig.append(make_signal("inconsistent_company_identity", True, "high",
                               f"Claimed website ({claimed_domain}) differs from the known domain of this organisation.",
                               "website"))
        risk += 30; conf += 10
    if web is not None and web.available and website is not None or (web and web.found and kb and kb.found):
        f = web.facts
        if web.found:
            sig.append(make_signal("official_website_found", True, "positive",
                                   "A reachable website was found.", "website-check"))
            risk -= 8; conf += 20
            if f.get("https"):
                sig.append(make_signal("https_available", True, "info",
                                       "HTTPS is available (this alone does not prove legitimacy).", "website-check"))
                conf += 2
            else:
                sig.append(make_signal("no_https", True, "low", "Website does not use HTTPS.", "website-check"))
                risk += 5
            if f.get("name_on_site"):
                sig.append(make_signal("website_represents_company", True, "positive",
                                       "Company name appears on the website.", "website-check"))
                risk -= 5; conf += 10
            elif web.facts:
                sig.append(make_signal("website_represents_company", False, "low",
                                       "Company name was not found on the website.", "website-check"))
                risk += 8
            if f.get("has_about") or f.get("has_contact"):
                sig.append(make_signal("about_contact_present", True, "positive",
                                       "Website has about/contact information.", "website-check"))
                risk -= 4; conf += 8
            else:
                sig.append(make_signal("about_contact_present", False, "low",
                                       "No about/contact information detected on the website.", "website-check"))
                risk += 5
            if f.get("parked"):
                sig.append(make_signal("suspicious_domain", True, "medium",
                                       "Website looks like a parked or for-sale domain.", "website-check"))
                risk += 15
        else:
            sig.append(make_signal("official_website_found", False, "medium" if website else "info",
                                   "The supplied website could not be reached or does not resolve.", "website-check"))
            if website:
                risk += 12; conf += 8
    elif website:
        sig.append(make_signal("official_website_found", "unchecked", "info",
                               "Website was supplied but could not be checked (offline)."))

    if official:
        rel = name_domain_relationship(norm, official)
        if rel == "none" and not (kb and kb.found):
            sig.append(make_signal("company_name_match", False, "medium",
                                   f"Domain {official} does not obviously correspond to the company name.", "domain-analysis"))
            risk += 12; conf += 5
        elif rel in ("strong", "partial") and not (kb and kb.found):
            sig.append(make_signal("company_name_match", True, "positive",
                                   f"Domain {official} corresponds to the company name.", "domain-analysis"))
            risk -= 5; conf += 8
        tld = official.rsplit(".", 1)[-1]
        if tld in SUSPICIOUS_TLDS or official in URL_SHORTENERS:
            sig.append(make_signal("suspicious_domain", True, "medium",
                                   f"Domain uses a TLD/host ('.{tld}') frequently abused in scam listings; not proof of fraud.",
                                   "domain-analysis"))
            risk += 10

    # --- email comparison
    if edomain:
        free = is_free_email_domain(edomain)
        if free:
            sig.append(make_signal("free_email_used", True, "low",
                                   "Recruiter uses a free email provider. Common among small teams too, but raises caution.",
                                   "email-analysis"))
            risk += 8; conf += 8
        if official:
            if registrable_domain(edomain) == registrable_domain(official):
                sig.append(make_signal("official_domain_match", True, "positive",
                                       "Recruiter email domain matches the company's official domain.", "email-analysis"))
                sig.append(make_signal("email_domain_match", "official_domain_match", "positive",
                                       "Email domain evidence: official_domain_match.", "email-analysis"))
                risk -= 15; conf += 20
            else:
                state = "free_email_provider" if free else "domain_mismatch"
                sig.append(make_signal("official_domain_match", False, "high" if (kb and kb.found) else "medium",
                                       f"Recruiter email domain ({edomain}) does not match the official domain ({official}).",
                                       "email-analysis"))
                sig.append(make_signal("email_domain_match", state, "medium", f"Email domain evidence: {state}.",
                                       "email-analysis"))
                if kb and kb.found:
                    result["impersonation_suspected"] = True
                    sig.append(make_signal("possible_company_impersonation", True, "high",
                                           "A well-known company name is used with an unrelated contact domain. "
                                           "This suggests possible impersonation of the company, not wrongdoing by the company itself.",
                                           "email-analysis"))
                    risk += 35; conf += 15
                else:
                    risk += 12; conf += 8
        else:
            sig.append(make_signal("email_domain_match", "unknown", "info",
                                   "No official domain known, so the email domain cannot be compared."))
            rel = name_domain_relationship(norm, edomain) if not free else "none"
            if rel in ("strong", "partial"):
                sig.append(make_signal("company_name_match", True, "positive",
                                       f"Email domain {edomain} corresponds to the company name.", "email-analysis"))
                risk -= 8; conf += 10

    # --- search / reputation
    if srch and srch.available:
        f = srch.facts
        conf += 12
        if f.get("presence_results", 0) >= 2:
            sig.append(make_signal("company_presence_strength", "moderate/strong", "positive",
                                   "Multiple public web results reference the company.", "web-search"))
            risk -= 8; conf += 8
        else:
            sig.append(make_signal("company_presence_strength", "weak", "low",
                                   "Few public web results reference the company.", "web-search"))
            risk += 8
        if f.get("scam_mentions", 0):
            sig.append(make_signal("scam_report_found", True, "high",
                                   f"{f['scam_mentions']} public result(s) mention scam/fraud together with this name. "
                                   "Review them; they may refer to impersonators.", "web-search"))
            sig.append(make_signal("negative_reputation_found", True, "medium",
                                   "Negative reputation mentions were found.", "web-search"))
            risk += 25
    sig_names = {s["name"] for s in sig}
    if not (kb and kb.found) and not (web and web.found) and not (srch and srch.found):
        sig.append(make_signal("insufficient_public_information", True, "low",
                               "Little independent public information was available to verify this company.", None))
        risk += 10
        result["limitations"].append("Company identity could not be confidently established.")

    result["company_found"] = bool((kb and kb.found) or (web and web.found) or (srch and srch.found))
    result["risk_score"] = round(max(0, min(100, risk)))
    result["confidence"] = round(max(0, min(100, conf)))
    result["risk_level"] = config.risk_level(result["risk_score"])
    _finalise(result)
    if use_cache and online and result["confidence"] > 10:
        _cache_put(key, result)
    return result


def _finalise(result):
    """Derive positive/warning/high lists and a status label from signals."""
    sev_groups = {"positive": "positive_evidence", "low": "warning_signals", "medium": "warning_signals",
                  "high": "high_risk_signals"}
    for k in ("positive_evidence", "warning_signals", "high_risk_signals"):
        result[k] = []
    for s in result["signals"]:
        g = sev_groups.get(s["severity"])
        if g:
            result[g].append({"title": _title(s),
                              "detail": s["explanation"], "source": s["source"]})
    result["status"] = company_status(result)
    return result


_NEG_TITLES = {
    "official_domain_match": "Recruiter domain does not match company domain",
    "official_website_found": "Company website could not be confirmed",
    "company_name_match": "Domain does not match company name",
    "website_represents_company": "Website does not clearly represent the company",
    "about_contact_present": "Website lacks about/contact details",
    "company_presence_strength": "Limited public presence",
}


def _title(s):
    """Human-readable title; negative values of match-style signals read as mismatches."""
    if s["value"] is False and s["name"] in _NEG_TITLES:
        return _NEG_TITLES[s["name"]]
    return s["name"].replace("_", " ").capitalize()


def company_status(r):
    """VERIFIED / PARTIALLY VERIFIED / UNVERIFIED / HIGH RISK SIGNALS / UNAVAILABLE."""
    if not r.get("verification_ran", True):
        return "UNAVAILABLE"
    if r.get("impersonation_suspected") or (r["risk_score"] >= 60 and r["confidence"] >= 30):
        return "HIGH RISK SIGNALS"
    if r["company_found"] and r["risk_score"] <= 30 and r["confidence"] >= 55:
        return "VERIFIED"
    if r["company_found"] and r["confidence"] >= 30:
        return "PARTIALLY VERIFIED"
    return "UNVERIFIED"
