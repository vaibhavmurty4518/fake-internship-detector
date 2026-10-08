"""Deterministic helpers: company-name extraction/normalisation, email & URL parsing."""
import re
from urllib.parse import urlparse

FREE_EMAIL_PROVIDERS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.in", "yahoo.co.in",
    "outlook.com", "hotmail.com", "live.com", "rediffmail.com", "aol.com",
    "icloud.com", "protonmail.com", "proton.me", "mail.com", "yandex.com",
    "zoho.com", "gmx.com", "blogspot.com",
}
URL_SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "forms.gle", "is.gd",
                  "cutt.ly", "rb.gy", "shorturl.at", "wa.me"}
JOB_BOARDS = {"linkedin.com", "indeed.com", "internshala.com", "naukri.com",
              "glassdoor.com", "unstop.com", "wellfound.com", "foundit.in",
              "letsintern.com", "lever.co", "greenhouse.io", "workday.com",
              "myworkdayjobs.com", "smartrecruiters.com"}
MULTI_PART_TLDS = {"co.in", "co.uk", "com.au", "org.in", "net.in", "ac.in",
                   "com.br", "co.jp", "co.za", "gov.in", "edu.in"}
SUSPICIOUS_TLDS = {"xyz", "top", "click", "work", "tk", "ml", "ga", "cf", "gq",
                   "buzz", "monster", "icu", "rest", "loan", "cam"}

_SUFFIXES = {
    "pvt", "private", "ltd", "limited", "llc", "llp", "inc", "incorporated",
    "corp", "corporation", "co", "company", "plc", "gmbh", "pte", "sa", "ag",
}
_GEO_SUFFIXES = {"india", "global", "worldwide", "international", "technologies india"}

_LABELS = r"(?:company(?: name)?|organi[sz]ation|hiring company|employer|about the company|about us|firm|hiring organi[sz]ation)"
_LABEL_RE = re.compile(rf"(?im)^\s*[\-\*•]?\s*{_LABELS}\s*[:\-–]\s*(.+?)\s*$")
_PHRASE_RES = [
    re.compile(r"(?:^|[\.\n]\s*)(?:about\s+)?([A-Z][\w&\.\-]*(?:\s+[A-Z&][\w&\.\-]*){0,4})\s+is\s+(?:a|an|the)\s+(?:leading|growing|global|fast|top|series|well|small|new|reputed|pioneering|[a-z\-]+)", 0),
    re.compile(r"\b(?i:join|joining)\s+([A-Z][\w&\.\-]*(?:\s+[A-Z&][\w&\.\-]*){0,4})\b"),
    re.compile(r"\b(?:at|with)\s+([A-Z][\w&\.\-]*(?:\s+[A-Z&][\w&\.\-]*){0,3}\s+(?:Pvt\.?\s*Ltd\.?|Private Limited|Ltd\.?|LLC|Inc\.?|Technologies|Solutions|Systems|Labs|Corporation))"),
    re.compile(r"\b([A-Z][\w&\.\-]*(?:\s+[A-Z&][\w&\.\-]*){0,3}\s+(?:Pvt\.?\s*Ltd\.?|Private Limited|Ltd\.?|LLC|Inc\.?))"),
]
_STOP_CAPS = {"We", "The", "Our", "You", "This", "Apply", "About", "Role", "Requirements",
              "Join", "Internship", "Intern", "Software", "Engineering", "Important", "Note"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")
URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>\"')\]]+")


def normalize_name(name):
    """Lowercase, strip punctuation and legal suffixes (Pvt Ltd/LLC/Inc...).

    'ABC Technologies Pvt. Ltd.' -> 'abc technologies'
    """
    if not name:
        return ""
    s = name.lower().replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)
    toks = [t for t in s.split() if t]
    while toks and toks[-1] in _SUFFIXES:
        toks.pop()
    toks = [t for t in toks if t not in {"pvt", "private"} or len(toks) <= 1]
    # drop trailing geography words ("microsoft india")
    while len(toks) > 1 and toks[-1] in {"india", "global", "worldwide", "international"}:
        toks.pop()
    return re.sub(r"\s+", " ", " ".join(toks)).strip()


def _clean_display(name):
    name = re.sub(r"\s+", " ", name or "").strip(" \t-–:,;|")
    name = re.split(r"\s+[\|•]\s+|\s+-\s+(?=[a-z])", name)[0]
    return name[:80].strip()


def extract_company(text, explicit=None):
    """Extract a company name. Returns dict(display_name, normalized_name, method).

    Order: explicit field -> labelled line ("Company: X") -> phrase patterns ->
    email/website domain hint. method is 'none' when nothing is found.
    """
    if explicit and explicit.strip():
        d = _clean_display(explicit)
        return {"display_name": d, "normalized_name": normalize_name(d), "method": "explicit"}
    text = text or ""
    m = _LABEL_RE.search(text)
    if m:
        d = _clean_display(m.group(1))
        if d and len(d) > 1:
            return {"display_name": d, "normalized_name": normalize_name(d), "method": "labelled"}
    for rx in _PHRASE_RES:
        for mm in rx.finditer(text):
            d = _clean_display(mm.group(1))
            first = d.split(" ")[0] if d else ""
            if d and first not in _STOP_CAPS and len(normalize_name(d)) > 1:
                return {"display_name": d, "normalized_name": normalize_name(d), "method": "pattern"}
    return {"display_name": "", "normalized_name": "", "method": "none"}


def extract_emails(text):
    """Return all email addresses found in text (order preserved, deduped)."""
    seen, out = set(), []
    for e in EMAIL_RE.findall(text or ""):
        e = e.rstrip(".").lower()
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def extract_urls(text):
    """Return URLs found in free text, normalised with a scheme."""
    out = []
    for u in URL_RE.findall(text or ""):
        u = u.rstrip(".,;")
        out.append(u if u.lower().startswith("http") else "http://" + u)
    return out


def validate_email(email):
    """True when the string is a plausible single email address."""
    return bool(email) and bool(re.fullmatch(EMAIL_RE.pattern, email.strip()))


def normalize_url(url):
    """Return (normalised_url, error). Accepts bare domains; rejects junk."""
    if not url or not url.strip():
        return None, None
    u = url.strip()
    if re.search(r"\s", u):
        return None, "URL contains spaces"
    if not re.match(r"(?i)^https?://", u):
        u = "https://" + u
    p = urlparse(u)
    host = (p.hostname or "").lower()
    if not host or "." not in host or not re.fullmatch(r"[a-z0-9\.\-]+", host) \
            or host.startswith(".") or host.endswith(".") or ".." in host:
        return None, "URL does not look like a valid web address"
    return u, None


def get_domain(url_or_host):
    """Hostname of a URL (without leading www.) or '' if unparsable."""
    if not url_or_host:
        return ""
    s = url_or_host if "//" in url_or_host else "//" + url_or_host
    try:
        host = (urlparse(s).hostname or "").lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def registrable_domain(host):
    """Approximate registrable domain: 'careers.tcs.com' -> 'tcs.com'."""
    host = get_domain(host)
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    last2 = ".".join(parts[-2:])
    if last2 in MULTI_PART_TLDS and len(parts) >= 3:
        return ".".join(parts[-3:])
    return last2


def email_domain(email):
    """Domain part of an email address ('' if invalid)."""
    return email.split("@", 1)[1].lower() if email and "@" in email else ""


def is_free_email_domain(domain):
    """True if domain belongs to a free/personal email provider."""
    return registrable_domain(domain) in FREE_EMAIL_PROVIDERS or domain in FREE_EMAIL_PROVIDERS


def _label(domain):
    d = registrable_domain(domain)
    parts = d.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in MULTI_PART_TLDS:
        return parts[-3]
    return parts[0] if parts else ""


def name_domain_relationship(normalized_name, domain):
    """Score how well a domain corresponds to a company name.

    Returns 'strong' | 'partial' | 'none'. Compares the domain label with the
    concatenated name, initialism and individual words.
    """
    if not normalized_name or not domain:
        return "none"
    label = re.sub(r"[^a-z0-9]", "", _label(domain))
    words = normalized_name.split()
    joined = "".join(words)
    initials = "".join(w[0] for w in words)
    if not label:
        return "none"
    if label == joined or label == words[0] and len(words) == 1 or (len(initials) >= 2 and label == initials):
        return "strong"
    if joined.startswith(label) and len(label) >= 4 or label.startswith(joined) and len(joined) >= 4:
        return "strong" if label == joined else "partial"
    if len(words[0]) >= 4 and (words[0] in label or label in words[0] and len(label) >= 4):
        return "partial"
    return "none"


def names_related(a, b):
    """True if two normalized names plausibly refer to the same organisation."""
    if not a or not b:
        return False
    if a == b:
        return True
    ta, tb = a.split(), b.split()
    return ta[0] == tb[0] and len(ta[0]) >= 3 and (len(ta) == 1 or len(tb) == 1 or a.startswith(b) or b.startswith(a))


domain_label = _label  # public alias: 'careers.tcs.co.in' -> 'tcs'
