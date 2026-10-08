"""Evidence graph, source-quality grading, per-dimension scoring and verdict logic."""
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from company_utils import JOB_BOARDS, get_domain, registrable_domain

SOURCE_WEIGHTS = {"very_high": 1.0, "high": 0.8, "medium_high": 0.65, "medium": 0.5, "low": 0.25, "very_low": 0.1}
_MEDIUM = {"wikipedia.org", "crunchbase.com", "bloomberg.com", "reuters.com", "forbes.com", "economictimes.com",
           "techcrunch.com", "britannica.com", "wikidata.org"}
_LOW = {"glassdoor.com", "glassdoor.co.in", "ambitionbox.com", "zaubacorp.com", "tofler.in", "trustpilot.com",
        "quora.com", "reddit.com", "medium.com"}


def classify_source(url: str, official_domain: Optional[str] = None) -> Dict:
    """Grade a source URL. Returns {quality, weight}. Unknown sites are 'very_low'."""
    host = get_domain(url)
    reg = registrable_domain(host)
    if official_domain and reg == registrable_domain(official_domain):
        q = "very_high"
    elif host.endswith((".gov", ".gov.in", ".nic.in")) or reg in ("opencorporates.com", "sec.gov", "mca.gov.in"):
        q = "very_high"
    elif reg == "linkedin.com":
        q = "high"
    elif reg in JOB_BOARDS:
        q = "medium_high"
    elif reg in _MEDIUM:
        q = "medium"
    elif reg in _LOW:
        q = "low"
    else:
        q = "very_low"
    return {"quality": q, "weight": SOURCE_WEIGHTS[q]}


@dataclass
class Relation:
    """One edge of the evidence graph."""
    status: str = "not_checked"      # verified|partially_verified|mismatch|unverified|not_found|unavailable|not_checked
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)
    reason: str = ""


def relation(status, confidence, reason, evidence=None, sources=None) -> Dict:
    """Build a Relation as a plain dict."""
    return asdict(Relation(status, round(confidence, 2), evidence or [], [s for s in (sources or []) if s], reason))


def _clamp(x) -> int:
    return int(max(0, min(100, round(x))))


def score_company(identity, live: bool) -> Optional[int]:
    """Company authenticity 0-100 (None if identity could not be established at all)."""
    if not identity.official_domain and identity.confidence == 0:
        return None
    return _clamp(identity.confidence)


def score_domain(official: Optional[Dict], provided: List[Dict]) -> Optional[int]:
    """Domain authenticity: how trustworthy the domains actually supplied are (or the official one if none supplied)."""
    if provided:
        vals = []
        for p in provided:
            if p["status"] == "verified": vals.append(95)
            elif "subdomain_spoof" in p["techniques"]: vals.append(5)
            elif p["lookalike"] and p["risk"] == "HIGH": vals.append(10 + (100 - p["similarity"]) // 3)
            elif p["lookalike"]: vals.append(25)
            elif p["status"] == "mismatch": vals.append(35)
        return min(vals) if vals else None
    if official and official.get("dns") == "verified":
        s = 85
        if official.get("age_days") is not None and official["age_days"] < 180: s -= 30
        if official.get("parked"): s -= 40
        return _clamp(s)
    return None


def score_recruiter(provided: bool, email: Dict, prof: Dict, listed: str) -> Optional[int]:
    """Recruiter authenticity (None when no recruiter detail was supplied)."""
    if not provided:
        return None
    s = 45
    st = email.get("status")
    if st == "official_domain_match": s += 35
    elif st == "lookalike_domain": s = min(s - 25, 15)
    elif st == "domain_mismatch": s -= 20
    elif st == "free_email_provider": s -= 12
    if email.get("possible_impersonation"): s = min(s, 15)
    if email.get("disposable"): s -= 15
    if listed == "verified": s += 20
    if prof.get("level") == "strong": s += 20
    elif prof.get("level") == "medium": s += 12
    if prof.get("conflicting_employer"): s -= 15
    if prof.get("linkedin_url_valid") is False: s -= 5
    return _clamp(s)


def score_job(careers: Dict, job_url_domain: Optional[Dict], job_url_kind: Optional[str], provided: bool) -> Optional[int]:
    """Job/listing authenticity (None when neither a job title nor a job URL is available)."""
    if not provided:
        return None
    if careers["status"] == "verified":
        return 90
    if job_url_domain:
        if job_url_domain["status"] == "verified": s = 65
        elif job_url_kind == "job_board": s = 50
        elif job_url_domain["lookalike"]: s = 12
        else: s = 28
        if careers["status"] == "not_found": s -= 5
        return _clamp(s)
    return 45 if careers["status"] == "not_found" else 50


VERDICT_TEXT = {
    "VERIFIED": "Strong evidence that the company and the supplied identity details are genuine.",
    "MOSTLY VERIFIED": "The company appears genuine and most evidence is consistent; some items could not be confirmed.",
    "PARTIALLY VERIFIED": "The company appears real, but recruiter/job/contact authenticity remains uncertain.",
    "SUSPICIOUS": "Multiple inconsistencies were found.",
    "LIKELY IMPERSONATION": "Strong evidence that someone may be pretending to represent the company.",
    "UNVERIFIED": "Not enough reliable evidence to verify the company.",
    "VERIFICATION UNAVAILABLE": "Live verification could not run, so no conclusion about the company is possible.",
}


def decide_verdict(*, identity_conf: int, basis: str, live: bool, scores: Dict, impersonation: bool,
                   negatives: float, provided_recruiter: bool, provided_job: bool, unavailable_all: bool) -> str:
    """Nuanced verdict. 'Not found' never maps to 'fake'; impersonation needs an established company identity."""
    from config import IDENTITY_VERIFIED_MIN
    established = identity_conf >= IDENTITY_VERIFIED_MIN
    if impersonation and identity_conf >= 60:
        return "LIKELY IMPERSONATION"
    if not established:
        if negatives >= 2:
            return "SUSPICIOUS"
        return "VERIFICATION UNAVAILABLE" if unavailable_all else "UNVERIFIED"
    weak_recruiter = provided_recruiter and (scores.get("recruiter") is None or scores["recruiter"] < 60)
    weak_job = provided_job and (scores.get("job") is None or scores["job"] < 60)
    if negatives >= 2:
        return "SUSPICIOUS"
    if negatives > 0 or weak_recruiter or weak_job:
        return "PARTIALLY VERIFIED"
    if basis == "offline_database" or not live:
        return "MOSTLY VERIFIED"
    return "VERIFIED" if scores.get("overall", 0) >= 85 else "MOSTLY VERIFIED"
