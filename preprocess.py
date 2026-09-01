"""
preprocess.py
-------------
Basic, explainable NLP preprocessing used before TF-IDF vectorisation.

Kept intentionally simple (Engineering Principle: use the simplest tool
that solves the problem) — undergrad-explainable, no heavy NLP pipeline.
"""

import re
import pandas as pd

try:
    import nltk
    from nltk.corpus import stopwords
    _NLTK_OK = True
except ImportError:
    _NLTK_OK = False

_STOPWORDS = None


def _get_stopwords():
    """Lazy-load NLTK stopwords; fall back to a small built-in list if the
    NLTK corpus isn't downloaded (keeps the project runnable offline)."""
    global _STOPWORDS
    if _STOPWORDS is not None:
        return _STOPWORDS

    if _NLTK_OK:
        try:
            _STOPWORDS = set(stopwords.words("english"))
            return _STOPWORDS
        except LookupError:
            try:
                nltk.download("stopwords", quiet=True)
                _STOPWORDS = set(stopwords.words("english"))
                return _STOPWORDS
            except Exception:
                pass

    # Fallback minimal stopword list (used only if NLTK data unavailable)
    _STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
        "be", "been", "being", "in", "on", "at", "to", "for", "of", "with",
        "as", "by", "this", "that", "it", "we", "you", "your", "our",
        "will", "from", "has", "have", "had", "not", "no", "if", "so",
    }
    return _STOPWORDS


HTML_TAG_RE = re.compile(r"<[^>]+>")
NON_ALPHA_RE = re.compile(r"[^a-zA-Z\s]")
MULTI_SPACE_RE = re.compile(r"\s+")


def clean_text(text):
    """Lowercase, strip HTML, remove non-alphabetic characters, remove
    stopwords, collapse whitespace. Returns a cleaned string ready for
    TF-IDF vectorisation."""
    if not isinstance(text, str):
        return ""

    text = HTML_TAG_RE.sub(" ", text)
    text = text.lower()
    text = NON_ALPHA_RE.sub(" ", text)
    text = MULTI_SPACE_RE.sub(" ", text).strip()

    stop = _get_stopwords()
    tokens = [t for t in text.split() if t not in stop and len(t) > 1]
    return " ".join(tokens)


def combine_fields(row, fields):
    """Concatenate several dataframe columns (which may contain NaN) into
    one raw text blob, matching what a user would paste as a single
    posting in the Streamlit app."""
    parts = []
    for f in fields:
        val = row.get(f, "")
        if pd.notna(val) and str(val).strip():
            parts.append(str(val))
    return " ".join(parts)
