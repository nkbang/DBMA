"""Smith Bible Dictionary activation heuristic.

Determines whether a user query should trigger Smith Bible Dictionary
background retrieval based on query intent signals.

SPRINT34-SMITH-PHASEB: This module is the ONLY place that knows about
Smith Bible Dictionary as a knowledge source. It does NOT import any
retrieval code — it only classifies intent and returns a boolean +
optional rewritten query.

Activation strategy (lightweight, no LLM dependency):
    1. Proper noun detection (capitalized words that look like biblical names)
    2. Theological term matching (known dictionary entry keywords)
    3. Definition-seeking patterns ("what is", "define", "의미", "정의")
    4. Biblical concept keywords (grace, faith, covenant, resurrection, etc.)

Fallback: If no signal detected, Smith retrieval is skipped and TSU
proceeds normally — zero regression risk.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger("nae.smith_activation")

# ── Biblical proper noun patterns ────────────────────────────────────
# Common biblical names/places that would appear in Smith entries
_BIBLICAL_PROPER_NOUN_PATTERNS = [
    # Hebrew names (Korean + English) — \b only at start for Korean terms
    r"\b모세\b|\bMoses\b|\b아브라함\b|\bAbraham\b|\b다윗\b|\bDavid\b|\b솔로몬\b|\bSolomon\b "
    r"|\b야곱\b|\bJacob\b|\b이사악\b|\bIsaac\b|\b요셉\b|\bJoseph\b|\b아론\b|\bAaron\b "
    r"|\b엘리\b|\bEli\b|\b사무엘\b|\bSamuel\b|\b사울\b|\bSaul\b|\b베드로\b|\bPeter\b "
    r"|\b바울\b|\bPaul\b|\b안드레\b|\bAndrew\b|\b요한\b|\bJohn\b|\b빌립\b|\bPhilip\b "
    r"|\b도마\b|\bThomas\b|\b누가\b|\bLuke\b|\b마태\b|\bMatthew\b|\b마가\b|\bMark\b "
    r"|\b디모데\b|\bTimothy\b|\b디도\b|\bTitus\b|\b예수\b|\bJesus\b",
    # Biblical places — \b only at start for Korean terms
    r"\b예루살렘\b|\bJerusalem\b|\b나사렛\b|\bNazareth\b|\b갈릴리\b|\bGalilee\b "
    r"|\b베들레헴\b|\bBethlehem\b|\b에덴\b|\bEden\b|\b바벨론\b|\bBabylon\b|\b이집트\b|\bEgypt\b "
    r"|\b시온\b|\bZion\b|\b사마리아\b|\bSamaria\b|\b요단\b|\bJordan\b|\b헤르몬\b|\bHermon\b "
    r"|\b빌립보\b|\bPhilippi\b|\b코린도\b|\bCorinth\b|\b에베소\b|\bEphesus\b|\b로마\b|\bRome\b "
    r"|\b애굽\b",
]

# Additional patterns for terms that may appear without \b (Korean particle attachment)
_BIBLICAL_PROPER_NOUN_KOREAN_LOOSE = [
    # Korean names without trailing \b — matches even when followed by particles
    r"모세|아브라함|다윗|솔로몬|야곱|이사악|요셉|아론|엘리|사무엘|사울|베드로|바울|안드레|요한|빌립|도마|누가|마태|마가|디모데|디도|예수",
    # Korean places without trailing \b
    r"예루살렘|나사렛|갈릴리|베들레헴|에덴|바벨론|이집트|시온|사마리아|요단|헤르몬|빌립보|코린도|에베소|로마|애굽",
]

# Additional patterns for English terms that may appear in various contexts
_BIBLICAL_PROPER_NOUN_ENGLISH_LOOSE = [
    r"\bAaron\b|\bMoses\b|\bAbraham\b|\bDavid\b|\bSolomon\b|\bJacob\b|\bIsaac\b|\bJoseph\b|\bAaron\b "
    r"|\bEli\b|\bSamuel\b|\bSaul\b|\bPeter\b|\bPaul\b|\bAndrew\b|\bJohn\b|\bPhilip\b|\bThomas\b "
    r"|\bLuke\b|\bMatthew\b|\bMark\b|\bTimothy\b|\bTitus\b|\bJesus\b|\bJerusalem\b|\bNazareth\b "
    r"|\bGalilee\b|\bBethlehem\b|\bEden\b|\bBabylon\b|\bEgypt\b|\bZion\b|\bSamaria\b|\bJordan\b "
    r"|\bHermon\b|\bPhilippi\b|\bCorinth\b|\bEphesus\b|\bRome\b|\bPharisee\b|\bPharisees\b|\bRed Sea\b",
]

# ── Theological concept keywords ─────────────────────────────────────
_THEOLOGICAL_CONCEPTS = [
    # English theological terms
    r"\bgrace\b|\bforgiveness\b|\bcovenant\b|\bresurrection\b|\bsalvation\b "
    r"|\bredemption\b|\bjustification\b|\bsanctification\b|\bpropitiation\b "
    r"|\batonement\b|\bpredestination\b|\bsovereignty\b|\btrinity\b "
    r"|\bpentecost\b|\btransfiguration\b|\bincarnation\b|\bregeneration\b "
    r"|\bjustification\b|\bconsecration\b|\bdiscipleship\b|\bprovidence\b",
    # Korean theological terms (no trailing \b — Korean particles attach directly)
    r"\b은혜|\b용서| 용서|\b언약|\b부활|\b구원|\b속죄 "
    r"|\b의롭다| 의로움|\b거룩하다| 거룩함|\b성령|\b기도 "
    r"|\b믿음| 신앙|\b사랑| 사랑|\b진리|\b광야|\b성전 "
    r"|\b제사| 제사장|\b율법|\b복음|\b천국|\b지옥 "
    r"|\bangel| 천사|\bdemon| 귀신|\bprophet| 선지자 "
    r"|예수| 예수님",
]

# ── Definition-seeking patterns ─────────────────────────────────────
_DEFINITION_PATTERNS = [
    # English
    r"\bwhat is\b|\bdefine\b|\bmeaning of\b|\bexplain\b|\bdescribe\b",
    # Korean (loose matching — particles attach directly)
    r"\b무엇이|\b정의| 정의는|\b의미| 의미는|\b설명해| 설명해줘|\b알려줘|\b무슨\s*뜻|\b무슨\s*말이야|\b뭐야",
]


def should_activate_smith(query: str) -> bool:
    """Determine if Smith Bible Dictionary retrieval should be triggered.

    Args:
        query: The user's raw question text.

    Returns:
        True if Smith retrieval is likely useful for this query.
    """
    if not query or not query.strip():
        return False

    lower = query.lower()
    # Skip very short queries — unlikely to be dictionary-style
    if len(query.strip()) < 3:
        return False

    # Check definition-seeking patterns first (highest signal)
    for pattern in _DEFINITION_PATTERNS:
        if re.search(pattern, lower):
            logger.debug("[smith_activation] matched definition pattern")
            return True

    # Check theological concepts
    for pattern in _THEOLOGICAL_CONCEPTS:
        if re.search(pattern, lower):
            logger.debug("[smith_activation] matched theological concept")
            return True

    # Check biblical proper nouns (strict — case-sensitive)
    for pattern in _BIBLICAL_PROPER_NOUN_PATTERNS:
        if re.search(pattern, query):  # case-sensitive for proper nouns
            logger.debug("[smith_activation] matched proper noun (strict)")
            return True

    # Check loose patterns (Korean without \b, English with \b)
    for pattern in _BIBLICAL_PROPER_NOUN_KOREAN_LOOSE:
        if re.search(pattern, query):
            logger.debug("[smith_activation] matched proper noun (Korean loose)")
            return True

    for pattern in _BIBLICAL_PROPER_NOUN_ENGLISH_LOOSE:
        if re.search(pattern, query):
            logger.debug("[smith_activation] matched proper noun (English loose)")
            return True

    return False


def rewrite_query_for_smith(query: str) -> Optional[str]:
    """Rewrite a query to be more effective for Smith Bible Dictionary search.

    For example, "하나님이 뭐야?" → "God" (focus on the key term).
    Returns None if no rewrite is needed.
    """
    # If query is already a proper noun or single concept, use as-is
    stripped = query.strip()

    # Remove question particles for cleaner search
    cleaned = re.sub(r"[?？]?$", "", stripped)
    cleaned = re.sub(r"^(무엇이|뭐|어떤|어느)\s*", "", cleaned)
    cleaned = re.sub(r"\b의\s*의미\b|\b정의\b|\b무슨\s*말이야\b", "", cleaned)
    cleaned = cleaned.strip()

    if not cleaned or len(cleaned) < 2:
        return None

    # If cleaned query is shorter and more focused, use it
    if len(cleaned) < len(stripped):
        logger.debug("[smith_activation] rewrote query: %r → %r", stripped, cleaned)
        return cleaned

    return None
