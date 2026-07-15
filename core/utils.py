import os
import re
import hashlib


def fmt_size(num):
    step = 1024.0
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < step:
            return f"{num:.1f} {unit}" if unit != "B" else f"{int(num)} {unit}"
        num /= step
    return f"{num:.1f} PB"


def make_safe_stem(filename: str) -> str:
    stem, ext = os.path.splitext(filename)
    stem = re.sub(r"\s+", " ", stem).strip()
    stem = re.sub(r"[^\w\-.가-힣 ]+", "_", stem)
    ext_clean = ext.lower().replace(".", "")
    return f"{stem}_{ext_clean}" if ext_clean else stem


def stable_file_id(path: str) -> str:
    return hashlib.md5(path.encode("utf-8")).hexdigest()[:12]


def file_checkbox_key(file_info: dict) -> str:
    return f"sel_{stable_file_id(file_info['path'])}"


def noise_color(score: float) -> str:
    if score >= 60:
        return "#d9534f"
    if score >= 35:
        return "#f0ad4e"
    return "#5cb85c"


def noise_label(score: float) -> str:
    if score >= 60:
        return "높음"
    if score >= 35:
        return "주의"
    return "양호"


def normalize_text_basic(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\t", " ")
    text = re.sub(r"[ \u00A0]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_text_for_plain_text(text: str) -> str:
    return normalize_text_basic(text)


def clean_text_for_rich_text(text: str) -> str:
    text = normalize_text_basic(text)
    text = re.sub(r"\\\\[[0-9]{1,3}\\\\\\\\\\]", "", text)
    text = re.sub(r"\\\\(\\s\*\\\*[0-9]{1,3}\\s\*\\\*\\\\\\)", "", text)
    return text.strip()


def _fix_ocr_word_splits(text: str) -> str:
    """
    OCR 단어 내 공백 삽입 복원.
    예:
      T he -> The
      m em bers -> members
      com m entary -> commentary
      o f -> of
    """
    t = text
    t = re.sub(r"\b([A-Z]) ([a-z]{2,})\b", r"\1\2", t)
    t = re.sub(r"\b([b-hj-z]) ([a-z]{1,2})\b", r"\1\2", t)
    for _ in range(5):
        prev = t
        t = re.sub(r"(?<=[a-z]) ([a-z]{1,3})(?= [a-z])", r"\1", t)
        if t == prev:
            break
    return t


def clean_text_for_pdf(text: str, is_ocr: bool = False) -> str:
    """
    PDF용 정리 함수.
    - 페이지 번호 제거
    - 하이픈 줄바꿈 복원
    - OCR 특유 잡음 제거
    - 단어 내 공백 분절 복원
    """
    text = normalize_text_basic(text)

    text = re.sub(r"(?m)^[ \t]*\d+[ \t]*$", "", text)
    text = re.sub(r"(?m)^[ \t]*page\s+\d+[ \t]*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    if is_ocr:
        text = _fix_ocr_word_splits(text)
        text = re.sub(r"[|¦]{2,}", " ", text)
        text = re.sub(r"[~`^]{2,}", " ", text)
        text = re.sub(r"(?m)^[^\w가-힣]{3,}$", "", text)
        text = re.sub(r"[·•※◆▶→←↑↓]{2,}", " ", text)

    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_symbol_ratio(text: str) -> float:
    if not text:
        return 0.0
    symbols = re.findall(r"[^\w\s가-힣]", text)
    return len(symbols) / max(len(text), 1)


def detect_short_line_ratio(text: str) -> float:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 0.0
    short_lines = [ln for ln in lines if len(ln) <= 3]
    return len(short_lines) / len(lines)


def detect_broken_line_ratio(text: str) -> float:
    """Fraction of sentences that don't end in terminal punctuation.

    PDF text extraction wraps lines at the page width, so most raw physical
    lines legitimately end mid-sentence — that is not corruption. This
    reuses core.text_normalizer.split_sentences_mixed(), which already
    merges wrapped lines into sentences (only splitting on an actual
    Korean/English sentence-ending or a bullet), so the ratio reflects real
    truncated/garbled content rather than ordinary PDF line-wrapping.
    """
    if not text or not text.strip():
        return 0.0

    from core.text_normalizer import split_sentences_mixed, _looks_like_korean_sentence_end, _looks_like_english_sentence_end

    sentences = split_sentences_mixed(text)
    if len(sentences) < 2:
        return 0.0

    broken = 0
    for s in sentences[:-1]:  # last sentence may legitimately be cut off at document end
        if re.search(r"[A-Za-z가-힣0-9]$", s) and not (
            re.search(r"[.!?)]$", s)
            or _looks_like_korean_sentence_end(s)
            or _looks_like_english_sentence_end(s)
        ):
            broken += 1
    return broken / len(sentences)


def detect_repeated_punct_ratio(text: str) -> float:
    if not text:
        return 0.0
    repeated = re.findall(r"([^\w\s가-힣])\1{2,}", text)
    return len(repeated) / max(len(text), 1)


def detect_pdf_ocr_like_noise(text: str) -> float:
    if not text:
        return 0.0
    strange = re.findall(r"[^\w\s가-힣.,;:!?()\"'\\-]", text)
    return len(strange) / max(len(text), 1)


def detect_word_split_ratio(text: str) -> float:
    if not text:
        return 0.0
    patterns = [
        r"\b[A-Z] [a-z]{2,}\b",
        r"\b[b-hj-z] [a-z]{1,2}\b",
        r"(?<=[a-z]) [a-z]{1,3}(?= [a-z])",
    ]
    hits = 0
    for pat in patterns:
        hits += len(re.findall(pat, text))
    return hits / max(len(text) / 100.0, 1.0)


def detect_page_artifact_ratio(text: str) -> float:
    if not text:
        return 0.0
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 0.0
    artifact_lines = 0
    for ln in lines:
        if re.fullmatch(r"\d+", ln):
            artifact_lines += 1
        elif re.fullmatch(r"page\s+\d+", ln, flags=re.IGNORECASE):
            artifact_lines += 1
        elif len(ln) <= 4 and re.fullmatch(r"[\-–—_]+", ln):
            artifact_lines += 1
    return artifact_lines / len(lines)


def calculate_noise_score(text: str, file_type: str = "", is_ocr: bool = False) -> dict:
    """
    파일 유형별 노이즈 점수 계산.
    점수는 0~100 사이로 정규화.
    """
    original = text or ""
    file_type = (file_type or "").lower().replace(".", "")

    if not original.strip():
        return {
            "score": 100.0,
            "mode": "empty",
            "cleaned": "",
            "charcount": 0,
            "symbol_ratio": 0.0,
            "short_line_ratio": 0.0,
            "broken_line_ratio": 0.0,
            "repeated_punct_ratio": 0.0,
            "ocr_noise_ratio": 0.0,
            "word_split_ratio": 0.0,
            "page_artifact_ratio": 0.0,
        }

    text_like = {"txt", "md"}
    rich_text = {"docx", "epub", "html", "htm", "rtf"}
    pdf_types = {"pdf"}

    if file_type in text_like:
        cleaned = clean_text_for_plain_text(original)
        symbol_ratio = detect_symbol_ratio(cleaned)
        short_line_ratio = detect_short_line_ratio(cleaned)
        broken_line_ratio = 0.0
        repeated_punct_ratio = 0.0
        ocr_noise_ratio = 0.0
        word_split_ratio = 0.0
        page_artifact_ratio = 0.0
        score_raw = symbol_ratio * 25 + short_line_ratio * 12
        mode = "plain_text"

    elif file_type in rich_text:
        cleaned = clean_text_for_rich_text(original)
        symbol_ratio = detect_symbol_ratio(cleaned)
        short_line_ratio = detect_short_line_ratio(cleaned)
        broken_line_ratio = detect_broken_line_ratio(cleaned)
        repeated_punct_ratio = 0.0
        ocr_noise_ratio = 0.0
        word_split_ratio = 0.0
        page_artifact_ratio = 0.0
        score_raw = symbol_ratio * 18 + short_line_ratio * 10 + broken_line_ratio * 12
        mode = "rich_text"

    elif file_type in pdf_types:
        cleaned = clean_text_for_pdf(original, is_ocr=is_ocr)
        symbol_ratio = detect_symbol_ratio(cleaned)
        short_line_ratio = detect_short_line_ratio(cleaned)
        broken_line_ratio = detect_broken_line_ratio(cleaned)
        repeated_punct_ratio = detect_repeated_punct_ratio(cleaned)
        ocr_noise_ratio = detect_pdf_ocr_like_noise(cleaned) if is_ocr else 0.0
        word_split_ratio = detect_word_split_ratio(original) if is_ocr else 0.0
        page_artifact_ratio = detect_page_artifact_ratio(original)
        score_raw = (
            symbol_ratio * 10
            + short_line_ratio * 8
            + broken_line_ratio * 12
            + repeated_punct_ratio * 18
            + ocr_noise_ratio * 16
            + word_split_ratio * 10
            + page_artifact_ratio * 12
        )
        mode = "pdf_ocr" if is_ocr else "pdf"

    else:
        cleaned = normalize_text_basic(original)
        symbol_ratio = detect_symbol_ratio(cleaned)
        short_line_ratio = detect_short_line_ratio(cleaned)
        broken_line_ratio = detect_broken_line_ratio(cleaned)
        repeated_punct_ratio = detect_repeated_punct_ratio(cleaned)
        ocr_noise_ratio = 0.0
        word_split_ratio = 0.0
        page_artifact_ratio = 0.0
        score_raw = symbol_ratio * 20 + short_line_ratio * 10 + broken_line_ratio * 10
        mode = "unknown"

    score = min(100.0, round(max(score_raw * 100, 3.0), 1))

    return {
        "score": score,
        "mode": mode,
        "cleaned": cleaned,
        "charcount": len(cleaned),
        "symbol_ratio": round(symbol_ratio * 100, 2),
        "short_line_ratio": round(short_line_ratio * 100, 2),
        "broken_line_ratio": round(broken_line_ratio * 100, 2),
        "repeated_punct_ratio": round(repeated_punct_ratio * 100, 2),
        "ocr_noise_ratio": round(ocr_noise_ratio * 100, 2),
        "word_split_ratio": round(word_split_ratio * 100, 2),
        "page_artifact_ratio": round(page_artifact_ratio * 100, 2),
    }
