"""Company identity resolution: find the REAL company behind a name from independent evidence.

The first search hit is never trusted. Candidates are scored by name/domain relationship,
cross-query corroboration, knowledge-panel agreement, independent sources and (later) website checks.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from company_providers import CachedSearch, lookup_known_company
from company_utils import get_domain, name_domain_relationship, normalize_name, registrable_domain

# Domains that are *about* companies, not their official site (used as independent evidence).
AGGREGATORS = {"wikipedia.org", "linkedin.com", "facebook.com", "twitter.com", "x.com", "instagram.com", "youtube.com",
               "crunchbase.com", "bloomberg.com", "reuters.com", "forbes.com", "glassdoor.com", "glassdoor.co.in",
               "indeed.com", "naukri.com", "ambitionbox.com", "zaubacorp.com", "tofler.in", "opencorporates.com",
               "economictimes.com", "techcrunch.com", "wikidata.org", "britannica.com", "medium.com", "quora.com",
               "reddit.com", "internshala.com", "trustpilot.com", "mca.gov.in", "sec.gov", "github.com"}


@dataclass
class Candidate:
    """A possible official identity for the entered company."""
    domain: str
    score: float = 0.0
    evidence: List[str] = field(default_factory=list)
    queries: set = field(default_factory=set)
    sources: List[dict] = field(default_factory=list)
    display_name: str = ""


@dataclass
class Identity:
    """Resolved company identity (fields None/'' when unknown)."""
    name: str
    normalized_name: str
    basis: str = "none"                 # live_search | user_supplied | offline_database | none
    official_domain: Optional[str] = None
    official_website: Optional[str] = None
    legal_name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    linkedin_url: Optional[str] = None
    careers_url: Optional[str] = None
    ambiguous: bool = False
    candidates: List[dict] = field(default_factory=list)
    independent_sources: List[dict] = field(default_factory=list)
    breakdown: Dict[str, str] = field(default_factory=dict)
    confidence: int = 0


def _tld_country(domain: str) -> Optional[str]:
    t = (domain or "").rsplit(".", 1)[-1]
    return {"in": "India", "uk": "United Kingdom", "de": "Germany", "au": "Australia", "ca": "Canada", "jp": "Japan",
            "sg": "Singapore", "fr": "France"}.get(t)


def resolve_identity(name: str, search: Optional[CachedSearch], user_website: Optional[str] = None) -> Identity:
    """Search for the company, score candidate domains and pick (or refuse to pick) an identity."""
    norm = normalize_name(name)
    ident = Identity(name=name, normalized_name=norm)
    if not norm:
        return ident
    toks = [t for t in norm.split() if len(t) > 2] or norm.split()
    cands: Dict[str, Candidate] = {}
    indep: Dict[str, dict] = {}
    knowledge: dict = {}

    def cand(dom):
        return cands.setdefault(dom, Candidate(domain=dom))

    known = lookup_known_company(norm)
    if known:
        c = cand(known[1]); c.score += 30; c.evidence.append("matches built-in well-known employer table")
    if user_website:
        d = registrable_domain(get_domain(user_website))
        if d:
            c = cand(d); c.score += 12; c.evidence.append("website supplied by user (not trusted by itself)")

    if search and search.available:
        qs = [f'"{name}"', f"{name} official website", f"{name} careers", f"{name} LinkedIn", f"{name} headquarters"]
        for q in qs:
            resp = search.search(q)
            if not resp.ok:
                continue
            if resp.knowledge and not knowledge and any(t in str(resp.knowledge.get("title", "")).lower() for t in toks):
                knowledge = resp.knowledge
            for rank, h in enumerate(resp.hits):
                dom = registrable_domain(get_domain(h.url))
                blob = (h.title + " " + h.snippet).lower()
                if dom in AGGREGATORS:
                    if any(t in blob for t in toks):
                        indep.setdefault(dom, {"title": h.title, "url": h.url, "domain": dom})
                    if dom == "linkedin.com" and "/company/" in h.url and not ident.linkedin_url and any(t in blob for t in toks):
                        ident.linkedin_url = h.url
                    continue
                rel = name_domain_relationship(norm, dom)
                if rel == "none" and not any(t in blob for t in toks):
                    continue
                c = cand(dom)
                c.queries.add(q)
                if h.url not in [s["url"] for s in c.sources]:
                    c.sources.append({"title": h.title, "url": h.url})
                if not c.display_name and h.title:
                    c.display_name = h.title
                if rel == "strong":
                    c.score += 12 if "relationship" not in " ".join(c.evidence) else 0
                    if "domain strongly matches name" not in c.evidence:
                        c.evidence.append("domain strongly matches name"); c.score += 22
                elif rel == "partial" and "domain partially matches name" not in c.evidence:
                    c.evidence.append("domain partially matches name"); c.score += 10
                if "official" in blob and rank < 3:
                    c.score += 5
                if q.endswith("official website") and rank == 0:
                    c.score += 12; c.evidence.append("top result for 'official website'")
                if any(t in h.title.lower() for t in toks):
                    c.score += 2
        for c in cands.values():
            if len(c.queries) >= 2:
                c.score += 4 * len(c.queries); c.evidence.append(f"appears across {len(c.queries)} independent queries")
        kw = (knowledge.get("website") or "")
        if kw:
            kd = registrable_domain(get_domain(kw))
            if kd:
                c = cand(kd); c.score += 28; c.evidence.append("knowledge panel lists this website")

    ranked = sorted(cands.values(), key=lambda c: -c.score)
    ident.candidates = [{"domain": c.domain, "score": round(c.score), "evidence": c.evidence, "sources": c.sources[:3]} for c in ranked[:4]]
    ident.independent_sources = list(indep.values())[:6]
    if knowledge:
        ident.industry = knowledge.get("type") or None
        ident.description = (knowledge.get("description") or "")[:240] or None
        attrs = knowledge.get("attributes") or {}
        ident.location = next((v for k, v in attrs.items() if "headquarter" in k.lower()), None)
        ident.legal_name = knowledge.get("title") or None
    if ranked and ranked[0].score >= 25:
        top = ranked[0]
        ident.official_domain, ident.official_website = top.domain, "https://" + ("www." if not top.domain.count(".") > 1 else "") + top.domain
        ident.ambiguous = len(ranked) > 1 and ranked[1].score >= 0.8 * top.score
        ident.country = _tld_country(top.domain)
        if top.queries:
            ident.basis = "live_search"
        elif known and registrable_domain(known[1]) == top.domain:
            ident.basis = "offline_database"
        else:
            ident.basis = "user_supplied"
    return ident


def finalize_confidence(ident: Identity, site: Optional[dict], domain_info: Optional[dict]) -> Identity:
    """Compute identity confidence (0-100) and the human-readable breakdown from all evidence."""
    if not ident.official_domain:
        ident.confidence, ident.breakdown = 0, {"Name match": "None", "Official website": "Not found", "Independent sources": "0"}
        return ident
    top = ident.candidates[0] if ident.candidates else {"evidence": []}
    ev = " ".join(top["evidence"])
    conf = 0
    nm = "Strong" if "strongly" in ev or "well-known" in ev else ("Partial" if "partially" in ev else "Weak")
    conf += {"Strong": 25, "Partial": 12, "Weak": 4}[nm]
    conf += 10  # a candidate official website exists
    reach = bool(site and site.get("status") == "verified")
    if reach:
        conf += 10
        conf += 12 if site.get("name_on_site") else 0
        conf += 5 if (site.get("has_about") or site.get("has_contact") or site.get("has_legal")) else 0
        conf += 3 if site.get("linkedin_url") else 0
    n_src = len(ident.independent_sources)
    conf += min(n_src, 4) * 5
    if "independent queries" in ev:
        conf += 8
    if "knowledge panel" in ev:
        conf += 10
    if "well-known" in ev and ident.basis == "offline_database":
        conf += 30
    if ident.ambiguous:
        conf -= 15
    if ident.basis == "offline_database" and not reach:
        conf = max(conf, 70)
    if ident.basis in ("offline_database", "user_supplied") and not reach:
        conf = min(conf, 75 if ident.basis == "offline_database" else 45)
    ident.confidence = max(0, min(100, conf))
    ident.breakdown = {
        "Name match": nm, "Official website": "Found" if ident.official_website else "Not found",
        "Domain relationship": nm, "Independent sources": str(n_src),
        "Website reachable": "Yes" if reach else ("Not checked" if not site or site.get("status") in (None, "not_checked", "unavailable") else "No"),
        "Company presence": "Strong" if n_src >= 3 else ("Some" if n_src else "Limited"),
    }
    return ident
