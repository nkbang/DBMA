"""Stage 2.5 - structural/semantic annotation on top of reflowed paragraphs.

Adds, per paragraph: sentence segmentation, heading/quote classification,
canonical scripture-reference forms, and script-based language tags
(Greek/Hebrew are detected reliably via Unicode block; Latin is not
attempted here since it shares script with English and a heuristic
would be unreliable - see module docstring in scripture.py).
"""
from __future__ import annotations

import re

from . import config
from .reflow import Paragraph

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"‘“])")
_ABBREVIATIONS = {
    "mr.", "mrs.", "dr.", "rev.", "elder", "st.", "vs.", "etc.", "i.e.", "e.g.",
    "rom.", "cor.", "gal.", "eph.", "phil.", "col.", "thess.", "tim.", "tit.",
    "heb.", "jas.", "pet.", "jn.", "rev.", "gen.", "exod.", "lev.", "num.",
    "deut.", "josh.", "judg.", "ps.", "prov.", "eccl.", "isa.", "jer.", "ezek.",
    "matt.", "mk.", "lk.", "no.", "vol.", "p.", "pp.", "ch.", "art.",
}

_HEADING_TOP_LEVEL = re.compile(
    r"^(CHAPTER|PART|BOOK|SECTION)\b|^[IVXLCDM]+\.?\s*$", re.IGNORECASE
)
_ALL_CAPS_LINE = re.compile(r"^[A-Z0-9][A-Z0-9 .,;:'\"\-]{2,80}$")

_QUOTE_WRAP = re.compile(r'^[\"“‘].*[\"”’]$', re.DOTALL)

_GREEK_RANGE = re.compile(r"[Ͱ-Ͽἀ-῿]")
_HEBREW_RANGE = re.compile(r"[֐-׿]")

# Roman-numeral chapter/verse ("John iii.16") -> canonical arabic ("John 3:16").
# Also normalizes the common "Book ch.verse" dotted form to "Book ch:verse".
# Roman numeral parser: general (no hardcoded map), supports 1–199.
# Upper bound prevents OCR false positives on non-Roman sequences.
_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def _parse_roman(s: str) -> int | None:
    """Parse a Roman numeral string to integer. Returns None if invalid or out of range (1–199)."""
    s = s.upper().strip()
    if not s:
        return None
    total = 0
    prev = 0
    for ch in reversed(s):
        val = _ROMAN_VALUES.get(ch)
        if val is None:
            return None
        if val < prev:
            total -= val
        else:
            total += val
        prev = val
    if total < 1 or total > 199:
        return None
    # Round-trip validation to reject "iiii", "vx", etc.
    roman = _int_to_roman(total)
    if roman.upper() != s:
        return None
    return total


def _int_to_roman(n: int) -> str:
    """Convert integer (1–3999) to canonical Roman numeral string."""
    vals = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ]
    result = []
    for value, numeral in vals:
        while n >= value:
            result.append(numeral)
            n -= value
    return "".join(result)


# Legacy reference pattern: "Book iv.16" or "Book iv. 16" (with optional space/dot)
# Allows 0–3 non-digit, non-letter noise chars between book and chapter.
# Supports Arabic numeral prefix (1-3) AND Roman numeral prefix (I/II/III).
_LEGACY_REF = re.compile(
    r"(?<!\w)(?P<book>(?:(?:[1-3]|I{1,3})\s?)?[A-Z][a-zA-Z]+)"
    r"(?=[.\s])"  # book must be followed by period or whitespace
    r"\s*"
    r"(?P<noise>[^\d\w]{0,5})"
    r"\s*"
    r"(?P<chapter>[ivxlcdmIVXLCDM]+)"
    r"\.?\s*"  # optional period + optional space between chapter and verse
    r"(?P<verse>\d{1,3}(?:[-–]\d{1,3})?)\b",
)


# Arabic reference pattern: "Book 3:16" or "Book 3.16"
# Supports Arabic numeral prefix (1-3) AND Roman numeral prefix (I/II/III).
_ARABIC_REF = re.compile(
    r"(?<!\w)(?P<book>(?:(?:[1-3]|I{1,3})\s?)?[A-Z][a-zA-Z]+)"
    r"(?=[.\s])"  # book must be followed by period or whitespace
    r"\s*"
    r"(?P<noise>[^\d\w]{0,5})"
    r"\s*"
    r"(?P<chapter>\d{1,3})[:.](?P<verse>\d{1,3}(?:[-–]\d{1,3})?)\b",
)


# Korean scripture reference patterns (split into two to avoid ambiguity):
# 1. "장/절" format: "요한복음 3장 16절"
# 2. Standard format with separator: "요 3:16", "롬 8:1-2"

_KOREAN_REF_ZANG = re.compile(
    r"(?<!\w)(?P<book>["
    r"창세기출애굽기레위기민수기신명기여호수아사사기룻기"
    r"사무엘상사무엘하열왕기상열왕기하역대상역대하에스라느헤미야에스더"
    r"욥기시편잠언전도서아가이사야예레미야애가에스겔다니엘"
    r"호세아요엘아모스오바댜요나미가나훔하박국스바냐학개스가랴말라기"
    r"마태복음마가복음누가복음요한복음사도행전"
    r"로마서고린도전서고린도후서갈라디아서에베소서빌립보서골로새서"
    r"데살로니가전서데살로니가후서디모데전서디모데후서디도서빌레몬서"
    r"히브리서야고보서베드로전서베드로후서요한일서요한이서요한삼서유다서"
    r"요롬고전고후갈엡빌골살전살후딤전딤후딛벧전벧후요일요이요삼빌계"
    r"]+)\s*"
    r"(?P<noise>[^\d\w]{0,3})?"
    r"(?P<chapter>\d{1,3})"
    r"\s*장\s*"
    r"(?P<verse>\d{1,3}(?:[-–]\d{1,3})?)",
    re.IGNORECASE,
)

_KOREAN_REF_STD = re.compile(
    r"(?<!\w)(?P<book>["
    r"창세기출애굽기레위기민수기신명기여호수아사사기룻기"
    r"사무엘상사무엘하열왕기상열왕기하역대상역대하에스라느헤미야에스더"
    r"욥기시편잠언전도서아가이사야예레미야애가에스겔다니엘"
    r"호세아요엘아모스오바댜요나미가나훔하박국스바냐학개스가랴말라기"
    r"마태복음마가복음누가복음요한복음사도행전"
    r"로마서고린도전서고린도후서갈라디아서에베소서빌립보서골로새서"
    r"데살로니가전서데살로니가후서디모데전서디모데후서디도서빌레몬서"
    r"히브리서야고보서베드로전서베드로후서요한일서요한이서요한삼서유다서"
    r"요롬고전고후갈엡빌골살전살후딤전딤후딛벧전벧후요일요이요삼빌계"
    r"]+)\s*"
    r"(?P<noise>[^\d\w]{0,3})?"
    r"(?P<chapter>\d{1,3})[:.](?P<verse>\d{1,3}(?:[-–]\d{1,3})?)",
    re.IGNORECASE,
)

# Short Korean abbreviations (common 1–2 char forms)
_KOREAN_SHORT: dict[str, str] = {
    "창": "GEN", "출": "EXO", "레": "LEV", "민": "NUM", "신": "DEU",
    "여": "JOS", "사": "JDG", "룻": "RUT",
    "상": "1SA", "하": "2SA", "열": "1KI", "역": "1CH",
    "에스": "EZR", "느": "NEH", "에스더": "EST",
    "욥": "JOB", "시": "PSA", "잠": "PRO", "전": "ECC", "아가": "SOT",
    "사": "ISA", "예": "JER", "애": "LAM", "겔": "EZE", "단": "DAN",
    "호": "HOS", "요엘": "JOEL", "암": "AMOS", "오": "OBA", "요나": "JON",
    "미": "MIC", "나": "NAM", "하박": "HAB", "스바": "ZEP", "학": "HAG",
    "스": "ZEC", "말": "MAL",
    "마": "MAT", "막": "MRK", "눅": "LUK", "요": "JHN", "행": "ACT",
    "롬": "ROM", "고전": "1CO", "고후": "2CO", "갈": "GAL", "엡": "EPH",
    "빌": "PHP", "골": "COL", "살전": "1TH", "살후": "2TH", "딤전": "1TI",
    "딤후": "2TI", "딛": "TIT", "빌레": "PHM",
    "히": "HEB", "약": "JAS", "벧전": "1PE", "벧후": "2PE", "요일": "1JN",
    "요이": "2JN", "요삼": "3JN", "유": "JUD", "계": "REV",
}

# Full Korean book names -> book_id (from BIBLE_BOOKS)
_KOREAN_FULL_TO_ID: dict[str, str] = {}
try:
    from core.sermon.bible_books import BIBLE_BOOKS
    for kr_name, book_id in BIBLE_BOOKS:
        _KOREAN_FULL_TO_ID[kr_name] = book_id
except ImportError:
    pass

# English book aliases (short/standard forms) -> full book name
_ENG_ALIASES: dict[str, str] = {
    "gen": "Genesis", "exod": "Exodus", "exodus": "Exodus", "lev": "Leviticus",
    "leviticus": "Leviticus", "num": "Numbers", "nums": "Numbers", "numbers": "Numbers",
    "deut": "Deuteronomy", "deuteronomy": "Deuteronomy", "josh": "Joshua", "joshua": "Joshua",
    "judg": "Judges", "judges": "Judges", "ruth": "Ruth", "rut": "Ruth",
    "1sam": "1 Samuel", "1sa": "1 Samuel", "first samuel": "1 Samuel",
    "2sam": "2 Samuel", "2sa": "2 Samuel", "second samuel": "2 Samuel",
    "1kgs": "1 Kings", "1ki": "1 Kings", "first kings": "1 Kings",
    "2kgs": "2 Kings", "2ki": "2 Kings", "second kings": "2 Kings",
    "1chr": "1 Chronicles", "1ch": "1 Chronicles", "first chronicles": "1 Chronicles",
    "2chr": "2 Chronicles", "2ch": "2 Chronicles", "second chronicles": "2 Chronicles",
    "ezra": "Ezra", "neh": "Nehemiah", "esth": "Esther", "esther": "Esther",
    "job": "Job", "ps": "Psalms", "psalms": "Psalms",
    "prov": "Proverbs", "prv": "Proverbs", "proverbs": "Proverbs", "eccl": "Ecclesiastes",
    "ecclesiastes": "Ecclesiastes", "song": "Song of Solomon", "sot": "Song of Solomon",
    "isa": "Isaiah", "isaiah": "Isaiah", "jer": "Jeremiah", "jeremiah": "Jeremiah",
    "lam": "Lamentations", "lamentations": "Lamentations", "ezek": "Ezekiel",
    "ezekiel": "Ezekiel", "dan": "Daniel", "daniel": "Daniel", "hos": "Hosea",
    "hosea": "Hosea", "joel": "Joel", "amos": "Amos", "obad": "Obadiah",
    "obadiah": "Obadiah", "jonah": "Jonah", "jon": "Jonah", "micah": "Micah",
    "mic": "Micah", "nahum": "Nahum", "nam": "Nahum", "hab": "Habakkuk",
    "habakkuk": "Habakkuk", "zeph": "Zephaniah", "zep": "Zephaniah", "hag": "Haggai",
    "haggai": "Haggai", "zec": "Zechariah", "zech": "Zechariah", "zechariah": "Zechariah",
    "mal": "Malachi", "malachi": "Malachi",
    "matt": "Matthew", "matthew": "Matthew", "mark": "Mark", "mk": "Mark",
    "luke": "Luke", "lk": "Luke", "john": "John", "acts": "Acts", "act": "Acts",
    "rom": "Romans", "romans": "Romans", "1cor": "1 Corinthians", "i cor": "1 Corinthians",
    "1 cor": "1 Corinthians", "2cor": "2 Corinthians", "ii cor": "2 Corinthians",
    "2 cor": "2 Corinthians", "gal": "Galatians", "galatians": "Galatians",
    "eph": "Ephesians", "ephesians": "Ephesians", "phil": "Philippians",
    "php": "Philippians", "philippians": "Philippians", "col": "Colossians",
    "colossians": "Colossians", "1thess": "1 Thessalonians", "1th": "1 Thessalonians",
    "i thess": "1 Thessalonians", "2thess": "2 Thessalonians", "2th": "2 Thessalonians",
    "ii thess": "2 Thessalonians", "1tim": "1 Timothy", "1ti": "1 Timothy",
    "i tim": "1 Timothy", "2tim": "2 Timothy", "2ti": "2 Timothy",
    "ii tim": "2 Timothy", "titus": "Titus", "tit": "Titus", "philem": "Philemon",
    "philemon": "Philemon", "phm": "Philemon", "heb": "Hebrews", "hebrews": "Hebrews",
    "james": "James", "jas": "James", "1pet": "1 Peter", "1pe": "1 Peter",
    "i pet": "1 Peter", "2pet": "2 Peter", "2pe": "2 Peter", "ii pet": "2 Peter",
    "1john": "1 John", "1jn": "1 John", "i john": "1 John", "2john": "2 John",
    "2jn": "2 John", "ii john": "2 John", "3john": "3 John", "3jn": "3 John",
    "iii john": "3 John", "jude": "Jude", "jud": "Jude", "rev": "Revelation",
    "revelation": "Revelation",
}

# Bare book name parts used after stripping number prefix (e.g., "1 cor" → "cor")
# These are NOT standalone book names — they only work with a number prefix.
_BARE_BOOK_PARTS = {
    "cor": "Corinthians",
    "corinthians": "Corinthians",
    "pet": "Peter",
    "john": "John",
    "sam": "Samuel",
    "kings": "Kings",
    "chronicles": "Chronicles",
    "esdras": "Ezra",
    "nehem": "Nehemiah",
    "esth": "Esther",
    "job": "Job",
    "pro": "Proverbs",
    "ecc": "Ecclesiastes",
    "lam": "Lamentations",
    "hos": "Hosea",
    "oba": "Obadiah",
    "jon": "Jonah",
    "nam": "Nahum",
    "zeph": "Zephaniah",
    "mal": "Malachi",
    "luk": "Luke",
    "heb": "Hebrews",
    "jas": "James",
    "jud": "Jude",
}

_NON_BOOK_WORDS = {
    "volume", "vol", "page", "pp", "chapter", "ch", "part", "section",
    "article", "art", "number", "no", "verse", "verses",
}


def _resolve_book_name(raw: str) -> str | None:
    """Resolve a raw book name string to its canonical full English name.

    Handles:
    - English aliases (short, standard, full forms)
    - Korean full names (from BIBLE_BOOKS)
    - Korean short abbreviations
    - All-caps forms (ROM, 1COR, etc.)
    - Number-prefixed forms ("1 cor", "1cor", "i cor", "1 john", "2 pet")

    F-3 Option A: Always returns English canonical.
    Returns canonical English book name or None if unresolvable.
    """
    if not raw:
        return None

    cleaned = raw.strip().rstrip(".").strip()
    lower = cleaned.lower()

    # Negative filter: skip non-book words
    if lower in _NON_BOOK_WORDS:
        return None

    # Try English aliases first (case-insensitive)
    if lower in _ENG_ALIASES:
        return _ENG_ALIASES[lower]

    # Try all-caps variant of English aliases
    upper = cleaned.upper()
    for k, v in _ENG_ALIASES.items():
        if k.upper() == upper:
            return v

    # Handle number-prefixed book names: "1 cor", "1cor", "i cor", "1 john", "2 pet"
    # Detect and preserve leading number/Roman numeral prefix
    prefix = ""

    # Strip leading Arabic numeral (1-3) optionally followed by space
    m = re.match(r'^([1-3])\s?(.+)$', cleaned)
    if m:
        prefix, rest = m.group(1), m.group(2).strip()
        rest_lower = rest.lower()
        # Try direct lookup of the rest
        if rest_lower in _ENG_ALIASES:
            return f"{prefix} {_ENG_ALIASES[rest_lower]}"
        # Try bare book parts (e.g., "cor" → "Corinthians")
        if rest_lower in _BARE_BOOK_PARTS:
            return f"{prefix} {_BARE_BOOK_PARTS[rest_lower]}"
        # Try all-caps variant
        rest_upper = rest.upper()
        for k, v in _ENG_ALIASES.items():
            if k.upper() == rest_upper:
                return f"{prefix} {v}"
        # Direct match against English book names
        eng_names_lower = {v.lower() for v in _ENG_ALIASES.values()}
        if rest_lower in eng_names_lower:
            for v in _ENG_ALIASES.values():
                if v.lower() == rest_lower:
                    return f"{prefix} {v}"

    # Handle Roman numeral-prefixed book names: "i cor", "ii pet", "iii john"
    roman_prefix_map = {"i": "1", "ii": "2", "iii": "3"}
    for roman, arabic in roman_prefix_map.items():
        if lower.startswith(roman + " ") or lower == roman:
            rest = lower[len(roman):].strip()
            # Standalone Roman numeral (e.g., "i" → "1 Corinthians")
            if not rest:
                # Map standalone I/II/III to common books
                standalone_map = {"i": "1 Corinthians", "ii": "2 Corinthians", "iii": "3 John"}
                return standalone_map.get(roman)
            if rest and rest in _ENG_ALIASES:
                return f"{arabic} {_ENG_ALIASES[rest]}"
            # Try bare book parts
            if rest and rest in _BARE_BOOK_PARTS:
                return f"{arabic} {_BARE_BOOK_PARTS[rest]}"
            rest_upper = rest.upper()
            for k, v in _ENG_ALIASES.items():
                if k.upper() == rest_upper:
                    return f"{arabic} {v}"

    # Try Korean full names (F-3 Option A: convert to English)
    if cleaned in _KOREAN_FULL_TO_ID:
        return _book_id_to_english(_KOREAN_FULL_TO_ID[cleaned])

    # Try Korean short abbreviations (F-3 Option A: convert to English)
    for abbr, book_id in _KOREAN_SHORT.items():
        if cleaned == abbr or cleaned.startswith(abbr):
            return _book_id_to_english(book_id)

    # Direct match: already a valid English book name
    eng_names_lower = {v.lower() for v in _ENG_ALIASES.values()}
    if lower in eng_names_lower:
        for v in _ENG_ALIASES.values():
            if v.lower() == lower:
                return v

    return None


def _book_id_to_english(book_id: str) -> str | None:
    """Convert a book_id to its canonical English name."""
    _ID_TO_ENG = {
        "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers",
        "DEU": "Deuteronomy", "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth",
        "1SA": "1 Samuel", "2SA": "2 Samuel", "1KI": "1 Kings", "2KI": "2 Kings",
        "1CH": "1 Chronicles", "2CH": "2 Chronicles", "EZR": "Ezra", "NEH": "Nehemiah",
        "EST": "Esther", "JOB": "Job", "PSA": "Psalms", "PRO": "Proverbs",
        "ECC": "Ecclesiastes", "SOT": "Song of Solomon", "ISA": "Isaiah",
        "JER": "Jeremiah", "LAM": "Lamentations", "EZE": "Ezekiel", "DAN": "Daniel",
        "HOS": "Hosea", "JOEL": "Joel", "AMOS": "Amos", "OBA": "Obadiah",
        "JON": "Jonah", "MIC": "Micah", "NAM": "Nahum", "HAB": "Habakkuk",
        "ZEP": "Zephaniah", "HAG": "Haggai", "ZEC": "Zechariah", "MAL": "Malachi",
        "MAT": "Matthew", "MRK": "Mark", "LUK": "Luke", "JHN": "John",
        "ACT": "Acts", "ROM": "Romans", "1CO": "1 Corinthians", "2CO": "2 Corinthians",
        "GAL": "Galatians", "EPH": "Ephesians", "PHP": "Philippians", "COL": "Colossians",
        "1TH": "1 Thessalonians", "2TH": "2 Thessalonians", "1TI": "1 Timothy",
        "2TI": "2 Timothy", "TIT": "Titus", "PHM": "Philemon", "HEB": "Hebrews",
        "JAS": "James", "1PE": "1 Peter", "2PE": "2 Peter", "1JN": "1 John",
        "2JN": "2 John", "3JN": "3 John", "JUD": "Jude", "REV": "Revelation",
    }
    return _ID_TO_ENG.get(book_id)


def _clean_noise(raw: str) -> str:
    """Strip OCR noise (non-alphanumeric, non-digit chars) from a raw string."""
    return re.sub(r"[^\w\s]", "", raw).strip()


def split_sentences(text: str) -> list[str]:
    """Best-effort sentence splitter; guards against common theological/biblical abbreviations."""
    if not text.strip():
        return []
    raw_parts = _SENTENCE_SPLIT.split(text)
    sentences: list[str] = []
    buffer = ""
    for part in raw_parts:
        buffer = f"{buffer} {part}".strip() if buffer else part
        tail = buffer.rstrip().split(" ")[-1].lower() if buffer.strip() else ""
        if tail in _ABBREVIATIONS:
            continue
        sentences.append(buffer)
        buffer = ""
    if buffer:
        sentences.append(buffer)
    return [s.strip() for s in sentences if s.strip()]


def classify_paragraph(paragraph: Paragraph) -> tuple[str, int | None]:
    """Return (type, heading_level). type in {heading, quote, verse, prose}; existing verse type wins."""
    if paragraph.type == "verse":
        return "verse", None

    text = paragraph.text.strip()
    is_single_line = "\n" not in text and len(text) <= 80

    if is_single_line and _HEADING_TOP_LEVEL.match(text):
        return "heading", 1
    if is_single_line and _ALL_CAPS_LINE.match(text) and text.upper() == text:
        return "heading", 2
    if _QUOTE_WRAP.match(text):
        return "quote", None
    return "prose", None


def canonicalize_scripture_ref(ref: str) -> str | None:
    """Convert legacy 'Book ivx.verse' notation to canonical 'Book chapter:verse'.

    Also handles:
    - Arabic numerals (Book 3:16)
    - Korean book names (요 3:16 -> John 3:16, F-3 Option A)
    - Both chapter AND verse as Roman numerals (F-1)
    """
    # Try legacy Roman numeral form first
    match = _LEGACY_REF.match(ref)
    if match:
        book_raw = re.sub(r"\s+", " ", match.group("book")).strip()
        book = _resolve_book_name(book_raw)
        if book is None:
            return None
        chapter_roman = match.group("chapter").lower()
        # Strip noise between book and chapter
        noise = match.group("noise") or ""
        chapter_num = _parse_roman(chapter_roman)
        if chapter_num is None:
            return None
        verse = match.group("verse")
        return f"{book} {chapter_num}:{verse}"

    # Try Arabic numeral form
    match = _ARABIC_REF.match(ref)
    if match:
        book_raw = re.sub(r"\s+", " ", match.group("book")).strip()
        book = _resolve_book_name(book_raw)
        if book is None:
            return None
        chapter = match.group("chapter")
        verse = match.group("verse")
        return f"{book} {chapter}:{verse}"

    # Try Korean reference form (장/절 format)
    match = _KOREAN_REF_ZANG.match(ref)
    if match:
        book_raw = match.group("book")
        chapter = match.group("chapter")
        verse = match.group("verse")
        book = _resolve_book_name(book_raw)
        if book is None:
            return None
        return f"{book} {chapter}:{verse}"

    # Try Korean reference form (standard separator format)
    match = _KOREAN_REF_STD.match(ref)
    if match:
        book_raw = match.group("book")
        chapter = match.group("chapter")
        verse = match.group("verse")
        book = _resolve_book_name(book_raw)
        if book is None:
            return None
        return f"{book} {chapter}:{verse}"

    return None


def find_scripture_references_extended(text: str) -> list[dict[str, str]]:
    """Find both canonical (John 3:16) and legacy (John iii.16) forms, paired with canonical output.

    Also finds Korean scripture references (요 3:16, 요한복음 3장 16절).
    """
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for pattern in (_ARABIC_REF, _LEGACY_REF, _KOREAN_REF_ZANG, _KOREAN_REF_STD):
        for match in pattern.finditer(text):
            original = match.group(0)
            if original in seen:
                continue
            canonical = canonicalize_scripture_ref(original)
            if canonical is None:
                continue
            seen.add(original)
            results.append({"original": original, "canonical": canonical})
    return results


def detect_script_language(text: str) -> str | None:
    """Reliable script-based detection only (Greek/Hebrew Unicode blocks). Latin is not attempted."""
    greek_chars = len(_GREEK_RANGE.findall(text))
    hebrew_chars = len(_HEBREW_RANGE.findall(text))
    total = max(len(text.strip()), 1)
    if greek_chars / total > 0.15:
        return "greek"
    if hebrew_chars / total > 0.15:
        return "hebrew"
    return None


def annotate_paragraph(paragraph: Paragraph, index: int) -> dict:
    ptype, heading_level = classify_paragraph(paragraph)
    sentences = split_sentences(paragraph.text) if ptype in ("prose", "quote") else []
    scripture = find_scripture_references_extended(paragraph.text)
    language = detect_script_language(paragraph.text)

    entry = {
        "index": index,
        "type": ptype,
        "text": paragraph.text,
        "page_start": paragraph.page_start,
        "page_end": paragraph.page_end,
        "sentences": [{"sentence_index": i, "text": s} for i, s in enumerate(sentences)],
        "scripture_references": scripture,
    }
    if heading_level is not None:
        entry["heading_level"] = heading_level
    if language is not None:
        entry["language"] = language
    return entry
