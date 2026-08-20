"""Phase 2 §6 Upper Bound — 재현 가능한 실측 스크립트.
Read-only. Run: python3 phase2-upper-bound-recount.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
canonical = json.load(
    open(ROOT / "NAE/corpus/canonical/Fuller_Complete_Works_Vol01/canonical.json")
)

# Build candidate list (same as parser.py: MIN_CLAIM_SENTENCE_CHARS >= 25)
sentences = []
for p in canonical.get("paragraphs", []):
    if p.get("type") != "prose":
        continue
    for s in p.get("sentences", []):
        t = s.get("text", "")
        if len(t) >= 25:
            sentences.append(t)

print(f"candidates(>=25 chars): {len(sentences)}")
print()

# Layer 0: 길이 필터 (already implemented, 852 removed before candidates)
total_raw_sentences = sum(
    1 for p in canonical.get("paragraphs", [])
    if p.get("type") == "prose"
    for s in p.get("sentences", [])
    if len(s.get("text", "")) >= 0
)
short_filtered = sum(1 for p in canonical.get("paragraphs", [])
                     for s in p.get("sentences", [])
                     if p.get("type") == "prose" and len(s.get("text", "")) < 25)
print(f"L0: 길이 필터 제거 (이미 구현됨): {short_filtered}")
print()

# Layer 1b: page number / header / footer 패턴
PAGE_NUMBER_PATTERNS = [r"^p\.?\s*\d+", r"\b\d+\s*p\.?\b", r"^[IVXLC]+\.?\s*"]
HEADER_FOOTER_PATTERNS = [r"^\s*[-=]{3,}\s*$", r"^\s*\d+\s*[-=]+\s*\d+\s*$"]

page_hits = set()
header_footer_hits = set()
for i, t in enumerate(sentences):
    if any(re.search(p, t) for p in PAGE_NUMBER_PATTERNS):
        page_hits.add(i)
    if any(re.search(p, t) for p in HEADER_FOOTER_PATTERNS):
        header_footer_hits.add(i)

print(f"L1b: 페이지 번호 패턴 매칭: {len(page_hits)}")
# Show some samples
page_samples = [sentences[i] for i in sorted(page_hits)[:5]]
for s in page_samples:
    print(f"  [{len(s)}자] {s[:80]}...")

print(f"L1b-2: header/footer 패턴 매칭: {len(header_footer_hits)}")
hf_samples = [sentences[i] for i in sorted(header_footer_hits)[:5]]
for s in hf_samples:
    print(f"  [{len(s)}자] {s[:80]}...")

# Layer 2a: Exact match duplicate (hash 기반)
import hashlib
def exact_duplicate_hash(text):
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()

seen_hashes = {}
exact_dup_indices = set()
for i, t in enumerate(sentences):
    h = exact_duplicate_hash(t)
    if h in seen_hashes:
        exact_dup_indices.add(i)
    else:
        seen_hashes[h] = i

print(f"\nL2a: Exact duplicate: {len(exact_dup_indices)}")
for i in sorted(exact_dup_indices)[:3]:
    print(f"  [{len(sentences[i])}자] {sentences[i][:80]}...")

# Layer 2b: Near-duplicate (skip — requires embedding, use doc's 15 as upper bound)
print(f"\nL2b: Near-duplicate (상한선): 15 (embedding 기반, 별도 benchmark 필요)")

# Layer 3a: 지나치게 짧은 fragment (25-34자 중 단어 수 < 4)
short_frag_indices = set()
for i, t in enumerate(sentences):
    if 25 <= len(t) <= 34 and len(t.split()) < 4:
        short_frag_indices.add(i)

print(f"\nL3a: 짧은 fragment (25-34자, 단어<4): {len(short_frag_indices)}")
for i in sorted(short_frag_indices)[:5]:
    print(f"  [{len(sentences[i])}자] '{sentences[i][:60]}...' (단어수={len(sentences[i].split())})")

# Layer 3b: 반복 boilerplate
BOILERPLATE_PATTERNS = [
    r"^\s*See also\.?\s*$",
    r"^\s*Amen\.?\s*$",
    r"^\s*End of (Chapter|Section)\.\s*$",
    r"^\s*Continued\.\s*$",
    r"^\s*\.\.\.\s*$",
]
boilerplate_indices = set()
for i, t in enumerate(sentences):
    if any(re.match(p, t) for p in BOILERPLATE_PATTERNS):
        boilerplate_indices.add(i)

print(f"\nL3b: Boilerplate: {len(boilerplate_indices)}")
for i in sorted(boilerplate_indices)[:5]:
    print(f"  [{len(sentences[i])}자] '{sentences[i][:60]}...'")

# Layer 3c: OCR garbage (특수문자 비율 > 30%)
ocr_garbage_indices = set()
for i, t in enumerate(sentences):
    if len(t) == 0:
        continue
    special = sum(1 for c in t if not c.isalnum() and not c.isspace())
    if special / len(t) > 0.3:
        ocr_garbage_indices.add(i)

print(f"\nL3c: OCR garbage (특수문자>30%): {len(ocr_garbage_indices)}")
for i in sorted(ocr_garbage_indices)[:5]:
    print(f"  [{len(sentences[i])}자] '{sentences[i][:60]}...'")

# Layer 4b: 소문자 시작 — 첫 글자가 알파벳이고 소문자인지 확인
lowercase_start_indices = set()
for i, t in enumerate(sentences):
    stripped = t.lstrip()
    if stripped and stripped[0].isalpha() and stripped[0].islower():
        lowercase_start_indices.add(i)

print(f"\nL4b: 소문자 시작 (첫 알파벳이 소문자): {len(lowercase_start_indices)}")
# Compare with CUE's simpler check: t[0].islower()
lowercase_start_cue = set()
for i, t in enumerate(sentences):
    if t and t[0].islower():
        lowercase_start_cue.add(i)

print(f"L4b (CUE 방식: t[0].islower()): {len(lowercase_start_cue)}")
# Show difference
diff = lowercase_start_indices.symmetric_difference(lowercase_start_cue)
if diff:
    print(f"  차이 발생 인덱스 수: {len(diff)}")
    for i in sorted(diff)[:5]:
        t = sentences[i]
        stripped = t.lstrip()
        print(f"    idx={i}: '{t[:60]}...' (lstrip 첫자='{stripped[0] if stripped else '?'}')")

# Union of all filterable layers (excluding L0 which is already applied)
all_filterable = page_hits | header_footer_hits | exact_dup_indices | short_frag_indices | boilerplate_indices | ocr_garbage_indices | lowercase_start_indices
print(f"\n=== 합집합 (Layer 간 중복 제거) ===")
print(f"총 제거 가능 수 (중복 제거 후): {len(all_filterable)}")
print(f"비율: {len(all_filterable)/len(sentences)*100:.1f}%")

# Show overlap between page and other layers
page_overlap_short = page_hits & short_frag_indices
page_overlap_lower = page_hits & lowercase_start_indices
print(f"\n=== Layer 간 중복 분석 ===")
print(f"페이지 번호 AND 짧은 fragment: {len(page_overlap_short)}")
print(f"페이지 번호 AND 소문자 시작: {len(page_overlap_lower)}")

# Show some page number samples that are NOT short/boilerplate
non_trivial_page = page_hits - short_frag_indices - boilerplate_indices
print(f"\n페이지 번호 패턴 (비trivial, 5건 샘플):")
for i in sorted(non_trivial_page)[:5]:
    print(f"  [{len(sentences[i])}자] '{sentences[i][:80]}...'")
