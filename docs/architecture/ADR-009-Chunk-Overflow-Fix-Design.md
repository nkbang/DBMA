---
title: "ADR-009: chunk overflow 결함(하위결함 A/B) 수정 방향 설계"
category: architecture
sprint: SPRINT33-D (연속)
based_on:
  - docs/architecture/ADR-008-Semantic-Chunking-Production-Path.md (제안 4)
  - docs/PREFLIGHT-split-sentences-mixed-chunk-overflow.md
created: 2026-08-18
status: 대안 2 구현 완료(2026-08-18, HQ 지시) / 대안 1 보류
scope_modified: docs/architecture/, core/text_normalizer.py, tests/test_text_normalizer.py
---

# ADR-009: chunk overflow 결함(하위결함 A/B) 수정 방향 설계

| | |
|---|---|
| Status | Proposed |
| Date | 2026-08-18 |
| Deciders | HQ (Task Order 승인) / CUE (조사·설계) |
| Supersedes | — |
| Superseded by | — |
| Amends | 없음 (ADR-008 제안 4를 구체화하는 후속 설계) |

---

## Context

`docs/PREFLIGHT-split-sentences-mixed-chunk-overflow.md`(commit `ae78866`)가
`core/text_normalizer.py::split_sentences_mixed()`의 개행(`\n`) 의존성으로
인한 chunk overflow 결함을 코드 추적 + 재현으로 확정했다. 근본 원인은
다음 체인이다.

```
collapse_soft_linebreaks() → 문단 내부의 모든 줄바꿈을 " "로 병합
split_paragraphs()         → "\n\n" 기준으로만 문단 분리 (내부 "\n" 없음)
split_sentences_mixed()    → 오직 "\n" 기준으로만 분할 → 입력에 "\n"이
                              없으면 항상 1개 원소 리스트 반환
```

호출 조건(`core/chunking_optimizer.py:303`)은 다음 중 하나만 참이면 이
경로를 탄다: `len(p) > chunk_size * 1.5`, `lang == "mixed"`,
`has_original_language`. 즉 원어/혼합 언어 여부와 무관하게 **순수
단일 언어 장문단도 전부 같은 결함 경로**를 탄다. 이는 두 하위결함으로
갈린다.

- **하위결함 A(경미)** — `chunking_optimizer.py:307-321`(mixed/원어
  경로). `sents`가 1개 원소이므로 `_slice_preserving_words()`(word-safe
  hard slice)로 떨어져 **chunk_size 상한은 지켜지나 문장 경계가 무시**된다.
- **하위결함 B(심각)** — `chunking_optimizer.py:325`
  → `_merge_sentence_fragments()`(`text_normalizer.py:404-406`). 입력이
  "이미 max_chars를 초과한 문장 1개"이므로 `if len(sent) > max_chars:`
  분기가 그대로 실행되어 **자르지 않고 통째로 chunk에 추가**된다.
  실측: 순수 한국어 2999자, 순수 영어 2429자 문단이 각각 청크 1개로
  그대로 생성됨(target 1200의 2~2.5배, overlong cap 1800도 초과).

Preflight 문서는 원인 규명까지만 하고 수정 방향은 "후속 검토용 ADR"로
넘겼다(§4 다음 조치 2번). 이 ADR이 그 후속이다. **코드는 수정하지
않는다** — 설계 대안과 권고안만 제시하고, 실제 구현 착수는 HQ 승인
대상이다.

---

## Decision

### 이 ADR이 결정하는 것 — 없음 (설계 제안만)

아래 대안을 비교하고 권고안을 제시하되, 실제 구현 착수 여부/순서는
HQ 결정 사항이다.

### 대안 1 — `split_sentences_mixed()` 무개행 자동 위임 폴백

`split_sentences_mixed()` 내부에서, 정제 후 입력에 `"\n"`이 전혀
없으면(= `split_paragraphs()`를 거친 표준 입력 형태) 정규식 기반
`split_sentences()`로 위임한다. `split_sentences()`는 Preflight에서
동일 입력에 대해 정상 동작(2개 분할)함이 이미 확인됨.

```python
def split_sentences_mixed(text, ...):
    text = normalize_pipeline_text(text)
    if not text:
        return []
    if "\n" not in text:
        return split_sentences(text)   # 위임
    ... (기존 줄바꿈 기준 로직 유지)
```

- **장점**: 근본 원인을 직접 해소. 하위결함 A(문장 경계 손실)와
  하위결함 B(상한 붕괴)를 **동시에** 개선 — 문장이 정상적으로 분리되면
  A는 `_slice_preserving_words` 대신 자연스러운 문장 경계로, B는
  `_merge_sentence_fragments`가 여러 개의 정상 크기 문장을 받아
  정상적으로 병합·분할하게 됨.
- **단점**: `split_sentences_mixed`가 원래 갖고 있던 "언어 전환
  지점에서 버퍼링"(mixed 언어 경계 인지) 로직은 줄바꿈이 있는 입력에만
  남고, 무개행 입력에서는 완전히 우회된다 — 즉 무개행 mixed 문단은
  이제 언어 인지 없이 순수 구두점 기준으로만 분할된다. Preflight가
  이미 "원어/혼합 언어 보호 로직의 실효성 자체가 과대평가됐을 수
  있다"(ADR-008 제안 4)고 지적했으므로, 이 우회가 실질적 품질 저하인지
  Beta corpus 재현으로 검증 필요.
  - Hebrew/Greek 원어 포함 문단(`has_original_language`)은
    `_looks_like_korean_sentence_end`/`english_sentence_end` 판정
    대상이 아니라 순수 구두점(`.!?`) 기준 분리이므로, 원어 자체에
    구두점이 드물다면(성경 히브리어는 sof pasuq `׃`을 쓰지 ASCII
    마침표를 쓰지 않음) `split_sentences()`도 여전히 1개로 반환할 수
    있다 — 이 경우 하위결함 B가 재발할 수 있으므로 대안 2와 병행이
    필요하다(아래 권고안 참고).

### 대안 2 — `_merge_sentence_fragments()` oversized 단일 항목 word-safe hard slice

`_merge_sentence_fragments()`의 `if len(sent) > max_chars:` 분기
(`text_normalizer.py:404-406`)에서 자르지 않고 그대로 추가하는 대신,
`core/chunking_optimizer.py::_slice_preserving_words()`와 동일한
word-safe hard slice를 적용한다.

- **장점**: chunk_size 상한을 **어떤 입력에서도 절대 위반하지 않는
  안전망**이 된다. 대안 1이 해소하지 못하는 잔여 케이스(원어 구두점
  부재, 극단적으로 긴 단일 문장 등)까지 방어.
- **단점**: 이 함수는 현재 `core/chunking_optimizer.py`뿐 아니라 다른
  호출부에서도 재사용될 수 있어(grep 필요, 아래 검증 항목 참고) 영향
  범위를 별도 확인해야 한다. Amendment A 원칙(private 함수 직접 import
  금지)에 따라 `_slice_preserving_words`를 그대로 import하지 않고
  `text_normalizer.py` 내부에 동등 구현을 두거나 공용 유틸로 승격해야
  한다 — 코드 중복 대 공용화 여부는 구현 단계에서 결정.

### 권고안 — 대안 1 + 대안 2 병행 (원인 해소 + 안전망)

Preflight의 두 후보를 양자택일이 아니라 **계층적으로 병행** 적용할
것을 권고한다.

1. 대안 1(무개행 위임)을 1차 방어선으로 적용 — 정상적인 산문 문단
   대부분에서 근본적으로 문장 경계를 복원해 A/B를 함께 해소.
2. 대안 2(word-safe hard slice)를 `_merge_sentence_fragments`에
   최종 안전망으로 적용 — 대안 1 이후에도 남을 수 있는 "구두점 없는
   초장문 단일 문장"(원어 인용, 목록형 텍스트 등) 케이스에서
   chunk_size 상한을 절대 보장.

두 대안을 함께 적용하면 "정상 케이스는 자연스러운 문장 경계, 예외
케이스는 최소한 크기 상한 보장"이라는 이중 방어 구조가 되어, Amendment
A가 Hierarchical Chunk Builder에 이미 적용한 "Level 1(의미 경계) +
Level 2(안전 상한)" 원칙과 production 경로에서도 일관성을 갖는다.

### 명시적으로 제안하지 않는 것

- `split_sentences_mixed()`의 언어 전환 버퍼링 로직 자체를 폐기하는
  것은 제안하지 않는다 — 줄바꿈이 있는 입력(PDF 추출 등 원본 구조가
  남아있는 경우)에서는 여전히 유효할 수 있으므로, 무개행 케이스에만
  위임을 추가하는 것으로 범위를 한정한다.
- Hierarchical Chunk Builder(`core/hierarchical_chunk_builder.py`)로의
  즉시 대체는 제안하지 않는다 — ADR-008이 이미 "§1 threshold 미확정,
  Level 3 미구현 상태에서 전환 금지"로 명시했고, 이 ADR의 범위는
  production 경로(`chunking_optimizer.py`)의 국소 결함 수정에
  한정된다.

---

## Consequences

### 이 ADR로 확정되는 것
- 없음 — 대안 비교와 권고안(대안 1+2 병행) 정리만 문서화.

### 이 ADR로 확정되지 않는 것 (전부 후속 HQ 승인 대상)
- 실제 구현 착수 여부/일정.
- `_slice_preserving_words` 동등 구현을 `text_normalizer.py`에 복제할지
  공용 유틸로 승격할지.
- 대안 1의 "무개행 mixed 문단 언어 인지 우회" 영향을 Beta corpus로
  재현·정량화할지(구현 전 사전 검증 vs 구현 후 회귀 테스트로 확인).

### 리스크
- 대안 1 단독 적용 시 원어 인용문(성경 히브리어 sof pasuq 등)처럼
  ASCII 구두점이 없는 텍스트에서 하위결함 B가 재발할 수 있음 — 권고안대로
  대안 2 병행이 필수인 이유.
- 대안 2의 `_slice_preserving_words` 재사용 범위를 확인하지 않고
  진행하면, 다른 호출부에 의도치 않은 동작 변화를 줄 수 있음(구현
  착수 시 `grep -rn _slice_preserving_words` 선행 필요).
- 두 대안 모두 청크 경계가 바뀌므로 기존 회귀 테스트(`tests/` 520+
  passed 기준선)와 D-5 metric(Axis 1/2/3) 재측정이 필요 — 순수 문서
  뿐 아니라 mixed/원어 문서 프로파일(Beta corpus Profile B)에 대한
  회귀 확인이 특히 중요.

---

## 검증 계획 (구현 착수 시)

1. `grep -rn "_slice_preserving_words\|_merge_sentence_fragments\|split_sentences_mixed"`로
   전체 호출부 확인 — production 경로 외 영향 범위 사전 파악.
2. 단위 테스트: Preflight의 3개 재현 케이스(한국어 2999자, 영어 2429자,
   헬라어 혼합 2399자 문단)를 회귀 테스트로 고정 — 수정 후 모든 청크가
   `chunk_size` 상한(및 overlong cap 1800) 이내인지 단언.
2-1. 원어 sof-pasuq 전용 케이스(구두점 없는 장문 히브리어 인용) 추가
   재현 — 대안 1만으로는 해소되지 않음을 확인하는 회귀 테스트.
3. Beta corpus 12개 문서 전체에 대해 `scripts/shadow_d5_metrics.py` 패턴을
   재사용해 하위결함 B(`len(chunk) > chunk_size * 1.5`) 발생률을
   수정 전/후로 비교.
4. 기존 `tests/` 전체 회귀(현재 기준선 520+ passed) 확인.

---

## Next Steps (HQ 승인 대기)

1. ~~이 ADR(대안 비교·권고안)에 대한 HQ 승인 여부 결정.~~ → HQ가 2026-08-18
   구현 진행을 지시(대화 지시, 별도 문서화된 Task Order 없음).
2. ~~승인 시 우선순위: ① Beta corpus 발생 빈도 실측~~ → 이 세션(원격) 환경에
   `output/`(생성된 corpus 산출물) 자체가 없어 실측 불가 확인. 순서를
   바꿔 **대안 2(안전망)만 우선 구현**하고 대안 1은 보류.

### 구현 결과 (2026-08-18)

- **대안 2 구현 완료**: `text_normalizer.py::_merge_sentence_fragments()`에
  신규 헬퍼 `_word_safe_hard_slice()` 추가, oversized 단일 문장을
  chunk_size 이내로 word-safe hard slice. `_slice_preserving_words`는
  이동하지 않고 독립 사본으로 둠(공용 유틸 승격은 이 ADR 범위 밖, 향후
  drift 방지에 주의 — §Consequences에서 이미 지적한 리스크).
  회귀 테스트 3건 추가(`tests/test_text_normalizer.py::
  TestMergeSentenceFragmentsOversizedUnit`), 기존 `tests/test_text_normalizer.py`
  11건 + `tests/test_chunking_optimizer.py` 19건 전부 통과(이 세션에서
  실행 가능한 스위트 기준 — `tests/` 전체 520+ 기준선은 로컬 확인 필요).
- **대안 1은 이번 구현에서 보류**: `grep -rn split_sentences_mixed`로
  확인한 결과 `core/utils.py::detect_broken_line_ratio()`(품질 노이즈
  점수 산정에 사용, 원문 그대로의 줄바꿈 유지 텍스트에 호출)와
  `scripts/shadow_d5_metrics.py`(Axis 3 unsplittable outlier 정의 자체가
  `split_sentences_mixed(text) <= 1`)가 이 함수의 **현재** 줄바꿈 의존
  동작에 암묵적으로 기대고 있음이 확인됐다. 무개행 위임(대안 1)을
  추가하면 이 두 호출부의 동작/지표 정의가 함께 바뀌는데, Beta corpus
  재측정으로 회귀를 검증할 방법이 이 세션에는 없어 리스크를 감수하고
  진행하지 않았다. 대안 2는 이런 부작용이 없는 순수 안전망(상한 초과
  케이스에서만 발동, 기존에도 깨져 있던 경로)이라 우선 적용.
3. `_slice_preserving_words` 코드 중복 vs 공용 유틸 승격 여부는 여전히
   결정되지 않음(이 ADR 범위 밖).
4. 대안 1(무개행 위임)과 Beta corpus 발생 빈도 실측은 로컬(Mac) 환경에서
   `output/beta_validation_v5/` 데이터를 갖고 별도로 진행 필요 — 순서는
   원안대로 ① 빈도 실측 → ② 대안 1 구현 → ③ `core/utils.py`/
   `scripts/shadow_d5_metrics.py` 영향 확인 → ④ D-5 metric 재측정.
