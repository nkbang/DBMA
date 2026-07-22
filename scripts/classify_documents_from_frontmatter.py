#!/usr/bin/env python
"""classify_documents_from_frontmatter.py — registry 문서의 프론트 메터 기반 유형 분류."""

import json
import re
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import pypdf
except ImportError:
    pypdf = None


COMMENTARY_KEYWORDS = re.compile(
    r"(Commentary|Commentaries|Exegetical|Critical|Anchor|Word Biblical|"
    r"Holman|Biblical Commentary|T&T Clark|Eerdmans|Blackwell|Wiley-Blackwell|"
    r"주석)",
    re.IGNORECASE,
)

SERMON_KEYWORDS = re.compile(
    r"(Sermon|Sermons|Preaching|Homiletic|강해|설교|강설|설교집|"
    r"Ministry|Pastoral)",
    re.IGNORECASE,
)

LITURGY_KEYWORDS = re.compile(
    r"(Liturgy|예배|예식|전례|worship|Worship)",
    re.IGNORECASE,
)

THESIS_KEYWORDS = re.compile(
    r"(Thesis|Dissertation|Theses|Dissertations|논문|学位|博士|Master's|"
    r"Doctoral|dissertation|thesis)",
    re.IGNORECASE,
)

SERIES_KEYWORDS = re.compile(
    r"(NICNT|NIGTC|ICC|Hermeneia|AB|Anchor|WBC|Word Biblical|"
    r"Holman Christian Standard|Biblical Commentary|IVP|"
    r"New International Commentary|Theological Commentary|"
    r"Eerdmans|T&T Clark|Blackwell|Wiley)",
    re.IGNORECASE,
)


def read_first_page_pdf(filepath: Path) -> str:
    """PDF 파일의 첫 페이지 텍스트 추출."""
    text = ""
    
    # pdfplumber 우선 시도
    if pdfplumber:
        try:
            with pdfplumber.open(filepath) as pdf:
                if pdf.pages:
                    text = pdf.pages[0].extract_text() or ""
            if text.strip():
                return text
        except Exception:
            pass
    
    # pypdf 두 번째 시도
    if pypdf:
        try:
            with open(filepath, "rb") as f:
                reader = pypdf.PdfReader(f)
                if reader.pages:
                    text = reader.pages[0].extract_text() or ""
            if text.strip():
                return text
        except Exception:
            pass
    
    # fallback: 텍스트로 직접 읽기 (OCR PDF 등 실패 가능)
    try:
        text = filepath.read_text(encoding="utf-8", errors="ignore")
        if text.strip():
            return text[:5000]
    except Exception:
        pass
    
    return ""


def classify_from_frontmatter(text: str) -> tuple[str, list[str]]:
    if not text.strip():
        return "기타", ["(빈 텍스트)"]
    matched = []
    commentary_matches = COMMENTARY_KEYWORDS.findall(text)
    if commentary_matches:
        matched.extend(commentary_matches)
        return "주석", list(set(matched))
    series_matches = SERIES_KEYWORDS.findall(text)
    if series_matches:
        matched.extend(series_matches)
        return "주석", list(set(matched))
    sermon_matches = SERMON_KEYWORDS.findall(text)
    if sermon_matches:
        matched.extend(sermon_matches)
        return "설교", list(set(matched))
    liturgy_matches = LITURGY_KEYWORDS.findall(text)
    if liturgy_matches:
        matched.extend(liturgy_matches)
        return "시전", list(set(matched))
    thesis_matches = THESIS_KEYWORDS.findall(text)
    if thesis_matches:
        matched.extend(thesis_matches)
        return "논문", list(set(matched))
    return "기타", matched


def main():
    registry_path = Path("output/registry/documents.json")
    if not registry_path.exists():
        print(f"registry 파일을 찾을 수 없음: {registry_path}")
        return
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        print(f"raw 디렉토리를 찾을 수 없음: {raw_dir}")
        return

    type_counts = {"주석": 0, "설교": 0, "시전": 0, "논문": 0, "기타": 0}
    type_docs = {"주석": [], "설교": [], "시전": [], "논문": [], "기타": []}

    print("=" * 80)
    print("문서 유형 분류 결과 (프론트 메터 기반)")
    print("=" * 80)

    for doc_id, doc in registry.get("documents", {}).items():
        source_file = doc.get("source_file", "")
        if not source_file:
            continue
        pdf_path = raw_dir / source_file
        if not pdf_path.exists():
            found = False
            for f in raw_dir.rglob("*"):
                if f.is_file() and f.name == source_file:
                    pdf_path = f
                    found = True
                    break
            if not found:
                print(f"\n[미발견] {source_file}")
                type_docs["기타"].append((source_file, "파일 미발견", []))
                type_counts["기타"] += 1
                continue
        first_page_text = read_first_page_pdf(pdf_path)
        doc_type, matched_keywords = classify_from_frontmatter(first_page_text)
        type_counts[doc_type] += 1
        type_docs[doc_type].append((source_file, doc_type, matched_keywords))
        print(f"\n[{doc_type}] {source_file}")
        if matched_keywords:
            print(f"  매칭 키워드: {', '.join(matched_keywords[:5])}")
        else:
            print(f"  텍스트 길이: {len(first_page_text)} 자")

    print("\n" + "=" * 80)
    print("유형별 집계")
    print("=" * 80)
    for doc_type, count in type_counts.items():
        if count > 0:
            print(f"  {doc_type}: {count}권")

    print("\n" + "=" * 80)
    print("유형별 문서 목록")
    print("=" * 80)
    for doc_type in ["주석", "설교", "시전", "논문", "기타"]:
        if type_docs[doc_type]:
            print(f"\n--- {doc_type} ({len(type_docs[doc_type])}권) ---")
            for source_file, dtype, keywords in type_docs[doc_type]:
                kw_str = f" [{', '.join(keywords[:3])}]" if keywords else ""
                print(f"  - {source_file}{kw_str}")


if __name__ == "__main__":
    main()