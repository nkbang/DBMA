import os
import re
import hashlib
from collections import Counter


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
    text = re.sub(r"\\[[0-9]{1,3}\\]", "", text)
    text = re.sub(r"\\(\\s\*[0-9]{1,3}\\s\*\\)", "", text)
    return text.strip()


def clean_text_for_pdf(text: str, is_ocr: bool = False) -> str:
    text = normalize_text_basic(text)
    text = re.sub(r"(?m)^[ \t]*\d+[ \t]*$", "", text)
    text = re.sub(r"(?m)^[ \t]*page\s+\d+[ \t]*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    if is_ocr:
        text = re.sub(r"[|¦]{2,}", " ", text)
        text = re.sub(r"[~`^]{2,}", " ", text)
        text = re.sub(r"(?m)^[^\w가-힣]{3,}$", "", text)

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
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return 0.0
    broken = 0
    for ln in lines[:-1]:
        if re.search(r"[A-Za-z가-힣0-9]$", ln) and not re.search(r"[.!?)]$", ln):
            broken += 1
    return broken / len(lines)


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


def calculate_noise_score(text: str, file_type: str = "", is_ocr: bool = False) -> dict:
    original = text or ""
    file_type = (file_type or "").lower().replace(".", "")

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
        score_raw = symbol_ratio * 25 + short_line_ratio * 12
        mode = "plain_text"

    elif file_type in rich_text:
        cleaned = clean_text_for_rich_text(original)
        symbol_ratio = detect_symbol_ratio(cleaned)
        short_line_ratio = detect_short_line_ratio(cleaned)
        broken_line_ratio = detect_broken_line_ratio(cleaned)
        repeated_punct_ratio = 0.0
        ocr_noise_ratio = 0.0
        score_raw = symbol_ratio * 18 + short_line_ratio * 10 + broken_line_ratio * 12
        mode = "rich_text"

    elif file_type in pdf_types:
        cleaned = clean_text_for_pdf(original, is_ocr=is_ocr)
        symbol_ratio = detect_symbol_ratio(cleaned)
        short_line_ratio = detect_short_line_ratio(cleaned)
        broken_line_ratio = detect_broken_line_ratio(cleaned)
        repeated_punct_ratio = detect_repeated_punct_ratio(cleaned)
        ocr_noise_ratio = detect_pdf_ocr_like_noise(cleaned) if is_ocr else 0.0

        score_raw = (
            symbol_ratio * 10
            + short_line_ratio * 10
            + broken_line_ratio * 15
            + repeated_punct_ratio * 10
            + ocr_noise_ratio * 15
        )
        mode = "pdf_ocr" if is_ocr else "pdf_text"

    else:
        cleaned = normalize_text_basic(original)
        symbol_ratio = detect_symbol_ratio(cleaned)
        short_line_ratio = detect_short_line_ratio(cleaned)
        broken_line_ratio = 0.0
        repeated_punct_ratio = 0.0
        ocr_noise_ratio = 0.0
        score_raw = symbol_ratio * 20 + short_line_ratio * 10
        mode = "generic"

    score = max(0.0, min(score_raw * 3.5, 100.0))

    return {
        "score": round(score, 2),
        "mode": mode,
        "file_type": file_type,
        "charcount": len(cleaned),
        "symbol_ratio": round(symbol_ratio * 100, 2),
        "short_line_ratio": round(short_line_ratio * 100, 2),
        "broken_line_ratio": round(broken_line_ratio * 100, 2),
        "repeated_punct_ratio": round(repeated_punct_ratio * 100, 2),
        "ocr_noise_ratio": round(ocr_noise_ratio * 100, 2),
        "cleaned_text": cleaned,
        "counter": Counter(cleaned).most_common(10),
    }

