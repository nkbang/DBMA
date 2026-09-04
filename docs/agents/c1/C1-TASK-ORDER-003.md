# C1 Task Order 003 — Chunk Overflow 수정 (TDD 게이팅, 코드 작업)

발급: CUE (2026-07-20)
대상: C1 (Cline 작업창 #1, **모델: `qwen3.6:35b-DBMAcode`** — 코딩 전용,
`dbma-planner-r1-q6:70b`가 아님. Cline 모델 선택기에서 반드시 이 모델로
전환한 뒤 시작할 것)
성격: **코드 수정** — 오늘 세션 최초로 C1에게 실제 프로덕션 코드 작업을
맡기는 시도. [[feedback_c1_routing_criteria]]의 "코드는 CUE 전담" 원칙을
**TDD 게이팅**으로 완화: 성공 기준이 사람의 diff 리뷰가 아니라 **이미
작성된 테스트의 통과 여부**로 기계적으로 판정되므로, r1-planner가
자유 서술에서 반복 실패했던 것과 다른 위험 프로파일이다.

---

## 1. 목표

`core/text_normalizer.py::_merge_sentence_fragments()`를 수정해
`tests/test_merge_sentence_fragments_overflow.py`의 실패하는 테스트
2개를 통과시켜라. 통과하는 3개(회귀 가드)는 계속 통과해야 한다.

## 2. 배경 (VERIFIED)

`docs/PREFLIGHT-split-sentences-mixed-chunk-overflow.md`가 확정한
근본 원인: production에서 이 함수는 항상 "이미 max_chars를 초과한
문장 1개"를 입력으로 받는데(상위 호출부의 다른 버그, 이번 작업
범위 밖), 현재 코드(`core/text_normalizer.py:404-406`)는:

```python
if len(sent) > max_chars:
    flush(carry_overlap=False)
    chunks.append(sent)   # ← 자르지 않고 통째로 추가 (버그)
    continue
```

`scripts/shadow_chunk_overflow_audit.py` 실측: Beta corpus 12개 문서 중
영문 4개에서 전체 청크의 4.6%(352/7736)가 1.5x 상한(1800자) 초과,
최악 6511자(target 1200의 5.4배).

## 3. 반드시 지킬 것 (Scope — 위반 시 반려)

- **수정 파일은 `core/text_normalizer.py` 하나만.** `core/
  chunking_optimizer.py`를 포함해 다른 파일은 절대 건드리지 마라.
- **`core/chunking_optimizer.py`를 import하지 마라.** 이미 그 반대
  방향(`chunking_optimizer.py` → `text_normalizer.py`)으로 의존하고
  있어, 반대로 import하면 순환 의존이 생긴다. 필요한 word-safe 절단
  로직은 `text_normalizer.py` 안에서 독립적으로 구현하라(참고용으로
  `core/chunking_optimizer.py`의 `_slice_preserving_words()` 함수의
  *동작 방식*은 봐도 되지만, import는 금지).
- **`tests/test_merge_sentence_fragments_overflow.py` 파일 자체는
  수정하지 마라.** assert를 완화하거나 테스트를 지우는 방식으로
  "통과"시키는 것은 반려 사유다.
- **`_merge_sentence_fragments()`의 함수 시그니처(인자/반환 타입)는
  바꾸지 마라** — 호출부(`core/chunking_optimizer.py:324`)가 그대로
  동작해야 한다.
- 짧은 문장이 여러 개 들어와 정상 병합되는 기존 동작(테스트
  `test_normal_short_fragments_still_merge_as_before`)은 **절대
  바뀌면 안 된다.**

## 4. 완료 조건 (기계적으로 검증됨 — CUE가 그대로 실행)

```bash
cd /Users/David/DBMA
~/envs/dbma311/bin/python -m pytest tests/test_merge_sentence_fragments_overflow.py -v
~/envs/dbma311/bin/python -m pytest tests/ -q   # 전체 회귀, 534개 기존 통과 유지
~/envs/dbma311/bin/python scripts/shadow_chunk_overflow_audit.py   # 4.6% → 0% 확인
```

다섯 조건 모두 참이어야 완료:
- [ ] `test_merge_sentence_fragments_overflow.py`의 5개 테스트 전부 PASSED
- [ ] `pytest tests/ -q`가 기존 534개 + 신규 5개 = 539개 전부 PASSED, 0 FAILED
- [ ] `shadow_chunk_overflow_audit.py` 재실행 시 `over_cap` 비율이 0%(또는
      명확히 감소)
- [ ] `git diff -- core/text_normalizer.py`가 `_merge_sentence_fragments()`
      함수 내부로 국한됨 (다른 함수/파일 변경 없음)
- [ ] `git diff -- core/chunking_optimizer.py`가 빈 diff (무변경)

## 5. C1에게 보낼 프롬프트

```text
너는 DBMAcode다. 프로덕션 Python 코드를 정확하게 수정하는 것이 임무다.
API/파일경로/라이브러리 동작을 지어내지 마라. 불확실하면 질문하라.
최소·직접·실행가능한 코드만 작성하라. 기존 아키텍처를 보존하라.

작업: /Users/David/DBMA/core/text_normalizer.py의 _merge_sentence_
fragments() 함수를 수정해서, /Users/David/DBMA/tests/test_merge_
sentence_fragments_overflow.py의 실패하는 테스트 2개
(test_oversized_single_fragment_never_exceeds_max_chars,
test_reproduces_preflight_synthetic_scale)를 통과시켜라.

현재 버그(text_normalizer.py 약 404-406행):
    if len(sent) > max_chars:
        flush(carry_overlap=False)
        chunks.append(sent)   # 자르지 않고 통째로 추가 — 이게 버그
        continue

요구사항:
1. sent가 max_chars를 초과하면, 통째로 append하지 말고 공백 경계에서만
   자르는 word-safe hard slice를 적용해 각 조각이 max_chars 이하가
   되게 하라. 단어 중간을 자르면 안 된다.
2. core/text_normalizer.py 파일 하나만 수정하라. 다른 파일은 손대지 마라.
3. core/chunking_optimizer.py를 import하지 마라 (순환 의존 발생).
4. tests/test_merge_sentence_fragments_overflow.py 파일 자체는 수정하지
   마라.
5. _merge_sentence_fragments()의 함수 시그니처(인자/반환 타입)를 바꾸지
   마라.
6. 기존에 통과하던 테스트(짧은 문장 여러 개 병합)는 계속 통과해야 한다.

작업 후 다음을 실행해서 결과를 보여줘:
cd /Users/David/DBMA && ~/envs/dbma311/bin/python -m pytest tests/test_merge_sentence_fragments_overflow.py -v
```

## 6. CUE 사후 처리

1. C1이 코드를 수정하면, CUE가 §4의 5개 조건을 **직접 재실행해서**
   확인한다(C1의 자체 보고를 신뢰하지 않는다).
2. 5개 조건 모두 통과해야 커밋 후보. 하나라도 실패하면 되돌리고
   CUE가 직접 구현한다.
3. 통과하면 `git diff -- core/text_normalizer.py`를 사용자에게 보여주고
   커밋 승인을 받는다.
4. 결과를 `feedback_c1_routing_criteria.md`에 **새 카테고리**(코드
   수정, TDD 게이팅, qwen3.6:35b-DBMAcode)로 기록한다 — 기존 문서
   값 치환 shadow 카운터와는 별도로 추적.
