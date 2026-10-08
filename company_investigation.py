"""Company/recruiter investigation orchestrator.

Flow: search -> identity -> official website -> domain checks -> careers -> recruiter -> email/domain
comparison -> impersonation -> evidence graph -> scores -> verdict. Every check reports one of
verified | unverified | not_found | unavailable | not_checked and nothing is claimed unless it ran.
"""
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import config
from cache_store import cache_get, cache_put
from company_identity import finalize_confidence, resolve_identity
from company_providers import (CachedSearch, CareersProvider, DomainProvider, ProfessionalEvidenceProvider,
                               SearchBackend, SiteInspector, get_search_backend, is_online, sanitize_text)
from company_utils import (JOB_BOARDS, email_domain, extract_company, get_domain, is_free_email_domain,
                           normalize_name, registrable_domain, validate_email)
from domain_analysis import analyze_domain, brand_in_text, is_disposable
from evidence_engine import (VERDICT_TEXT, classify_source, decide_verdict, relation, score_company, score_domain,
                             score_job, score_recruiter)

log = logging.getLogger("internshield.investigation")
_SCAM = re.compile(r"\b(scam|fraud|fake|phishing|beware)\b", re.I)


@dataclass
class InvestigationInput:
    """User-supplied facts. Only company_name is required."""
    company_name: str
    website: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    recruiter_linkedin: Optional[str] = None
    job_url: Optional[str] = None
    job_title: Optional[str] = None


@dataclass
class Toolkit:
    """Injectable providers (tests pass fakes; production uses defaults)."""
    backend: Optional[SearchBackend] = None
    site: object = field(default_factory=SiteInspector)
    domain: object = field(default_factory=DomainProvider)
    careers: object = field(default_factory=CareersProvider)
    professional: object = field(default_factory=ProfessionalEvidenceProvider)


def default_toolkit() -> Toolkit:
    """Toolkit using the configured search backend (None when no API key)."""
    return Toolkit(backend=get_search_backend())


def guess_job_title(text: str) -> Optional[str]:
    """Heuristic job title from the first lines of a listing."""
    for line in (text or "").splitlines()[:6]:
        line = line.strip(" -*•#\t")
        if 3 < len(line) < 80 and re.search(r"\b(intern(ship)?|engineer|analyst|developer|trainee|associate|designer|scientist)\b", line, re.I) \
                and not re.match(r"(?i)company|about|we |our ", line):
            return sanitize_text(line, 80)
    return None


def _cached(key, fn, use_cache, stamps):
    hit = cache_get(key) if use_cache else None
    if hit:
        stamps.append(hit[1]); return hit[0]
    v = fn()
    stamps.append(time.time())
    if use_cache and v.get("status", v.get("dns")) not in ("unavailable",):
        cache_put(key, v)
    return v


def analyze_email(email: Optional[str], official: Optional[str], brand: str) -> Dict:
    """Email evidence: official_domain_match | lookalike_domain | domain_mismatch | free_email_provider | unknown | not_provided."""
    out = {"email": email, "domain": None, "status": "not_provided", "free": False, "disposable": False,
           "possible_impersonation": False, "lookalike": None, "reasons": []}
    if not email:
        return out
    d = email_domain(email); local = email.split("@")[0]
    out.update(domain=d, free=is_free_email_domain(d), disposable=is_disposable(d))
    brand_local = brand_in_text(local, brand) or brand_in_text(d.split(".")[0], brand)
    if out["free"]:
        out["status"] = "free_email_provider"
        out["reasons"].append("Recruiter email uses a free provider; this alone is not proof of fraud.")
        if brand_local:
            out["possible_impersonation"] = True
            out["reasons"].append("The address embeds the company name on a free provider, which is a common impersonation pattern.")
    elif official:
        a = analyze_domain(official, d)
        out["lookalike"] = a
        if a["official_domain_match"]:
            out["status"] = "official_domain_match"
            out["reasons"].append(f"Email domain {d} matches the official domain {registrable_domain(official)}.")
        elif a["lookalike"]:
            out["status"] = "lookalike_domain"; out["reasons"] += a["reasons"]
            out["possible_impersonation"] = a["risk"] in ("HIGH", "MEDIUM")
        else:
            out["status"] = "domain_mismatch"; out["reasons"] += a["reasons"]
    else:
        out["status"] = "unknown"
    if out["disposable"]:
        out["reasons"].append("The email domain is a known disposable-mail provider.")
    return out


def investigate(inp: InvestigationInput, toolkit: Optional[Toolkit] = None, online: Optional[bool] = None,
                use_cache: bool = True) -> Dict:
    """Run the full verification pipeline and return the structured result (never raises for provider failures)."""
    tk = toolkit or default_toolkit()
    name = sanitize_text(inp.company_name, 80)
    norm = normalize_name(name)
    online = is_online() if online is None else online
    stamps: List[float] = []
    limitations: List[str] = []
    checks = {k: "not_checked" for k in ("internet", "search", "website", "domain_dns", "domain_age", "careers", "recruiter_search", "email_analysis", "lookalike_analysis")}
    checks["internet"] = "verified" if online else "unavailable"
    res: Dict = {"company_name": name, "normalized_name": norm, "checks": checks, "limitations": limitations}

    search = CachedSearch(tk.backend if online else None, use_cache)
    ident = resolve_identity(name, search, inp.website) if norm else resolve_identity("", None)
    if not online:
        checks["search"] = "unavailable"; limitations.append("Internet verification unavailable; only offline evidence (built-in employer table, domain analysis, ML) was used.")
    elif not search.available:
        checks["search"] = "unavailable"; limitations.append("No search API key configured (SEARCH_API_KEY); identity evidence is limited to the offline table and supplied details.")
    else:
        checks["search"] = "unavailable" if search.failed and search.failed >= len(search.ran) and not stamps and not any(search.timestamps) else "verified"
        if search.failed and search.failed >= len(search.ran) > 0:
            checks["search"] = "unavailable"; limitations.append("The search provider failed; live identity evidence is missing.")
    official = ident.official_domain

    # --- official website + domain facts
    site: Dict = {"status": "not_checked"}
    domain: Dict = {"dns": "not_checked", "age_status": "not_checked"}
    if online and ident.official_website:
        site = _cached("site:" + (official or ""), lambda: tk.site.inspect(ident.official_website, norm), use_cache, stamps)
        domain = _cached("domain:" + (official or ""), lambda: tk.domain.check(official), use_cache, stamps)
        checks["website"], checks["domain_dns"], checks["domain_age"] = site["status"], domain.get("dns", "unavailable"), domain.get("age_status", "not_checked")
        if site.get("parked"):
            domain["parked"] = True
        if site.get("status") == "not_checked" and site.get("reason"):
            limitations.append("Website not inspected: " + sanitize_text(site["reason"], 80))
        if site.get("instruction_like_text_ignored"):
            limitations.append("The website contained instruction-like text; it was treated as ordinary untrusted content.")
    elif ident.official_website:
        limitations.append("Official website could not be checked (offline).")
    finalize_confidence(ident, site, domain)
    established = ident.confidence >= config.IDENTITY_VERIFIED_MIN

    # --- provided details
    email = (inp.recruiter_email or "").strip().lower() or None
    if email and not validate_email(email):
        limitations.append("Recruiter email ignored (invalid format)."); email = None
    email_info = analyze_email(email, official if established or ident.official_domain else None, norm)
    checks["email_analysis"] = "verified" if email else "not_checked"
    provided: List[Dict] = []
    if inp.website and official:
        a = analyze_domain(official, inp.website); a["kind"] = "website"; provided.append(a)
    job_kind = None
    if inp.job_url:
        jd = registrable_domain(get_domain(inp.job_url))
        if jd in JOB_BOARDS:
            job_kind = "job_board"
        elif official:
            a = analyze_domain(official, inp.job_url); a["kind"] = "job_url"; provided.append(a); job_kind = "official" if a["official_domain_match"] else "other"
    if email_info["lookalike"]:
        l = dict(email_info["lookalike"]); l["kind"] = "email"; provided.append(l)
    checks["lookalike_analysis"] = "verified" if (provided or email_info["status"] != "not_provided") and official else "not_checked"
    job_url_analysis = next((p for p in provided if p["kind"] == "job_url"), None)

    # --- careers / recruiter evidence
    job_title = inp.job_title
    careers = {"status": "not_checked", "careers_page": "not_checked", "job_title_match": "not_checked", "company_match": "not_checked",
               "location_match": "not_checked", "recruiter_listed": "not_checked", "urls": []}
    if online and official and established and (job_title or inp.job_url):
        careers = tk.careers.find(official, site.get("careers_url"), job_title, inp.job_url, norm, search, inp.recruiter_name)
        checks["careers"] = careers["status"]
    prof = {"status": "not_checked", "level": "none", "profile_url": None, "conflicting_employer": None, "sources": [], "linkedin_url_valid": None}
    if inp.recruiter_name or inp.recruiter_linkedin:
        prof = tk.professional.find(inp.recruiter_name or "", name, inp.recruiter_linkedin, search if online else None, official)
        checks["recruiter_search"] = prof["status"]
    if inp.recruiter_name and site.get("recruiter_name_on_site"):
        careers["recruiter_listed"] = "verified"

    # --- reputation (company-level, cached)
    scam_hits = []
    if online and search.available and norm:
        r = search.search(f'"{name}" internship scam OR fraud')
        first = (norm.split() or [""])[0]
        scam_hits = [h for h in r.hits if first and first in (h.title + h.snippet).lower() and _SCAM.search(h.title + " " + h.snippet)] if r.ok else []

    # --- impersonation + negatives
    lookalike_high = [p for p in provided if p["lookalike"] and (p["risk"] == "HIGH")]
    impersonation = bool(lookalike_high) or email_info["possible_impersonation"] or any(p["lookalike"] and p["kind"] == "website" for p in provided)
    neg = 0.0
    neg += 0.5 if email_info["status"] == "free_email_provider" else 0
    neg += 1 if email_info["status"] in ("domain_mismatch", "lookalike_domain") else 0
    neg += 1 if email_info["possible_impersonation"] and email_info["status"] == "free_email_provider" else 0
    neg += sum(1 for p in provided if p["kind"] in ("website", "job_url") and p["status"] == "mismatch")
    neg += 1 if (domain.get("age_days") is not None and domain["age_days"] < config.YOUNG_DOMAIN_DAYS) else 0
    neg += 1 if domain.get("parked") else 0
    neg += 1 if prof.get("conflicting_employer") else 0
    neg += 0.5 if scam_hits else 0

    # --- scores
    scores: Dict = {"company_authenticity": score_company(ident, online)}
    scores["official_domain"] = score_domain(domain if domain.get("dns") == "verified" else None, [])
    scores["provided_domain"] = score_domain(None, provided) if provided else None
    scores["domain_authenticity"] = scores["provided_domain"] if scores["provided_domain"] is not None else scores["official_domain"]
    provided_recruiter = bool(inp.recruiter_name or email or inp.recruiter_linkedin)
    scores["recruiter_authenticity"] = score_recruiter(provided_recruiter, email_info, prof, careers["recruiter_listed"])
    provided_job = bool(job_title or inp.job_url)
    scores["job_authenticity"] = score_job(careers, job_url_analysis, job_kind, provided_job)
    parts = [(0.35, scores["company_authenticity"]), (0.20, scores["domain_authenticity"]), (0.25, scores["recruiter_authenticity"]), (0.20, scores["job_authenticity"])]
    parts = [(w, v) for w, v in parts if v is not None]
    ov = round(sum(w * v for w, v in parts) / sum(w for w, _ in parts)) if parts else None
    if ov is not None and impersonation and established:
        ov = min(ov, 30)
    scores["overall_verification"] = ov

    live = online and ident.basis == "live_search" or site.get("status") == "verified"
    unavailable_all = (not online or checks["search"] == "unavailable") and site.get("status") != "verified" and ident.basis != "offline_database"
    verdict = decide_verdict(identity_conf=ident.confidence, basis=ident.basis, live=bool(live),
                             scores={"recruiter": scores["recruiter_authenticity"], "job": scores["job_authenticity"], "overall": ov or 0},
                             impersonation=impersonation, negatives=neg, provided_recruiter=provided_recruiter,
                             provided_job=provided_job, unavailable_all=unavailable_all)
    conf = 0.5 * ident.confidence + (12 if site.get("status") == "verified" else 0) + (8 if domain.get("dns") == "verified" else 0) \
        + (8 if domain.get("age_status") == "verified" else 0) \
        + (10 if (not provided_recruiter or email or prof["status"] in ("verified", "not_found")) else 0) \
        + (10 if (not provided_job or careers["status"] in ("verified", "not_found") or job_url_analysis) else 0)
    if not live:
        conf = min(conf, 45)
    conf = int(max(0, min(100, conf)))
    res["confidence"], res["confidence_label"] = conf, "HIGH" if conf >= 75 else ("MEDIUM" if conf >= 45 else "LOW")

    # --- graph
    src = lambda *u: [x for x in u if x]
    graph = {
        "company_to_website": relation("verified" if established and site.get("status") == "verified" else ("partially_verified" if official else "unverified"),
                                       ident.confidence / 100, f"Identity basis: {ident.basis}.", ident.candidates[0]["evidence"] if ident.candidates else [], src(ident.official_website)),
        "website_to_domain": relation(domain.get("dns", "not_checked") if domain.get("dns") != "verified" else "verified", 0.9 if domain.get("dns") == "verified" else 0.0,
                                      "DNS resolution of the official domain.", [], src(ident.official_website)),
        "domain_to_careers": relation(careers["careers_page"], 0.8 if careers["careers_page"] == "verified" else 0.0, "Careers page on the official domain.", [], careers["urls"][:1]),
        "careers_to_job": relation(careers["status"] if job_title or inp.job_url else "not_checked", 0.85 if careers["status"] == "verified" else 0.4 if careers["status"] == "not_found" else 0.0,
                                   "Job title found on the official careers site." if careers["status"] == "verified" else "Job could not be independently confirmed on the official careers site.", [], careers["urls"][:1]),
        "job_to_recruiter": relation(careers["recruiter_listed"], 0.7 if careers["recruiter_listed"] == "verified" else 0.0, "Recruiter named on official pages.", [], []),
        "recruiter_to_company": relation("verified" if (prof["level"] == "strong") else "partially_verified" if prof["level"] == "medium" else (prof["status"] if inp.recruiter_name else "not_checked"),
                                         {"strong": 0.9, "medium": 0.6, "none": 0.0}[prof["level"]], "Public professional evidence linking recruiter and company.", [s["title"] for s in prof["sources"]][:3], [s["url"] for s in prof["sources"]][:3]),
        "recruiter_to_email": relation("verified" if email else "not_checked", 1.0 if email else 0.0, "Email supplied with the recruiter details.", [], []),
        "email_to_domain": relation({"official_domain_match": "verified", "lookalike_domain": "mismatch", "domain_mismatch": "mismatch", "free_email_provider": "mismatch", "unknown": "unverified", "not_provided": "not_checked"}[email_info["status"]],
                                    0.99 if email_info["status"] in ("official_domain_match", "lookalike_domain") else 0.6 if email_info["status"] != "not_provided" else 0.0,
                                    "; ".join(email_info["reasons"]) or "No email supplied.", [], []),
        "provided_domain_to_official": relation(("verified" if all(p["official_domain_match"] for p in provided) else "mismatch") if provided else "not_checked",
                                                0.95 if provided else 0.0, "; ".join(r for p in provided for r in p["reasons"]) or "No additional domain supplied.", [], []),
    }
    res["graph"] = graph

    # --- sources (graded, only real URLs)
    seen, sources = set(), []
    def add(title, url, kind):
        if url and url.startswith(("http://", "https://")) and url not in seen:
            seen.add(url); sources.append({"title": sanitize_text(title, 90) or url, "url": url, "kind": kind, **classify_source(url, official)})
    if site.get("status") == "verified": add("Official company website", site.get("final_url") or ident.official_website, "official website")
    if site.get("careers_url"): add("Careers link on official site", site["careers_url"], "careers")
    for u in careers["urls"]: add("Official careers page", u, "careers")
    for c in ident.candidates[:1]:
        for s in c["sources"]: add(s["title"], s["url"], "search result")
    for s in ident.independent_sources: add(s["title"], s["url"], "independent source")
    if ident.linkedin_url: add("Company LinkedIn page (search result)", ident.linkedin_url, "professional profile")
    for s in prof["sources"]: add(s["title"], s["url"], "recruiter evidence")
    for h in scam_hits[:2]: add("Possible scam/fraud mention: " + h.title, h.url, "reputation report")
    sources.sort(key=lambda s: -s["weight"])
    res["sources"] = sources

    # --- evidence + explanation
    pos, warn, high = [], [], []
    P = lambda t, d, **k: pos.append({"title": t, "detail": d, **k})
    W = lambda t, d, **k: warn.append({"title": t, "detail": d, **k})
    H = lambda t, d, **k: high.append({"title": t, "detail": d, **k})
    if established: P("Company identity established", f"Identity confidence {ident.confidence}% (basis: {ident.basis.replace('_', ' ')}).")
    else: W("Company identity not established", "Company identity could not be confidently established from available evidence.")
    if site.get("status") == "verified":
        P("Official website found and reachable", f"{ident.official_domain} responded" + (" over HTTPS (HTTPS alone is not proof)." if site.get("https") else "."))
        if site.get("name_on_site"): P("Company name matches website content", "The website content refers to the company.")
        if site.get("has_about") or site.get("has_contact"): P("About/contact information present", "The site exposes about/contact pages.")
        if site.get("careers_url"): P("Careers page link found", "The official site links to a careers section.")
    if domain.get("dns") == "verified": P("Official domain resolves", f"{official} resolves in DNS.")
    if domain.get("age_days") is not None and domain["age_days"] >= config.YOUNG_DOMAIN_DAYS: P("Established domain", f"Domain registered about {domain['age_days'] // 365} year(s) ago (public RDAP).")
    elif domain.get("age_days") is not None: H("Recently registered official-looking domain", f"Registered {domain['age_days']} days ago.")
    if careers["status"] == "verified": P("Job found on official careers site", "The job title matches content on the company's own careers domain.")
    elif careers["status"] == "not_found": W("Job not confirmed on official careers site", "The job could not be independently confirmed on the official careers site (it may be listed elsewhere or not indexed).")
    if prof["level"] in ("strong", "medium"): P("Public professional evidence for recruiter", "A public profile/page links the recruiter name with the company (cannot confirm current employment).")
    elif inp.recruiter_name and prof["status"] == "not_found": W("Recruiter connection could not be independently verified", "No public evidence linking the recruiter to the company was found; this is not proof of wrongdoing.")
    if prof.get("conflicting_employer"): W("Recruiter profile lists a different employer", f"A public result associates the name with '{prof['conflicting_employer']}'.")
    if email_info["status"] == "official_domain_match": P("Recruiter email matches official domain", email_info["reasons"][0])
    elif email_info["status"] == "free_email_provider": W("Recruiter uses a free email provider", email_info["reasons"][0])
    elif email_info["status"] == "domain_mismatch": H("Recruiter email domain does not match the official domain", " ".join(email_info["reasons"]))
    elif email_info["status"] == "lookalike_domain": H("Recruiter email uses a lookalike domain", " ".join(email_info["reasons"]))
    if email_info["possible_impersonation"] and email_info["status"] == "free_email_provider": H("Company name used in a free-provider email", email_info["reasons"][-1])
    if email_info["disposable"]: H("Disposable email provider", "The recruiter email uses a disposable-mail domain.")
    for p in provided:
        if p["kind"] == "email": continue
        lab = "Website" if p["kind"] == "website" else "Job link"
        if p["status"] == "verified": P(f"{lab} domain matches official domain", p["reasons"][0])
        elif p["lookalike"]: H(f"{lab} domain resembles the official domain but is not official", p["reasons"][0] + " " + p["caveat"])
        else: W(f"{lab} domain differs from the official domain", p["reasons"][0])
    if job_kind == "job_board": W("Job hosted on a third-party job platform", "Job boards are common, but the listing is not on the company's own domain.")
    if scam_hits: W("Public scam/fraud mentions", f"{len(scam_hits)} public result(s) mention scam/fraud with this name; they may concern impersonators — review the sources.")
    if impersonation and established: H("Possible company impersonation", "Contact details appear designed to look like the company's but are not connected to its official domain. This does not implicate the real company.")
    res["evidence"] = {"positive": pos, "warnings": warn, "high_risk": high}

    reasons: List[str] = []
    if official: reasons.append(f"The company's official domain appears to be {official}" + (" (live-verified)." if site.get("status") == "verified" else f" (basis: {ident.basis.replace('_', ' ')}; not live-verified)."))
    if email: reasons.append({"official_domain_match": f"The recruiter email uses the official domain ({email_info['domain']}).", "lookalike_domain": f"The recruiter email uses {email_info['domain']}, a lookalike of the official domain.",
                              "domain_mismatch": f"The recruiter email uses {email_info['domain']}, which is not the official domain.", "free_email_provider": f"The recruiter email uses a free provider ({email_info['domain']}).",
                              "unknown": "The recruiter email domain could not be compared (official domain unknown)."}[email_info["status"]])
    for p in provided:
        if p["kind"] != "email" and p["status"] != "verified": reasons.append(p["reasons"][0])
    if provided_recruiter and prof["status"] != "verified" and scores["recruiter_authenticity"] is not None and (scores["recruiter_authenticity"] < 60): reasons.append("The recruiter could not be independently connected to the company.")
    if provided_job and careers["status"] != "verified": reasons.append("The job could not be independently confirmed on the official careers site.")
    if not reasons: reasons.append("No contradicting evidence was found, but only limited details were supplied.")
    res["reasons"] = reasons

    conclusion = {
        "LIKELY IMPERSONATION": "The company itself appears legitimate, but the person/contact claiming to represent it could not be verified and shows multiple impersonation indicators.",
        "PARTIALLY VERIFIED": "The company appears legitimate, but the recruiter/job/contact details could not be fully connected to it.",
        "SUSPICIOUS": "Several inconsistencies were found; verify through the company's official channels before proceeding.",
        "UNVERIFIED": "The company could not be independently verified with the available evidence. This does not mean it is fake.",
        "VERIFICATION UNAVAILABLE": "Live verification was unavailable, so nothing could be concluded about this company.",
    }.get(verdict, VERDICT_TEXT[verdict])
    res["conclusion"] = conclusion
    res["verdict"], res["verdict_text"] = verdict, VERDICT_TEXT[verdict]

    # --- output
    res["identity"] = {k: getattr(ident, k) for k in ("legal_name", "official_website", "official_domain", "industry", "country", "location", "linkedin_url",
                                                       "careers_url", "description", "ambiguous", "basis", "confidence", "breakdown")}
    res["identity"]["careers_url"] = ident.careers_url or site.get("careers_url")
    res["identity"]["candidates"] = ident.candidates
    res["scores"] = scores
    res["domain_verification"] = {"official_domain": official, "dns": domain.get("dns"), "age_days": domain.get("age_days"), "registered": domain.get("registered"),
                                  "https": site.get("https"), "final_domain": site.get("final_domain"), "provided": provided}
    res["email"], res["recruiter"], res["careers"], res["site"] = email_info, prof, careers, {k: v for k, v in site.items() if k != "text"}
    res["flags"] = {
        "company_verified": established,
        "official_domain_verified": domain.get("dns") == "verified" and site.get("status") == "verified",
        "domain_match": (all(p["official_domain_match"] for p in provided if p["kind"] != "email") if any(p["kind"] != "email" for p in provided) else None),
        "official_domain_match": (all(p["official_domain_match"] for p in provided) if provided else None),
        "lookalike_domain": any(p["lookalike"] for p in provided),
        "free_email": email_info["free"], "possible_impersonation": bool(impersonation), "disposable_email": email_info["disposable"],
    }
    res["search_queries_run"] = len(search.ran)
    res["last_verified"] = datetime.fromtimestamp(min(stamps + search.timestamps) if (stamps or search.timestamps) else time.time()).strftime("%d %b %Y, %I:%M %p")
    res["live"] = bool(live)
    res["offline_notice"] = None if online else ("Internet verification unavailable.\n\nOffline evidence: built-in employer table, domain/lookalike analysis, existing ML scam analysis.\n"
                                                  "Verification confidence reduced because live web evidence is unavailable.")
    return res
