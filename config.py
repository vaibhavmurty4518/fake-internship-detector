"""Central configuration for InternShield AI (weights, thresholds, cache, timeouts).

Every value can be overridden through environment variables so nothing needs
code changes. No secrets are stored here.
"""
import os


def _f(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return float(default)


# --- Aggregation weights (relative; re-normalised at runtime) -------------
INTERNSHIP_WEIGHT = _f("INTERNSHIP_WEIGHT", 0.55)
COMPANY_WEIGHT = _f("COMPANY_WEIGHT", 0.30)
CONTACT_WEIGHT = _f("CONTACT_WEIGHT", 0.15)

# Evidence below this confidence (0-100) still counts a little, never zero.
MIN_CONFIDENCE_INFLUENCE = _f("MIN_CONFIDENCE_INFLUENCE", 0.15)

# If the internship content model alone is at/above this, other layers can
# not pull the overall score more than STRONG_EVIDENCE_MAX_DISCOUNT below it.
STRONG_EVIDENCE_THRESHOLD = _f("STRONG_EVIDENCE_THRESHOLD", 70)
STRONG_EVIDENCE_MAX_DISCOUNT = _f("STRONG_EVIDENCE_MAX_DISCOUNT", 10)
IMPERSONATION_MIN_OVERALL = _f("IMPERSONATION_MIN_OVERALL", 65)

# --- Risk level thresholds (upper bound exclusive) -------------------------
RISK_LEVELS = [
    (20, "LOW RISK"),
    (40, "CAUTION"),
    (60, "SUSPICIOUS"),
    (80, "HIGH RISK"),
    (101, "VERY HIGH RISK"),
]

# --- Network / cache ---------------------------------------------------------
OFFLINE_MODE = os.getenv("INTERNSHIELD_OFFLINE", "").lower() in ("1", "true", "yes")
HTTP_TIMEOUT = _f("INTERNSHIELD_HTTP_TIMEOUT", 5)
CACHE_FILE = os.getenv("COMPANY_CACHE_FILE", "company_cache.json")
CACHE_TTL_HOURS = _f("COMPANY_CACHE_TTL_HOURS", 24)
# Privacy: user-submitted listing text is never persisted. Only company-level
# verification results are cached, and only when this is enabled.
CACHE_ENABLED = os.getenv("COMPANY_CACHE_ENABLED", "1").lower() in ("1", "true", "yes")

# --- Optional API keys (read lazily via os.getenv; never hardcoded) --------
SEARCH_API_KEY_ENV = "SERPER_API_KEY"


def risk_level(score):
    """Map a 0-100 score to a label using RISK_LEVELS."""
    s = max(0, min(100, float(score)))
    for upper, label in RISK_LEVELS:
        if s < upper:
            return label
    return RISK_LEVELS[-1][1]


def get_secret(name):
    """Return a key from env vars, falling back to Streamlit secrets if present."""
    val = os.getenv(name)
    if val:
        return val
    try:  # pragma: no cover - only inside Streamlit
        import streamlit as st
        return st.secrets.get(name)
    except Exception:
        return None


# ---- Investigation (v2) settings ---------------------------------------
# Search key: SEARCH_API_KEY preferred, SERPER_API_KEY accepted (Serper.dev).
SEARCH_KEY_ENVS = ("SEARCH_API_KEY", "SERPER_API_KEY")
MAX_PAGE_BYTES = int(_f("INTERNSHIELD_MAX_PAGE_BYTES", 400_000))
USER_AGENT = "InternShieldAI/2.0 (+company-verification; respects robots.txt)"
RDAP_ENABLED = os.getenv("INTERNSHIELD_RDAP", "1").lower() in ("1", "true", "yes")  # keyless public RDAP
IDENTITY_VERIFIED_MIN = _f("IDENTITY_VERIFIED_MIN", 70)
YOUNG_DOMAIN_DAYS = _f("YOUNG_DOMAIN_DAYS", 180)


def get_search_key():
    """First configured search API key (env or Streamlit secrets), else None."""
    for n in SEARCH_KEY_ENVS:
        v = get_secret(n)
        if v:
            return v
    return None
