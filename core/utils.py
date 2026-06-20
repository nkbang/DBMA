import re
import unicodedata
import streamlit as st
from typing import Dict, List


def fmt_size(b: int) -> str:
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


def make_safe_stem(filename: str) -> str:
    import os
    name, ext = os.path.splitext(filename)
    return f"{name}__{ext.lower().replace('.', '')}"


def noise_color(score: float) -> str:
    if score <= 20:
        return "#3fb950"
    if score <= 40:
        return "#d29922"
    return "#f85149"


def noise_label(score: float) -> str:
    if score <= 20:
        return "GOOD"
    if score <= 40:
        return "WARN"
    return "BAD"


def apply_select_all() -> None:
    newval = st.session_state.select_all
    for key in list(st.session_state.keys()):
        if key.startswith("sel_"):
            st.session_state[key] = newval


def on_item_change() -> None:
    selkeys = [k for k in st.session_state if k.startswith("sel_")]
    if selkeys:
        st.session_state.select_all = all(st.session_state[k] for k in selkeys)


def calculate_noise_score(text: str) -> Dict:
    if not text or len(text) < 50:
        return {
            "total": 100.0,
            "symbolratio": 40.0,
            "shortline": 30.0,
            "blankratio": 15.0,
            "repeatratio": 15.0,
            "charcount": len(text) if text else 0,
            "linecount": 1,
            "wordcount": 0,
            "langdetected": "",
        }

    text = unicodedata.normalize("NFC", text)
    lines = text.splitlines()
    charcount = len(text)
    wordcount = len(text.split())
    linecount = len(lines)

    has_korean = bool(re.search(r"[가-힣]", text))
    has_hebrew = bool(re.search(r"[\u05b0-\u05ea\u0591-\u05f4]", text))
    has_greek = bool(re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", text))
    has_english = bool(re.search(r"[a-zA-Z]", text))
    langdetected = "ko" if has_korean else "he" if has_hebrew else "el" if has_greek else "en" if has_english else ""

    allowed = re.compile(r"[가-힣a-zA-Z\u05b0-\u05ea\u0591-\u05f4\u0370-\u03ff\u1f00-\u1fff0-9\s\.,!?\-:;\\(\\)\\[\\]\{\}\'\"/\\%&@#\*\+=_]")
    nonallowed = sum(1 for ch in text if not allowed.match(ch))
    symscore = min((nonallowed / max(charcount, 1)) * 40 * 5, 40.0)

    shortlines = sum(1 for ln in lines if 0 < len(ln.strip()) < 20)
    slscore = min((shortlines / max(linecount, 1)) * 30 * 2, 30.0)

    blanklines = sum(1 for ln in lines if not ln.strip())
    blscore = min((blanklines / max(linecount, 1)) * 15 * 3, 15.0)

    repeats = len(re.findall(r"(.)\1{3,14}", text))
    rpscore = min(repeats * 3.0, 15.0)

    total = symscore + slscore + blscore + rpscore
    return {
        "total": round(total, 2),
        "symbolratio": round(symscore, 2),
        "shortline": round(slscore, 2),
        "blankratio": round(blscore, 2),
        "repeatratio": round(rpscore, 2),
        "charcount": charcount,
        "linecount": linecount,
        "wordcount": wordcount,
        "langdetected": langdetected,
    }


def detect_langs(text: str) -> List[str]:
    found = []
    if any("\u0600" <= c <= "\u06ff" or "\u05b0" <= c <= "\u05ea" for c in text):
        found.append("he")
    if any("\u0370" <= c <= "\u03ff" or "\u1f00" <= c <= "\u1fff" for c in text):
        found.append("el")
    if any("가" <= c <= "힣" for c in text):
        found.append("ko")
    if any(c.isascii() and c.isalpha() for c in text[:5000]):
        found.append("en")
    return found
