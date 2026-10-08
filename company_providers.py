"""Pluggable company-verification providers. All API keys are optional.

Each provider returns a ProviderResult; failures never raise to the caller.
"""
import ipaddress
import logging
import re
import socket
import time
from html.parser import HTMLParser
from typing import Dict, List, Optional
from urllib import robotparser
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from typing import List, Optional

import config
from company_utils import (get_domain, name_domain_relationship, normalize_name,
                           registrable_domain)

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


@dataclass
class ProviderResult:
    """Evidence returned by one provider."""
    provider: str
    available: bool = True               # False = provider could not run
    found: Optional[bool] = None         # company recognised?
    website: Optional[str] = None
    official_domain: Optional[str] = None
    facts: dict = field(default_factory=dict)
    sources: List[dict] = field(default_factory=list)   # [{"title","url"}]
    notes: List[str] = field(default_factory=list)


class CompanyVerificationProvider:
    """Base class. Subclasses implement verify()."""
    name = "base"

    def verify(self, display_name, normalized_name, website=None):
        """Return ProviderResult for the company (never raise)."""
        raise NotImplementedError


def is_online(timeout=1.5):
    """Cheap connectivity probe (DNS server TCP connect). False in offline mode."""
    if config.OFFLINE_MODE:
        return False
    for host in (("1.1.1.1", 53), ("8.8.8.8", 53)):
        try:
            socket.create_connection(host, timeout=timeout).close()
            return True
        except OSError:
            continue
    return False


# Small offline knowledge base of well-known employers (NOT a scam list):
# used only as positive identity evidence when the network is unavailable.
KNOWN_COMPANIES = {
    "google": ("google.com", ["alphabet", "google india", "google llc"]),
    "microsoft": ("microsoft.com", ["microsoft india", "microsoft corporation"]),
    "amazon": ("amazon.com", ["amazon india", "amazon web services", "aws", "amazon.in"]),
    "apple": ("apple.com", []),
    "meta": ("meta.com", ["facebook"]),
    "tcs": ("tcs.com", ["tata consultancy services", "tata consultancy services limited"]),
    "infosys": ("infosys.com", ["infosys limited"]),
    "wipro": ("wipro.com", ["wipro limited"]),
    "hcl": ("hcltech.com", ["hcl technologies", "hcltech"]),
    "accenture": ("accenture.com", []),
    "ibm": ("ibm.com", ["international business machines"]),
    "oracle": ("oracle.com", ["oracle india"]),
    "adobe": ("adobe.com", ["adobe systems"]),
    "intel": ("intel.com", []),
    "nvidia": ("nvidia.com", []),
    "cognizant": ("cognizant.com", ["cognizant technology solutions"]),
    "deloitte": ("deloitte.com", []),
    "flipkart": ("flipkart.com", []),
    "zomato": ("zomato.com", []),
    "razorpay": ("razorpay.com", []),
}


def lookup_known_company(normalized_name):
    """Return (key, official_domain) if the name matches a known employer/alias."""
    n = normalized_name
    if not n:
        return None
    for key, (domain, aliases) in KNOWN_COMPANIES.items():
        names = {key} | {normalize_name(a) for a in aliases}
        if n in names:
            return key, domain
    return None


class KnownCompanyProvider(CompanyVerificationProvider):
    """Offline alias/domain table for widely known employers."""
    name = "offline-knowledge"

    def verify(self, display_name, normalized_name, website=None):
        hit = lookup_known_company(normalized_name)
        if not hit:
            return ProviderResult(self.name, found=None,
                                  notes=["Not in the built-in list of well-known employers."])
        key, domain = hit
        return ProviderResult(
            self.name, found=True, website="https://www." + domain, official_domain=domain,
            facts={"known_brand": True, "alias_match": normalized_name != key},
            sources=[{"title": "Built-in well-known employer reference", "url": ""}])


class WebsiteProvider(CompanyVerificationProvider):
    """Fetches the website (user-provided or the known domain) and inspects it."""
    name = "website-check"

    def __init__(self, timeout=None):
        self.timeout = timeout or config.HTTP_TIMEOUT

    def verify(self, display_name, normalized_name, website=None):
        if not website:
            return ProviderResult(self.name, available=True, found=None,
                                  notes=["No website supplied or discovered."])
        if requests is None or not is_online():
            return ProviderResult(self.name, available=False,
                                  notes=["Website could not be checked (offline)."])
        domain = get_domain(website)
        facts = {"domain": domain, "resolves": False, "https": False}
        try:
            facts["resolves"] = bool(socket.gethostbyname(domain))
        except OSError:
            return ProviderResult(self.name, found=False, facts=facts,
                                  notes=[f"Domain {domain} does not resolve."])
        url = website if website.lower().startswith("http") else "https://" + website
        try:
            r = requests.get(url, timeout=self.timeout, allow_redirects=True,
                             headers={"User-Agent": "InternShieldAI/1.0 (verification)"})
            facts["https"] = r.url.lower().startswith("https://")
            facts["status"] = r.status_code
            facts["final_domain"] = registrable_domain(get_domain(r.url))
            body = r.text[:200000].lower() if "text" in r.headers.get("content-type", "") else ""
            title = re.search(r"<title[^>]*>(.*?)</title>", body, re.S)
            facts["title"] = re.sub(r"\s+", " ", title.group(1)).strip()[:120] if title else ""
            first = normalized_name.split()[0] if normalized_name else ""
            facts["name_on_site"] = bool(first) and first in body
            facts["has_about"] = bool(re.search(r"about( us)?|our story|who we are", body))
            facts["has_contact"] = bool(re.search(r"contact( us)?|get in touch", body))
            facts["parked"] = bool(re.search(r"domain (is )?for sale|buy this domain|parked", body))
            return ProviderResult(self.name, found=r.status_code < 400, website=r.url,
                                  official_domain=registrable_domain(get_domain(r.url)),
                                  facts=facts, sources=[{"title": "Company website", "url": r.url}])
        except Exception as e:  # timeouts, SSL, connection errors
            facts["error"] = type(e).__name__
            return ProviderResult(self.name, found=False, facts=facts,
                                  notes=[f"Website could not be fetched ({type(e).__name__})."])


log = logging.getLogger("internshield.providers")

# Vocabulary for every check: verified | unverified | not_found | unavailable | not_checked
VERIFIED, UNVERIFIED, NOT_FOUND, UNAVAILABLE, NOT_CHECKED = "verified", "unverified", "not_found", "unavailable", "not_checked"
_INJECTION = re.compile(r"ignore (all |any )?(previous|prior|above) instructions|disregard .{0,30}instructions|system prompt|you are now", re.I)


def sanitize_text(s: str, limit: int = 200) -> str:
    """Strip control chars/markup and truncate. Web text is DATA, never instructions."""
    s = re.sub(r"[\x00-\x1f\x7f<>]", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()[:limit]


# ------------------------------------------------------------ search backends
@dataclass
class SearchHit:
    """One search result."""
    title: str
    url: str
    snippet: str = ""


@dataclass
class SearchResponse:
    """Search result list + optional knowledge panel; ok=False means the provider failed."""
    hits: List[SearchHit] = field(default_factory=list)
    knowledge: dict = field(default_factory=dict)
    ok: bool = True
    error: Optional[str] = None


class SearchBackend:
    """Interface for a web-search provider. Add new providers by subclassing."""
    name = "search"

    def available(self) -> bool:
        """True when the backend is configured (API key present)."""
        return False

    def search(self, query: str, num: int = 8) -> SearchResponse:
        """Run a query. Must not raise; return ok=False on failure."""
        raise NotImplementedError


class SerperBackend(SearchBackend):
    """Serper.dev Google-results API. Key: SEARCH_API_KEY (or SERPER_API_KEY)."""
    name = "serper"

    def available(self) -> bool:
        return bool(config.get_search_key()) and requests is not None

    def search(self, query, num=8):
        key = config.get_search_key()
        if not key or requests is None:
            return SearchResponse(ok=False, error="not configured")
        try:
            r = requests.post("https://google.serper.dev/search", headers={"X-API-KEY": key, "Content-Type": "application/json"},
                              json={"q": query, "num": num}, timeout=config.HTTP_TIMEOUT)
            r.raise_for_status()
            j = r.json()
            hits = [SearchHit(sanitize_text(x.get("title"), 120), x.get("link", ""), sanitize_text(x.get("snippet"), 240))
                    for x in j.get("organic", []) if str(x.get("link", "")).startswith("http")]
            return SearchResponse(hits=hits, knowledge=j.get("knowledgeGraph") or {})
        except Exception as e:  # network/auth/quota - never leak the key
            log.warning("search failed: %s", type(e).__name__)
            return SearchResponse(ok=False, error=type(e).__name__)


def get_search_backend() -> Optional[SearchBackend]:
    """Configured backend or None (offline / no key)."""
    b = SerperBackend()
    return b if b.available() else None


class CachedSearch:
    """Wraps a backend with timestamped caching and an honest log of what actually ran."""

    def __init__(self, backend: Optional[SearchBackend], use_cache: bool = True):
        self.backend, self.use_cache = backend, use_cache
        self.ran: List[str] = []
        self.failed = 0
        self.timestamps: List[float] = []

    @property
    def available(self) -> bool:
        return self.backend is not None

    def search(self, query: str, cache: bool = True) -> SearchResponse:
        """Search (cache=False for anything involving a person's name)."""
        from cache_store import cache_get, cache_put
        if not self.backend:
            return SearchResponse(ok=False, error="unavailable")
        key = "search:" + hashlib_sha(query)
        if cache and self.use_cache:
            hit = cache_get(key)
            if hit:
                self.timestamps.append(hit[1])
                v = hit[0]
                return SearchResponse([SearchHit(**h) for h in v["hits"]], v["knowledge"])
        resp = self.backend.search(query)
        self.ran.append(query if cache else "[recruiter query]")
        self.timestamps.append(time.time())
        if not resp.ok:
            self.failed += 1
        elif cache and self.use_cache:
            cache_put(key, {"hits": [h.__dict__ for h in resp.hits], "knowledge": resp.knowledge})
        return resp


def hashlib_sha(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()[:20]


# ------------------------------------------------------------- safe web fetch
@dataclass
class Page:
    """Fetched page (untrusted). status: verified(fetched) | unavailable | not_checked(blocked/robots)."""
    url: str
    status: str = UNAVAILABLE
    final_url: str = ""
    http_status: int = 0
    title: str = ""
    text: str = ""
    links: List[tuple] = field(default_factory=list)
    reason: str = ""


class _Parse(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.links, self.text, self._skip, self._in_title, self._href = "", [], [], 0, False, None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "a":
            self._href = dict(attrs).get("href")
            self.links.append([self._href or "", ""])

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = max(0, self._skip - 1)
        elif tag == "title":
            self._in_title = False
        elif tag == "a":
            self._href = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._skip:
            return
        self.text.append(data)
        if self._href is not None and self.links:
            self.links[-1][1] += data


def parse_html(html_text: str, base_url: str = "") -> dict:
    """Pure parser (no network): title, visible text (lowercase), absolute links."""
    p = _Parse()
    try:
        p.feed(html_text or "")
    except Exception:  # malformed HTML
        pass
    links = [(urljoin(base_url, h) if h else "", sanitize_text(t, 80).lower()) for h, t in p.links if h]
    return {"title": sanitize_text(p.title, 150), "text": re.sub(r"\s+", " ", " ".join(p.text)).lower()[:150000], "links": links}


def check_public_host(host: str):
    """(ok, reason). Blocks localhost/private/link-local targets (SSRF guard) and unresolvable hosts."""
    if not host:
        return False, "no host"
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False, "does not resolve"
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False, "blocked: non-public address"
    return True, ""


def robots_allows(url: str) -> bool:
    """Respect robots.txt (allow when robots.txt is missing/unreachable)."""
    try:
        p = urlparse(url)
        r = requests.get(f"{p.scheme}://{p.netloc}/robots.txt", timeout=config.HTTP_TIMEOUT,
                         headers={"User-Agent": config.USER_AGENT})
        if r.status_code != 200:
            return True
        rp = robotparser.RobotFileParser()
        rp.parse(r.text.splitlines())
        return rp.can_fetch("InternShieldAI", url)
    except Exception:
        return True


def fetch_page(url: str, check_robots: bool = True) -> Page:
    """Fetch one page politely: public hosts only, robots.txt honoured, size-capped, redirects re-checked."""
    pg = Page(url=url)
    if requests is None:
        pg.reason = "requests not installed"; return pg
    cur = url
    try:
        if check_robots and not robots_allows(url):
            pg.status, pg.reason = NOT_CHECKED, "robots.txt disallows automated access"; return pg
        for _ in range(5):
            ok, why = check_public_host(urlparse(cur).hostname or "")
            if not ok:
                pg.reason = why; return pg
            r = requests.get(cur, timeout=config.HTTP_TIMEOUT, allow_redirects=False, stream=True,
                             headers={"User-Agent": config.USER_AGENT})
            if r.is_redirect and r.headers.get("location"):
                cur = urljoin(cur, r.headers["location"]); continue
            body = r.raw.read(config.MAX_PAGE_BYTES, decode_content=True)
            pg.final_url, pg.http_status = cur, r.status_code
            if "html" in r.headers.get("content-type", "html") or not r.headers.get("content-type"):
                d = parse_html(body.decode(r.encoding or "utf-8", "ignore"), cur)
                pg.title, pg.text, pg.links = d["title"], d["text"], d["links"]
            pg.status = VERIFIED if r.status_code < 400 else NOT_FOUND
            return pg
        pg.reason = "too many redirects"
    except Exception as e:
        pg.reason = type(e).__name__
    return pg


_ADDR = re.compile(r"\b(\d{1,5}[ ,]+[a-z0-9 .]{3,40}(street|st\.|road|rd\.|avenue|ave\.|lane|floor|suite|tower|nagar|sector)\b|pin(code)?\s*[:\-]?\s*\d{6}|\b\d{6}\b.{0,20}india|registered office)", re.I)


class SiteInspector:
    """Inspects an official-website candidate (about/contact/careers/legal/LinkedIn/consistency)."""

    def inspect(self, url: str, normalized_name: str, recruiter_name: Optional[str] = None) -> Dict:
        """Return facts dict with `status` (verified|not_found|unavailable|not_checked) and findings."""
        pg = fetch_page(url)
        facts: Dict = {"status": pg.status, "url": url, "reason": pg.reason, "final_url": pg.final_url or None}
        if pg.status != VERIFIED:
            return facts
        reg_start, reg_final = registrable_domain(get_domain(url)), registrable_domain(get_domain(pg.final_url))
        toks = [t for t in (normalized_name or "").split() if len(t) > 2]
        hits = sum(t in pg.text or t in pg.title.lower() for t in toks)
        links = pg.links
        def link(rx):
            for h, t in links:
                if re.search(rx, h.lower() + " " + t):
                    return h
        li = next((h for h, _ in links if re.search(r"linkedin\.com/company/", h.lower())), None)
        emails = set(re.findall(r"[a-z0-9._%+\-]+@([a-z0-9\-]+(?:\.[a-z0-9\-]+)+)", pg.text))
        facts.update({
            "final_domain": reg_final, "cross_domain_redirect": reg_start != reg_final,
            "https": pg.final_url.startswith("https://"), "http_status": pg.http_status,
            "title": pg.title, "name_on_site": bool(toks) and hits / len(toks) >= 0.6,
            "has_about": bool(link(r"about|who we are|our story")), "has_contact": bool(link(r"contact|get in touch")),
            "careers_url": link(r"career|jobs|join us|work with us"), "linkedin_url": li,
            "has_legal": bool(re.search(r"privacy policy|terms (of|&) (use|service)|©|copyright|registered office|\bcin\b", pg.text)),
            "has_address": bool(_ADDR.search(pg.text)),
            "site_email_domains": sorted(registrable_domain(e) for e in emails)[:5],
            "parked": bool(re.search(r"domain (is )?for sale|buy this domain|this domain may be for sale|parked", pg.text)),
            "instruction_like_text_ignored": bool(_INJECTION.search(pg.text)),
            "recruiter_name_on_site": bool(recruiter_name) and all(p in pg.text for p in recruiter_name.lower().split()),
        })
        return facts


class DomainProvider:
    """DNS + public RDAP (keyless) domain facts. RDAP availability varies by TLD; failures are reported."""

    def check(self, domain: str) -> Dict:
        """Return dict: dns (verified|not_found|unavailable), age_days, registered, registrar, age_status."""
        out = {"domain": domain, "dns": UNAVAILABLE, "age_status": NOT_CHECKED, "age_days": None, "registrar": None}
        try:
            socket.getaddrinfo(domain, None); out["dns"] = VERIFIED
        except socket.gaierror:
            out["dns"] = NOT_FOUND
        except OSError:
            out["dns"] = UNAVAILABLE
        if not config.RDAP_ENABLED or requests is None or out["dns"] == UNAVAILABLE:
            return out
        try:
            r = requests.get(f"https://rdap.org/domain/{registrable_domain(domain)}", timeout=config.HTTP_TIMEOUT,
                             headers={"User-Agent": config.USER_AGENT})
            if r.status_code == 200:
                j = r.json()
                reg = next((e["eventDate"] for e in j.get("events", []) if e.get("eventAction") == "registration"), None)
                if reg:
                    from datetime import datetime, timezone
                    d = datetime.fromisoformat(reg.replace("Z", "+00:00"))
                    out.update(age_days=(datetime.now(timezone.utc) - d).days, age_status=VERIFIED, registered=reg[:10])
                else:
                    out["age_status"] = UNAVAILABLE
            else:
                out["age_status"] = UNAVAILABLE
        except Exception:
            out["age_status"] = UNAVAILABLE
        return out


def _tokens(s: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9\+#]+", (s or "").lower()) if len(t) > 2 and t not in {"the", "and", "for", "with"}]


class CareersProvider:
    """Looks for a job on the OFFICIAL domain (careers page probes + site: search)."""

    def find(self, official_domain: str, careers_url: Optional[str], job_title: Optional[str], job_url: Optional[str],
             normalized_name: str, search: Optional[CachedSearch], recruiter_name: Optional[str] = None) -> Dict:
        """Return dict(status, careers_page, job_title_match, company_match, location_match, recruiter_listed, urls)."""
        out = {"status": NOT_CHECKED, "careers_page": NOT_CHECKED, "job_title_match": NOT_CHECKED, "company_match": NOT_CHECKED,
               "location_match": NOT_CHECKED, "recruiter_listed": NOT_CHECKED, "urls": []}
        if not official_domain:
            return out
        reg = registrable_domain(official_domain)
        tt = _tokens(job_title)
        probes = []
        if job_url and registrable_domain(get_domain(job_url)) == reg:
            probes.append(job_url)
        if careers_url and registrable_domain(get_domain(careers_url)) == reg:
            probes.append(careers_url)
        probes += [f"https://careers.{reg}", f"https://www.{reg}/careers"]
        fetched = 0
        for u in list(dict.fromkeys(probes))[:4]:
            pg = fetch_page(u)
            if pg.status == VERIFIED:
                fetched += 1
                out["careers_page"] = VERIFIED
                out["urls"].append(pg.final_url)
                out["company_match"] = VERIFIED if any(t in pg.text for t in normalized_name.split() if len(t) > 2) else UNVERIFIED
                if tt and sum(t in pg.text for t in tt) / len(tt) >= 0.7:
                    out["job_title_match"] = VERIFIED
                if recruiter_name and all(p in pg.text for p in recruiter_name.lower().split()):
                    out["recruiter_listed"] = VERIFIED
        if out["careers_page"] != VERIFIED:
            out["careers_page"] = UNAVAILABLE if fetched == 0 and not probes else NOT_FOUND
        if tt and search and search.available and out["job_title_match"] != VERIFIED:
            resp = search.search(f"site:{reg} {job_title}")
            if resp.ok:
                for h in resp.hits:
                    if registrable_domain(get_domain(h.url)) == reg and sum(t in (h.title + " " + h.snippet).lower() for t in tt) / len(tt) >= 0.7:
                        out["job_title_match"] = VERIFIED; out["urls"].append(h.url); break
                else:
                    out["job_title_match"] = NOT_FOUND
            else:
                out["job_title_match"] = UNAVAILABLE
        if tt:
            jm = out["job_title_match"]
            out["status"] = VERIFIED if jm == VERIFIED else (NOT_FOUND if jm == NOT_FOUND or out["careers_page"] == VERIFIED else UNAVAILABLE)
        return out


_LI_PROFILE = re.compile(r"^https?://([a-z]{2,3}\.)?linkedin\.com/in/[\w\-%]{3,100}/?$", re.I)


class ProfessionalEvidenceProvider:
    """Public professional evidence for a recruiter via search results only (no LinkedIn scraping)."""

    def find(self, name: str, company: str, linkedin_url: Optional[str], search: Optional[CachedSearch],
             official_domain: Optional[str] = None) -> Dict:
        """Return dict(status, level none|medium|strong, profile_url, conflicting_employer, sources, linkedin_url_valid)."""
        out = {"status": NOT_CHECKED, "level": "none", "profile_url": None, "conflicting_employer": None, "sources": [],
               "linkedin_url_valid": None}
        if linkedin_url:
            out["linkedin_url_valid"] = bool(_LI_PROFILE.match(linkedin_url.strip()))
        if not name:
            return out
        if not search or not search.available:
            out["status"] = UNAVAILABLE; return out
        np_ = [p for p in re.findall(r"[a-z]+", name.lower()) if len(p) > 1]
        ct = [t for t in normalized_tokens(company)]
        any_ok = False
        for q in (f'"{name}" "{company}"', f'"{name}" LinkedIn {company}'):
            resp = search.search(q, cache=False)   # never cache person-related queries
            if not resp.ok:
                continue
            any_ok = True
            for h in resp.hits:
                blob = (h.title + " " + h.snippet).lower()
                if not all(p in blob for p in np_):
                    continue
                host = registrable_domain(get_domain(h.url))
                has_co = any(t in blob for t in ct)
                if official_domain and host == registrable_domain(official_domain) and has_co:
                    out.update(level="strong", status=VERIFIED); out["sources"].append({"title": h.title, "url": h.url, "kind": "official"})
                elif host == "linkedin.com" and "/in/" in h.url:
                    if has_co:
                        if out["level"] != "strong":
                            out.update(level="medium", status=VERIFIED, profile_url=h.url)
                        out["sources"].append({"title": h.title, "url": h.url, "kind": "profile"})
                    else:
                        m = re.search(r"\b(?:at|@)\s+([A-Z][\w&\. ]{2,30})", h.title + " " + h.snippet)
                        if m:
                            out["conflicting_employer"] = sanitize_text(m.group(1), 40)
        if out["status"] != VERIFIED:
            out["status"] = NOT_FOUND if any_ok else UNAVAILABLE
        return out


def normalized_tokens(company: str) -> List[str]:
    """Significant tokens of a normalised company name."""
    return [t for t in normalize_name(company).split() if len(t) > 2] or normalize_name(company).split()


class SearchProvider(CompanyVerificationProvider):
    """Legacy-compatible provider used by verify_company(): presence + scam mentions via CachedSearch."""
    name = "web-search"
    SCAM_WORDS = re.compile(r"\b(scam|fraud|fake|cheat|phishing|beware|complaint)\b", re.I)

    def __init__(self, search: Optional[CachedSearch] = None):
        self._search = search

    def verify(self, display_name, normalized_name, website=None):
        if not is_online():
            return ProviderResult(self.name, available=False, notes=["Search unavailable (offline)."])
        s = self._search or CachedSearch(get_search_backend())
        if not s.available:
            return ProviderResult(self.name, available=False, notes=["Search provider not configured (no API key)."])
        gen, rep = s.search(f'"{display_name}" company'), s.search(f'"{display_name}" internship scam OR fraud')
        if not (gen.ok or rep.ok):
            return ProviderResult(self.name, available=False, notes=["Search failed."])
        first = normalized_name.split()[0] if normalized_name else ""
        rel = [h for h in gen.hits if first and first in (h.title + h.url).lower()]
        scam = [h for h in rep.hits if first and first in (h.title + h.snippet).lower() and self.SCAM_WORDS.search(h.title + " " + h.snippet)]
        return ProviderResult(self.name, found=len(rel) >= 2, facts={"presence_results": len(rel), "scam_mentions": len(scam)},
                              sources=[{"title": h.title[:90], "url": h.url} for h in rel[:3] + scam[:2]])


def default_providers():
    """Providers used by verify_company() (offline knowledge first)."""
    return [KnownCompanyProvider(), WebsiteProvider(), SearchProvider()]
