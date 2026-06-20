import os
from bs4 import BeautifulSoup
from docx import Document
from ebooklib import epub, ITEM_DOCUMENT
from striprtf.striprtf import rtf_to_text


def read_text_file(path: str) -> str:
    encodings = ["utf-8", "utf-8-sig", "cp949", "euc-kr"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as fh:
                return fh.read()
        except Exception:
            continue
    raise ValueError(f"텍스트 파일 인코딩을 읽을 수 없습니다: {os.path.basename(path)}")


def extract_text_from_txt(path: str) -> str:
    return read_text_file(path)


def extract_text_from_md(path: str) -> str:
    return read_text_file(path)


def extract_text_from_html(path: str) -> str:
    raw = read_text_file(path)
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def extract_text_from_docx(path: str) -> str:
    doc = Document(path)
    parts = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            parts.append(text)
    for table in doc.tables:
        for row in table.rows:
            row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_text:
                parts.append(" | ".join(row_text))
    return "\n\n".join(parts).strip()


def extract_text_from_epub(path: str) -> str:
    book = epub.read_epub(path)
    texts = []
    for item in book.get_items():
        if item.get_type() == ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text("\n", strip=True)
            if text:
                texts.append(text)
    return "\n\n".join(texts).strip()


def extract_text_from_rtf(path: str) -> str:
    raw = read_text_file(path)
    return rtf_to_text(raw).strip()


def extract_text_from_pdf(path: str, converter) -> str:
    result = converter.convert(path)
    if not result or not result.document:
        raise ValueError("PDF 변환 실패")
    full_text = result.document.export_to_markdown()
    if not full_text or not full_text.strip():
        raise ValueError("PDF/OCR 결과가 비어 있습니다")
    return full_text


def extract_text_from_file(path: str, converter=None) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        if converter is None:
            raise ValueError("PDF 처리에 converter가 필요합니다")
        return extract_text_from_pdf(path, converter)
    if ext == ".txt":
        return extract_text_from_txt(path)
    if ext == ".md":
        return extract_text_from_md(path)
    if ext in [".html", ".htm"]:
        return extract_text_from_html(path)
    if ext == ".docx":
        return extract_text_from_docx(path)
    if ext == ".epub":
        return extract_text_from_epub(path)
    if ext == ".rtf":
        return extract_text_from_rtf(path)
    raise ValueError(f"지원하지 않는 형식: {ext}")
