"""Lookalike / impersonation analysis of a provided domain against an official domain.

High similarity never proves malicious intent; results carry a caveat and technique list.
"""
import difflib
import re
import unicodedata
from typing import Dict, List, Optional

from company_utils import SUSPICIOUS_TLDS, domain_label, get_domain, registrable_domain

HIRING_KEYWORDS = ("careers", "career", "jobs", "job", "recruitment", "recruiter", "recruit", "hiring",
                   "hr", "talent", "internships", "internship", "apply", "india", "official", "join",
                   "team", "work", "vacancy", "openings")
_CONFUSABLES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ѕ": "s", "ј": "j",
    "ԁ": "d", "ɡ": "g", "ο": "o", "ν": "v", "ı": "i", "0": "o", "1": "l", "3": "e", "4": "a", "5": "s",
    "7": "t", "$": "s", "@": "a"})
DISPOSABLE_DOMAINS = {"mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com", "temp-mail.org",
                      "yopmail.com", "trashmail.com", "sharklasers.com", "getnada.com", "dispostable.com"}
CAVEAT = ("High similarity does not by itself prove malicious intent; the domain may be owned by the company "
          "but could not be confirmed as official.")


def skeleton(text: str) -> str:
    """Collapse look-alike characters/digits into plain letters for comparison ('micr0soft' -> 'microsoft')."""
    s = unicodedata.normalize("NFKC", (text or "").lower()).translate(_CONFUSABLES)
    s = s.replace("rn", "m").replace("vv", "w")
    return re.sub(r"[^a-z]", "", s)


def decode_host(host: str) -> str:
    """Decode punycode (xn--) hosts to Unicode when possible."""
    try:
        return host.encode("ascii").decode("idna") if "xn--" in host else host
    except (UnicodeError, ValueError):
        return host


def is_disposable(domain: str) -> bool:
    """True if the email domain is a known disposable-mail provider."""
    return registrable_domain(domain) in DISPOSABLE_DOMAINS


def brand_in_text(text: str, brand_norm: str) -> bool:
    """True when the (skeletonised) text contains the brand (brand must be >= 4 letters)."""
    b = skeleton(brand_norm)
    return len(b) >= 4 and b in skeleton(text)


def analyze_domain(official_domain: Optional[str], provided: Optional[str]) -> Dict:
    """Compare provided domain/URL with the official domain.

    Returns dict: status (verified|mismatch|not_checked), official_domain_match, similarity (0-100),
    lookalike, techniques, risk (LOW|MEDIUM|HIGH), impersonation_likelihood, reasons, caveat.
    """
    host = decode_host(get_domain(provided or ""))
    out = {"provided_domain": host or None, "expected_domain": official_domain, "status": "not_checked",
           "official_domain_match": False, "similarity": 0, "lookalike": False, "techniques": [],
           "risk": "LOW", "impersonation_likelihood": "LOW", "reasons": [], "caveat": CAVEAT}
    if not host or not official_domain:
        return out
    reg_p, reg_o = registrable_domain(host), registrable_domain(official_domain)
    if reg_p == reg_o:
        out.update(status="verified", official_domain_match=True, similarity=100)
        out["reasons"].append(f"{host} belongs to the official domain {reg_o}.")
        return out
    out["status"] = "mismatch"
    label_p, label_o = domain_label(reg_p), domain_label(reg_o)
    brand, prov = skeleton(label_o), skeleton(label_p)
    tech: List[str] = []
    if "xn--" in get_domain(provided or "") or any(ord(c) > 127 for c in host):
        tech.append("homograph")
    if brand and prov == brand:
        tech.append("character_substitution" if "homograph" not in tech else "homograph_match")
        sim = 0.98
    elif brand and brand in prov and (len(brand) >= 4 or prov.replace(brand, "", 1) in HIRING_KEYWORDS):
        rem = prov.replace(brand, "", 1)
        tech.append("brand_plus_hiring_keyword" if any(k in rem for k in HIRING_KEYWORDS) else "brand_embedded")
        sim = 0.80 + 0.20 * len(brand) / max(len(prov), 1)
    else:
        sim = difflib.SequenceMatcher(None, prov, brand).ratio() if len(brand) >= 4 else 0.0
        if sim >= 0.8:
            tech.append("typosquat")
    sub = host[: -len(reg_p)].strip(".").split(".") if host != reg_p else []
    if brand and any(x and (skeleton(x) == brand or (len(brand) >= 4 and brand in skeleton(x))) for x in sub):
        tech.append("subdomain_spoof"); sim = max(sim, 0.95)
    if "-" in label_p and brand and brand in prov and sim >= 0.78:
        tech.append("misleading_hyphen")
    if reg_p.rsplit(".", 1)[-1] in SUSPICIOUS_TLDS:
        tech.append("suspicious_tld")
    out["techniques"], out["similarity"] = tech, round(sim * 100)
    out["lookalike"] = sim >= 0.78 or "subdomain_spoof" in tech or ("homograph" in tech and sim >= 0.6)
    strong = {"homograph", "homograph_match", "character_substitution", "brand_plus_hiring_keyword", "subdomain_spoof"}
    if out["lookalike"]:
        high = bool(strong & set(tech)) or sim >= 0.9
        out["risk"] = "HIGH" if high else "MEDIUM"
        out["impersonation_likelihood"] = out["risk"]
        out["reasons"].append(f"{host} is not the official domain ({reg_o}) but closely resembles it "
                              f"({out['similarity']}% similar; {', '.join(t.replace('_', ' ') for t in tech)}).")
    else:
        out["risk"] = "MEDIUM"
        out["reasons"].append(f"{host} is unrelated to the official domain ({reg_o}).")
    return out
