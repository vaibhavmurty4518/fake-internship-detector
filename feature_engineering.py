"""
feature_engineering.py
-----------------------
Builds hand-crafted, RULE-BASED structured features from the raw text of a
job/internship posting. These features are combined with TF-IDF text
features before being passed to the ML classifiers.

Design note (Engineering Principle: Explainability by design):
Every structured feature here maps directly to a human-readable
"suspicious indicator" that is shown to the end user in the Streamlit
app (see app.py -> explain_indicators()). Keeping these two things
(the feature and its plain-English explanation) tied together in one
place makes the system auditable and avoids a black-box "fake=1"
output.

IMPORTANT (Ethics): thresholds below (e.g. what counts as an
"unusually high" stipend) are HEURISTICS chosen using general domain
reasoning about Indian/global internship stipends, NOT statistics
derived from the EMSCAD training dataset. The EMSCAD 'salary_range'
column encodes annual salary ranges in mixed currencies for a mix of
countries and job types, and is far too sparse/inconsistent to be used
to derive a reliable "expected stipend range" for arbitrary pasted
text. We say so explicitly in the README/UI rather than pretending the
threshold is something it isn't.
"""

import re
import numpy as np

# ---------------------------------------------------------------------------
# Keyword / pattern banks
# ---------------------------------------------------------------------------

FEE_PATTERNS = [
    r"registration fee", r"processing fee", r"security deposit",
    r"refundable fee", r"refundable deposit", r"training fee",
    r"joining fee", r"pay\s*(rs\.?|inr|₹|\$)\s*\d+", r"nominal fee",
    r"deposit of", r"one[- ]time payment", r"pay to apply",
    r"kit fee", r"caution money", r"advance payment", r"activation fee",
]

URGENCY_PATTERNS = [
    r"limited seats", r"apply today", r"apply now", r"hurry",
    r"only \d+ (seats|slots|spots)", r"immediate joining",
    r"act now", r"few slots left", r"last date", r"offer ends",
    r"urgent(ly)? hiring", r"apply immediately", r"seats filling fast",
    r"don'?t miss", r"today only",
]

SUSPICIOUS_PHRASES = [
    r"no experience needed", r"no experience required", r"easy money",
    r"work from home guaranteed", r"100% job guarantee",
    r"guaranteed placement", r"guaranteed income", r"be your own boss",
    r"unlimited earning", r"earn (rs\.?|inr|₹|\$)\s*\d+.{0,15}(per day|daily)",
    r"no interview", r"no skills required", r"instant hiring",
    r"data entry.{0,15}home", r"quick money",
]

PERSONAL_EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@(gmail|yahoo|hotmail|outlook|rediffmail)\.com",
    re.IGNORECASE,
)
WHATSAPP_PATTERN = re.compile(r"whats\s*app", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(\+?\d[\d\-\s]{8,13}\d)")
URL_PATTERN = re.compile(r"(https?://\S+|www\.\S+|bit\.ly/\S+)", re.IGNORECASE)

# heuristic monthly-stipend threshold (INR). Anything claimed above this for
# an "intern" role, worded as a fixed guaranteed monthly figure, is treated
# as an "unusually high compensation" indicator. Documented heuristic only.
HIGH_STIPEND_INR = 40000
# also catch USD-style figures for generality
HIGH_STIPEND_USD = 1500

MONEY_PATTERN = re.compile(
    r"(?:₹|rs\.?|inr)\s?([\d,]{3,7})|(?:\$|usd)\s?([\d,]{3,7})",
    re.IGNORECASE,
)


def _count_matches(patterns, text_lower):
    count = 0
    for p in patterns:
        count += len(re.findall(p, text_lower))
    return count


def _detect_high_amount(text_lower):
    """Return 1 if a guaranteed monthly figure above the heuristic
    threshold is present, else 0."""
    for m in MONEY_PATTERN.finditer(text_lower):
        inr_val, usd_val = m.groups()
        if inr_val:
            try:
                val = int(inr_val.replace(",", ""))
                if val >= HIGH_STIPEND_INR:
                    return 1
            except ValueError:
                pass
        if usd_val:
            try:
                val = int(usd_val.replace(",", ""))
                if val >= HIGH_STIPEND_USD:
                    return 1
            except ValueError:
                pass
    return 0


def extract_structured_features(text, telecommuting=0, has_company_logo=0,
                                 has_questions=0):
    """
    Compute the structured (non-TF-IDF) numeric feature vector for one
    posting.

    Parameters
    ----------
    text : str
        Full raw text of the posting (title + description + requirements +
        benefits + company profile, whatever is available, concatenated).
    telecommuting, has_company_logo, has_questions : int (0/1)
        Optional meta-data flags mirroring the columns present in the
        EMSCAD training dataset. Default to 0 (unknown / conservative)
        when not supplied by the caller (e.g. from the Streamlit UI).

    Returns
    -------
    dict of feature_name -> value (all numeric)
    """
    text = text or ""
    text_lower = text.lower()

    words = text.split()
    n_words = len(words)
    n_chars = len(text)

    fee_count = _count_matches(FEE_PATTERNS, text_lower)
    urgency_count = _count_matches(URGENCY_PATTERNS, text_lower)
    suspicious_count = _count_matches(SUSPICIOUS_PHRASES, text_lower)

    personal_email_flag = 1 if PERSONAL_EMAIL_PATTERN.search(text_lower) else 0
    whatsapp_flag = 1 if WHATSAPP_PATTERN.search(text_lower) else 0
    phone_count = len(PHONE_PATTERN.findall(text))
    url_count = len(URL_PATTERN.findall(text))
    high_amount_flag = _detect_high_amount(text_lower)

    exclamation_count = text.count("!")
    upper_letters = sum(1 for c in text if c.isupper())
    letters = sum(1 for c in text if c.isalpha())
    uppercase_ratio = (upper_letters / letters) if letters else 0.0

    features = {
        "length_chars": n_chars,
        "length_words": n_words,
        "fee_count": fee_count,
        "fee_flag": 1 if fee_count > 0 else 0,
        "urgency_count": urgency_count,
        "urgency_flag": 1 if urgency_count > 0 else 0,
        "suspicious_phrase_count": suspicious_count,
        "high_amount_flag": high_amount_flag,
        "personal_email_flag": personal_email_flag,
        "whatsapp_flag": whatsapp_flag,
        "phone_count": phone_count,
        "url_count": url_count,
        "exclamation_count": exclamation_count,
        "uppercase_ratio": round(uppercase_ratio, 4),
        "telecommuting": int(telecommuting),
        "has_company_logo": int(has_company_logo),
        "has_questions": int(has_questions),
    }
    return features


# Fixed, ordered list of structured feature names -> used to build the
# numeric matrix consistently at both train time and inference time.
STRUCTURED_FEATURE_NAMES = [
    "length_chars", "length_words", "fee_count", "fee_flag",
    "urgency_count", "urgency_flag", "suspicious_phrase_count",
    "high_amount_flag", "personal_email_flag", "whatsapp_flag",
    "phone_count", "url_count", "exclamation_count", "uppercase_ratio",
    "telecommuting", "has_company_logo", "has_questions",
]


def structured_features_to_vector(feat_dict):
    return np.array([feat_dict[name] for name in STRUCTURED_FEATURE_NAMES],
                     dtype=float)


def build_structured_matrix(text_series, telecommuting=None,
                             has_company_logo=None, has_questions=None):
    """Vectorised helper used by train_model.py to build the structured
    feature matrix for an entire pandas Series of full_text values."""
    n = len(text_series)
    tc = telecommuting if telecommuting is not None else np.zeros(n)
    hl = has_company_logo if has_company_logo is not None else np.zeros(n)
    hq = has_questions if has_questions is not None else np.zeros(n)

    rows = []
    for i, txt in enumerate(text_series):
        feats = extract_structured_features(txt, tc[i], hl[i], hq[i])
        rows.append(structured_features_to_vector(feats))
    return np.vstack(rows)
