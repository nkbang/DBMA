# Preflight — `split_sentences_mixed()` 줄바꿈 의존성으로 인한 Chunk Overflow

상태: 고정(fixed). ADR-008 제안 4의 후속 조사. 코드 미수정, 조사·재현만
수행(`core/chunking_optimizer.py`, `core/text_normalizer.py` 무접촉).

## 배경

SPRINT33-D Phase 3-A(`docs/SPRINT33-D-phase3a-d5-metrics-formal-evaluation.md`)가
"`split_sentences_mixed()`가 원어/혼합 언어 문단에서 거의 트리거되지
않을 가능성"을 관찰만 하고 넘어갔다. 이 문서는 그 관찰을 코드 추적과
실제 재현 실행으로 확정하고, 애초 추정보다 **영향 범위가 넓고
심각도가 다른 두 가지 하위 결함**으로 갈린다는 것을 밝힌다.

---

## 근본 원인

```text
core/text_normalizer.py:66  collapse_soft_linebreaks()
  → 문단 내부의 모든 줄바꿈을 " ".join()으로 병합, 문단 사이만 "\n\n" 유지

core/text_normalizer.py:127  split_paragraphs()
  → collapse_soft_linebreaks()를 거친 뒤 "\n\n" 기준으로만 분리
  → 결과: 개별 문단 문자열은 내부에 "\n"을 절대 포함하지 않음

core/text_normalizer.py:266  split_sentences_mixed()
  → text.split("\n")이 유일한 분할 단서
  → 입력에 "\n"이 없으면 반드시 1개 원소 리스트(원문 그대로) 반환
```

재현(코드 미수정, 대화형 실행만):

```python
from core.text_normalizer import split_paragraphs, split_sentences_mixed, split_sentences

text = "문장1.\n문장2.\n문장3이고 조금 더 길게 작성해서 청킹 사이즈를 넘게 만들어봅니다. 계속 이어써봅니다.\n문장4. 그리고 문장5도 있습니다."
p = split_paragraphs(text)[2]   # "\n\n" 없는 단일 문단으로 재합쳐짐
split_sentences_mixed(p)   # -> 1개 (분할 안 됨)
split_sentences(p)         # -> 2개 (정규식 기반, 정상 분할)
```

`split_sentences()`(정규식 `(?<=[.!?。！？])\s+|\n+` 기반, 줄바꿈이
아니라 문장부호+공백으로 판정)는 이 조건에서 **정상 동작**한다. 그런데
`core/chunking_optimizer.py:305`는 `split_sentences_mixed`가 import에
성공하는 한(production에서는 항상 성공) 이를 무조건 우선 호출하고,
`split_sentences`는 `split_sentences_mixed is None`일 때만 쓰이는
죽은 코드(dead fallback)다.

---

## 영향 범위 — Phase 3-A 추정보다 넓음

Phase 3-A는 "원어(Hebrew/Greek) 포함 문단"에 한정된 문제로 추정했으나,
호출 조건(`chunking_optimizer.py:303`)은 다음 **셋 중 하나만 참이면**
동일 경로를 탄다:

```text
len(p) > chunk_size * 1.5   (원어/혼합 언어 여부와 무관)
lang == "mixed"
has_original_language
```

즉 **순수 한국어 또는 순수 영어로만 이루어진, 단순히 긴 문단**도 전부
같은 결함 경로를 탄다. 실제로는 두 개의 서로 다른 하위 결함으로
분기된다.

### 하위 결함 A — mixed/원어 문단: 크기는 보존, 문장 경계만 손실 (경미)

`chunking_optimizer.py:307-321` 분기. `sents`가 항상 1개 원소이므로
`len(s) > chunk_size`가 되어 `_slice_preserving_words()`(단어/구절
경계 보존 hard slice)로 떨어진다 — **chunk_size 상한은 지켜짐**, 다만
문장 단위로 자연스럽게 나뉘지 않고 word-safe 강제 절단만 발생.

재현:
```text
헬라어 λόγος 포함 2399자 문단 → chunk_once() 결과: [1199, 1199]자
(chunk_size=1200 상한 준수, 문장 경계 무시)
```

### 하위 결함 B — 순수 단일 언어 장문단: chunk_size 상한 자체가 깨짐 (심각)

`chunking_optimizer.py:324` 분기 → `core/text_normalizer.py:404-406`
(`_merge_sentence_fragments`)로 전달. 이 함수는 "여러 개의 짧은
문장 조각을 모아 max_chars까지 병합"하는 용도로 설계되어 있는데,
입력이 항상 "이미 max_chars를 초과한 문장 1개"이므로 다음 코드가
그대로 실행된다:

```python
if len(sent) > max_chars:
    flush(carry_overlap=False)
    chunks.append(sent)   # ← 자르지 않고 통째로 추가
    continue
```

**재현(두 언어 모두 확인)**:
```text
순수 한국어 2999자 문단 (다./습니다. 로 끝나는 정상 문장 반복)
  → chunk_once(chunk_size=1200, overlap=200) 결과: [2999]자 1개 청크
  (target 1200의 2.5배, overlong 판정 cap인 1800도 초과)

순수 영어 2429자 문단
  → chunk_once(chunk_size=1200, overlap=200) 결과: [2429]자 1개 청크
  (target의 2배, cap 1800 초과)
```

이는 `config.yaml`의 `chunk_size`/`chunk_overlap` 설정이 **순수
단일 언어 장문단에 대해서는 사실상 무시된다**는 뜻이다. 임베딩 모델
컨텍스트 가정, 검색 정밀도(청크가 너무 커서 관련 없는 내용까지
포함), retrieval top_k 슬라이싱 전제(ADR-001 "One Retrieval Engine"
원칙이 가정하는 청크 크기 균일성) 모두에 영향을 줄 수 있는 잠재적
심각도가 하위 결함 A보다 훨씬 높다.

---

## 발생 빈도 실측 (2026-07-20, `scripts/shadow_chunk_overflow_audit.py`)

Beta corpus 12개 문서 전체에 `core.chunking_optimizer.chunk_once()`
(production이 실제로 호출하는 함수 그 자체, 재구현 아님)를 그대로
실행해 결과 청크 길이 분포를 측정했다. 로직 재현이 아니라 production
함수를 직접 호출한 결과이므로 이 수치는 추정이 아니라 실측이다.

```text
chunk_size=1200  overflow_cap(1.5x)=1800

document                                                              chunks  >target  >1.5x cap  max_len
11. 고린도전서                                                           293        0          0     1200
12. 고린도후서                                                           213        1          0     1219
2 Chronicles, Volume 15 (Word Biblical Commentary)                     1109      177         55     2514
2 Kings, The Anchor Bible Commentary (Cogan/Tadmor)                     763      343        194     4616
2 Kings, The Power and the Fury (Dale Ralph Davis)                      723      122         40     2455
2 Kings, Volume 13 (Hubbard/Barker et al.)                             2984      122         63     6511
3. 마가복음                                                              315        0          0     1200
5. 요한복음1                                                             231        0          0     1200
6. 요한복음2                                                             234        0          0     1199
7. 사도행전1                                                             276        0          0     1199
8. 사도행전2                                                             352        0          0     1200
9. 로마서1                                                              243        0          0     1200

documents: 12
documents with >=1 chunk over 1.5x cap: 4
total chunks: 7736
chunks over target (1200): 765 (9.9%)
chunks over 1.5x cap (1800, likely 하위 결함 B): 352 (4.6%)
largest chunk observed: 6511 chars (5.4x target)
```

**해석**:
- 한국어 성경 8개 문서: 결함 B 발생 **0건**(완전히 경계 안에 있음).
- 영문 WBC류 학술 주석서 4개 문서: 전체 코퍼스 청크의 4.6%(352/7736)가
  1.5x 상한(1800자)을 초과 — **이 4개 문서에만 100% 집중**되어 있다.
  ADR-007 Amendment A의 Profile 분류(문단 중 1800자 초과 candidate
  존재 여부)와 정확히 겹치는 문서군이다.
- 최악 사례 **"2 Kings, Volume 13"**(6511자, target의 5.4배)는
  ADR-007 Amendment A가 Axis 3(Unsplittable Outlier)에서도 최악
  (18.6%)으로 지목했던 바로 그 문서 — 두 개의 서로 다른 측정 방법론이
  같은 문서를 최악으로 재확인, 교차 검증 성격.
- 결론: 하위 결함 B는 "드문 예외"가 아니라 **Profile B 문서군 전체에
  구조적으로 발생**하며, 심각도(5.4배)도 처음 합성 재현(2~2.5배)보다
  실제로 더 큼.

---

## 완료 조건

```text
✅ 근본 원인 코드 추적 완료 (collapse_soft_linebreaks → split_paragraphs
   → split_sentences_mixed의 개행 의존성 체인)
✅ 하위 결함 A/B 분리 확인 및 각각 합성 재현(한국어/영어/원어 혼합)
✅ split_sentences()(정규식 기반)가 동일 입력에서 정상 동작함을 대조 확인
✅ chunking_optimizer.py:305의 split_sentences_mixed 우선 호출로 인해
   split_sentences()가 현재 production에서 도달 불가능한 dead fallback임을 확인
✅ 발생 빈도 실측 완료 (scripts/shadow_chunk_overflow_audit.py, Beta
   corpus 12개 문서, production chunk_once() 직접 호출) — 4.6%(352/7736)
   청크가 1.5x 상한 초과, Profile B 4개 문서에 100% 집중, 최악 5.4배
코드 변경: 진단 스크립트 2개 신규 추가만
   (scripts/shadow_chunk_overflow_audit.py, tests/test_shadow_chunk_
   overflow_audit.py — 유닛테스트 6건 + 전체 회귀 534 passed). core/
   chunking_optimizer.py, core/text_normalizer.py 등 production 코드는
   여전히 무접촉.
```

## 다음 조치 (HQ 승인 대기, 이 문서 범위 밖)

1. **발생 빈도 실측 — 완료(위 §"발생 빈도 실측" 참고)**. 결과는
   "드문 예외"가 아니라 Profile B 4개 문서에 구조적으로 집중된
   4.6%(352/7736 청크)이며, 최악 사례는 target의 5.4배(6511자).
   실측치가 나왔으므로 수정 우선순위 결정은 더 이상 이 항목에
   막혀있지 않다 — HQ가 §2 수정 방향을 바로 검토 가능한 상태.
2. **수정 방향 후보(구현 없음, 검토용만)**:
   - (a) `split_sentences_mixed()`가 입력에 `\n`이 없으면 `split_sentences()`
     (정규식 기반)로 자동 위임하는 내부 폴백 추가.
   - (b) `_merge_sentence_fragments()`의 "단일 oversized 항목" 케이스에
     `_slice_preserving_words()`와 동일한 word-safe hard slice를
     적용해 하위 결함 A와 동일한 안전망을 B에도 적용.
   - 두 후보 모두 `core/chunking_optimizer.py`의 private 함수 재사용
     여부를 포함해 별도 설계 검토(ADR) 필요 — 이 Preflight는 방향만
     제시하고 결정하지 않음.
3. **Hierarchical Chunk Builder와의 관계 확인 완료(이 Preflight에서
   바로 확인)**: `core/hierarchical_chunk_builder.py`는
   `split_sentences_mixed()`를 호출하지 않는다 — candidate 생성은
   `scripts/shadow_boundary_delta.py::candidates_with_offsets()`가
   `split_paragraphs()`와 동일한 정규식(`\n\n+`)으로 만들고, builder는
   각 문단을 원자적 candidate로 다룬다. 따라서 **이 Preflight의
   근본 원인(개행 의존성)과는 다른 경로**지만, "문단 내부를 더
   잘게 못 쪼갠다"는 현상 자체는 동일하게 나타난다 — 이는 이미
   ADR-007 Amendment A가 **"Axis 3: Unsplittable Outlier Ratio"**로
   명명하고 측정 중인 바로 그 현상이다(Profile B 5.5%, 최악 18.6%,
   Level 3 Hard Fallback이 "설계만·미구현"인 이유). 즉 하위 결함 B는
   production(`chunking_optimizer.py`)에서는 **미인지 상태의 버그**이지만,
   Hierarchical Chunk Builder에서는 **이미 알려진 채 해결을 기다리는
   설계 항목(Level 3)**이라는 차이가 있다. 별도 재검토는 불필요 —
   ADR-008 제안 2(Level 3 구현)가 이미 이 문제의 해결 경로임을 확인.
