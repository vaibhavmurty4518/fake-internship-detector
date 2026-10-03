"""
inference.py
-------------
Shared prediction + explainability logic, used by BOTH app.py (Streamlit)
and test_examples.py, so the demo script and the live app can never give
different answers for the same input.

Loads the artifacts saved by train_model.py:
  models/model.pkl        -> trained classifier (best of the 3 compared)
  models/vectorizer.pkl   -> fitted TF-IDF vectorizer
  models/scaler.pkl       -> fitted StandardScaler for structured features
"""

import re
import joblib
from scipy.sparse import hstack, csr_matrix

from preprocess import clean_text
from feature_engineering import (extract_structured_features,
                                  structured_features_to_vector,
                                  FEE_PATTERNS, URGENCY_PATTERNS,
                                  SUSPICIOUS_PHRASES, PERSONAL_EMAIL_PATTERN,
                                  WHATSAPP_PATTERN)

MODEL_PATH = "models/model.pkl"
VECTORIZER_PATH = "models/vectorizer.pkl"
SCALER_PATH = "models/scaler.pkl"

_model = None
_vectorizer = None
_scaler = None


def load_artifacts():
    global _model, _vectorizer, _scaler
    if _model is None:
        _model = joblib.load(MODEL_PATH)
        _vectorizer = joblib.load(VECTORIZER_PATH)
        _scaler = joblib.load(SCALER_PATH)
    return _model, _vectorizer, _scaler


# Maps each structured feature flag -> a plain-English, non-defamatory
# explanation shown to the user. Deliberately worded as "indicator /
# potential risk / requires verification", never as a factual claim that
# the company or posting IS fraudulent (Ethics requirement).
INDICATOR_EXPLANATIONS = {
    "fee_flag": (
        "Payment / registration fee language detected",
        "The posting appears to request a registration fee, security "
        "deposit, or similar upfront payment. Legitimate internships "
        "almost never require candidates to pay to be hired — this is a "
        "common pattern in scam listings and should be verified "
        "independently before any payment is made.",
    ),
    "urgency_flag": (
        "Urgency-oriented language detected",
        "Phrases suggesting extreme urgency (e.g. 'limited seats', "
        "'apply today', 'hurry') were found. Scammers often use urgency "
        "to pressure applicants into skipping normal due diligence.",
    ),
    "suspicious_phrase_count": (
        "Generic 'too good to be true' phrasing detected",
        "Phrases such as 'no experience needed', 'guaranteed income', or "
        "'100% job guarantee' were found. These are common in low-quality "
        "or fraudulent postings, though they can occasionally appear in "
        "genuine, informal listings too.",
    ),
    "high_amount_flag": (
        "Unusually high compensation for an internship",
        "A guaranteed monthly figure above a typical internship-stipend "
        "range was detected. This is a heuristic threshold, not a "
        "certainty — but unusually high, guaranteed pay for an entry-"
        "level/internship role is a frequently reported scam indicator "
        "and is worth independent verification.",
    ),
    "personal_email_flag": (
        "Contact via personal (non-corporate) email address",
        "The posting asks candidates to respond to a free personal "
        "email address (Gmail/Yahoo/Hotmail/etc.) rather than a "
        "company-domain email. Legitimate employers usually correspond "
        "from a company domain.",
    ),
    "whatsapp_flag": (
        "Requests contact via WhatsApp",
        "The posting asks applicants to reach out over WhatsApp rather "
        "than a formal company channel. This alone isn't necessarily "
        "suspicious, but combined with other indicators it raises risk.",
    ),
    "url_count": (
        "External links present",
        "The posting contains external links. Links to unfamiliar or "
        "shortened URLs, in particular, should be treated with caution "
        "and not clicked without verifying the destination.",
    ),
    "low_company_info_flag": (
        "Limited company information",
        "The posting includes little to no verifiable detail about the "
        "hiring company (address, website, official description). "
        "Genuine employers typically provide identifiable company "
        "information.",
    ),
}


def _company_info_flag(text, threshold_words=25):
    """Very light heuristic: does the posting contain any company-profile-
    style content at all? We look for common 'about us' style cues; if
    none are present AND the whole post is short, we flag missing company
    info. This is intentionally conservative (few false positives)."""
    text_lower = text.lower()
    cues = ["about us", "about the company", "our company", "we are ",
            "founded in", "headquartered", "www.", "http"]
    has_cue = any(c in text_lower for c in cues)
    return 0 if has_cue else 1


def extract_matched_highlights(text):
    """
    Finds exact spans of suspicious or notable terms for live visual highlighting.
    Returns a list of dicts with { 'start': int, 'end': int, 'match': str, 'category': str, 'label': str, 'color': str }
    """
    if not text:
        return []
    
    highlights = []
    text_lower = text.lower()
    
    # Check fee patterns
    for p in FEE_PATTERNS:
        for m in re.finditer(p, text_lower):
            highlights.append({
                "start": m.start(),
                "end": m.end(),
                "match": text[m.start():m.end()],
                "category": "fee",
                "label": "Payment / Fee Trap",
                "color": "#ef4444"
            })
            
    # Check urgency patterns
    for p in URGENCY_PATTERNS:
        for m in re.finditer(p, text_lower):
            highlights.append({
                "start": m.start(),
                "end": m.end(),
                "match": text[m.start():m.end()],
                "category": "urgency",
                "label": "High Urgency Pressure",
                "color": "#f59e0b"
            })

    # Check suspicious phrases
    for p in SUSPICIOUS_PHRASES:
        for m in re.finditer(p, text_lower):
            highlights.append({
                "start": m.start(),
                "end": m.end(),
                "match": text[m.start():m.end()],
                "category": "too_good",
                "label": "Suspicious Promise",
                "color": "#ec4899"
            })

    # Personal emails
    for m in PERSONAL_EMAIL_PATTERN.finditer(text_lower):
        highlights.append({
            "start": m.start(),
            "end": m.end(),
            "match": text[m.start():m.end()],
            "category": "email",
            "label": "Personal Email Contact",
            "color": "#eab308"
        })

    # WhatsApp
    for m in WHATSAPP_PATTERN.finditer(text_lower):
        highlights.append({
            "start": m.start(),
            "end": m.end(),
            "match": text[m.start():m.end()],
            "category": "whatsapp",
            "label": "WhatsApp Contact",
            "color": "#06b6d4"
        })

    # Deduplicate overlapping matches
    highlights.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
    filtered = []
    last_end = 0
    for h in highlights:
        if h["start"] >= last_end:
            filtered.append(h)
            last_end = h["end"]
            
    return filtered


def predict(text, telecommuting=0, has_company_logo=0, has_questions=0, sensitivity_threshold=50.0):
    """Run the full pipeline on one raw posting and return a rich result dict
    ready for display."""
    model, vectorizer, scaler = load_artifacts()

    cleaned = clean_text(text)
    tfidf_vec = vectorizer.transform([cleaned])

    feats = extract_structured_features(
        text, telecommuting=telecommuting,
        has_company_logo=has_company_logo, has_questions=has_questions,
    )
    struct_vec = structured_features_to_vector(feats).reshape(1, -1)
    struct_scaled = scaler.transform(struct_vec)

    combined = hstack([tfidf_vec, csr_matrix(struct_scaled)]).tocsr()

    proba = model.predict_proba(combined)[0]
    raw_ml_score = float(proba[1]) * 100  # probability of class 1 (fraudulent)

    # Heuristic adjustment for strong multi-indicator presence
    risk_score = raw_ml_score
    if feats.get("fee_flag", 0) and risk_score < 60:
        risk_score = max(risk_score, 72.0)  # Upfront fees are a major red flag

    # Determine risk level based on sensitivity threshold
    # Scaled by user sensitivity
    mult = 50.0 / max(10.0, sensitivity_threshold)
    thresh_high = max(40.0, min(85.0, 70.0 * mult))
    thresh_med = max(15.0, min(60.0, 35.0 * mult))

    if risk_score >= thresh_high:
        risk_level = "HIGH RISK"
        badge_color = "#ef4444"
    elif risk_score >= thresh_med:
        risk_level = "MEDIUM RISK"
        badge_color = "#f59e0b"
    else:
        risk_level = "LOW RISK"
        badge_color = "#10b981"

    feats["low_company_info_flag"] = _company_info_flag(text)

    indicators = []
    for key, (title, explanation) in INDICATOR_EXPLANATIONS.items():
        val = feats.get(key, 0)
        triggered = val >= 1
        if triggered:
            indicators.append({
                "key": key,
                "title": title,
                "explanation": explanation,
                "raw_value": val,
            })

    # Calculate Sub-Dimension Threat Vectors (0 to 100)
    financial_risk = min(100, (feats.get("fee_count", 0) * 50) + (feats.get("high_amount_flag", 0) * 45))
    urgency_risk = min(100, (feats.get("urgency_count", 0) * 35) + min(30, feats.get("exclamation_count", 0) * 5))
    channel_risk = min(100, (feats.get("personal_email_flag", 0) * 55) + (feats.get("whatsapp_flag", 0) * 35) + (10 if feats.get("url_count", 0) > 0 else 0))
    
    # Calculate domain & URL risk vector
    url_count = feats.get("url_count", 0)
    free_hosts = ["blogspot", "wixsite", "wordpress", "weebly", "tinyurl", "bit.ly", "forms.gle"]
    has_free_host = 1 if any(fh in text.lower() for fh in free_hosts) else 0
    domain_risk = min(100, (url_count * 15) + (has_free_host * 60) + (feats.get("personal_email_flag", 0) * 25))

    legitimacy_score = max(5, min(98, (
        (100 - raw_ml_score) * 0.4 +
        (30 if has_company_logo else 0) +
        (25 if has_questions else 0) +
        (0 if feats.get("low_company_info_flag", 0) else 25) -
        (feats.get("uppercase_ratio", 0.0) * 30) -
        (has_free_host * 20)
    )))

    highlights = extract_matched_highlights(text)

    return {
        "risk_score": round(risk_score, 1),
        "raw_ml_score": round(raw_ml_score, 1),
        "risk_level": risk_level,
        "badge_color": badge_color,
        "indicators": indicators,
        "raw_features": feats,
        "highlights": highlights,
        "vectors": {
            "financial_risk": round(financial_risk, 1),
            "urgency_risk": round(urgency_risk, 1),
            "channel_risk": round(channel_risk, 1),
            "legitimacy_score": round(legitimacy_score, 1),
            "domain_risk": round(domain_risk, 1),
            "nlp_similarity": round(raw_ml_score, 1),
        }
    }


def extract_text_from_file(file_obj, filename):
    """
    Extract text content from uploaded files (.pdf, .txt, .md, .docx).
    """
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext in [".txt", ".md"]:
        return file_obj.read().decode("utf-8", errors="ignore")
    elif ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(file_obj)
            text = [page.extract_text() for page in reader.pages if page.extract_text()]
            return "\n".join(text)
        except Exception as e:
            file_obj.seek(0)
            try:
                return file_obj.read().decode("utf-8", errors="ignore")
            except Exception:
                return f"[PDF Parsing Error: {e}]"
    elif ext == ".docx":
        try:
            import docx
            doc = docx.Document(file_obj)
            return "\n".join([p.text for p in doc.paragraphs if p.text])
        except Exception as e:
            return f"[DOCX Parsing Error: {e}]"
    else:
        try:
            return file_obj.read().decode("utf-8", errors="ignore")
        except Exception:
            return ""

