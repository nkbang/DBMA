---
title: "ADR-011: Header/Footer Repetition Detector — 한글 PDF 주석서 디노이즈·청킹 고도화"
category: architecture
sprint: SPRINT33-D (연속)
based_on:
  - docs/SPRINT33-D-preflight-issues.md (§2 PageHeaderArtifact)
  - core/noise_classifier.py (§SPRINT28-B "Best-effort only" 주석)
  - docs/architecture/ADR-007-Amendment-A.md
  - docs/architecture/ADR-008-Semantic-Chunking-Production-Path.md
created: 2026-07-22
status: Architecture Decision (제안 — 구현 전, HQ 승인 대기)
scope_modified: docs/architecture/ only (코드 미수정)
---

# ADR-011: Header/Footer Repetition Detector

| | |
|---|---|
| Status | Proposed |
| Date | 2026-07-22 |
| Deciders | HQ (승인) / CUE (조사·설계) |
| Supersedes | — |
| Amends | 없음 — ADR-007/Amendment A·ADR-008이 미룬 항목의 후속 제안 |

---

## Context

**질문**: "청킹의 고수준 결과와 디노이즈를 위해 CUE가 다음에 할 일은
무엇인가 — 한글 PDF 주석(commentary) 처리 고도화를 우선 설계하라."

조사 결과, **동일한 미해결 결함이 이미 두 곳에서 독립적으로 발견되어
있었다** — 지금까지 서로 연결되지 않은 채 각자 "별도 과제"로 미뤄진
상태였다.

### 1. 디노이즈 계층 — `core/noise_classifier.py`

`HEADER_FOOTER`는 이미 `NoiseType`에 존재하고 정책도 `REMOVE`로
정해져 있다. 그런데 실제 판정 로직(`_looks_like_byline_block()`)은
**청크 1개만 보고 판단하는 단발성 휴리스틱**(짧고 문장부호 없는
줄 1~4개)이다. 모듈 자체 주석(91-98행)이 이미 이렇게 명시한다:

> "Reliable header/footer detection requires cross-page repetition
> frequency (SPRINT28-A §3 'Header/Footer Intelligence Layer',
> deferred to SPRINT28-C) — this function sees one chunk's text in
> isolation..."

즉 "페이지마다 반복되는 헤더"라는 본질적 특징(반복 빈도)을 전혀 안
쓰고 있다 — SPRINT28-C가 이 갭을 메우기로 돼 있었으나 아직 미착수.

### 2. 청킹 고수준 결과 — `core/hierarchical_chunk_builder.py` (dormant)

SPRINT33-D Preflight §2(PageHeaderArtifact)가 독립적으로 같은 문제를
발견했다. "2 Kings, Volume 13"(주석서, Profile B 최악 사례) 실측:

```
동일 성구 참조 반복 등장 간격(candidate 순번 기준):
  min=9, median=25, max=1609(이상치), 대부분 9~56 구간
Feasibility: PASS — "최근 W개(W≈60~100) candidate 이내 동일 참조가
  이미 boundary로 판정됐는가"를 보는 stateful feature가 기술적으로 타당
Implementation: NOT APPROVED — "별도 ADR 필요"로 명시적으로 보류됨
```

이게 지금까지 Profile B(학술 주석서) 문서들이 Axis 3(unsplittable
outlier)에서 계속 나쁜 점수를 받아온 원인 중 하나로 추정된다(ADR-008
§Context: Profile B 5.5%, 최악 18.6%) — running header가 매 페이지
"새로운 semantic 신호"처럼 잘못 인식되면서 실제 문단 경계 판단을
왜곡한다.

### 왜 지금까지 안 고쳐졌나

두 소비처(디노이즈 vs 청킹) 모두 **같은 근본 능력**(반복 빈도 추적)을
필요로 하는데, 각자의 조사 시점엔 서로를 몰랐다. `noise_classifier.py`는
단일 청크만 보는 stateless 구조이고, `semantic_boundary_detector.py`의
5개 feature도 전부 stateless다(SPRINT33-D Preflight §2 결정 근거:
"기존 5개 feature는 전부 candidate 1개만으로 판단 가능한 stateless
구조"). 반복 빈도 추적은 **문서 전체에 걸친 상태(state)를 필요로 하는
첫 기능**이라 두 계층 다 구조적으로 준비돼 있지 않았다 — 이게 정확히
"ADR 수준 설계 변경"으로 분류된 이유다.

---

## Decision (제안 — 미확정)

### 제안 1 — 단일 공유 모듈로 한 번만 구현

`core/repetition_detector.py`(신규, dormant) — 문서 하나를 처리하는
동안 최근 등장한 candidate 텍스트(정규화된 형태)를 sliding window로
누적하고, "이 candidate가 최근 W개 안에서 이미 봤던 것과 (거의) 같은가"
를 판정하는 **하나의** stateful 클래스만 만든다. 두 소비처가 이걸
각자 다르게 재구현하지 않는다:

```python
class RepetitionTracker:
    def __init__(self, window: int = 80, similarity_threshold: float = 0.9):
        ...
    def observe(self, normalized_text: str) -> RepetitionSignal:
        """반복 여부·최근 등장 간격·누적 등장 횟수를 반환하고,
        내부 이력에 이번 candidate를 추가한다(순서 의존적 — 호출자가
        문서 순서대로 호출해야 함)."""
```

- 정규화: 페이지 번호처럼 매번 바뀌는 부분(예: "요한복음 주석 — 749")은
  숫자를 마스킹한 뒤 비교(`re.sub(r'\d+', '#', text)`) — 실측 근거인
  "2 Kings, Vol.13" 사례가 정확히 이 패턴(같은 러닝헤더 + 다른 페이지
  번호)이었다.
- window=80, threshold는 실측(median 25, majority 9~56)에 여유를 둔
  값 — 최종 수치는 이 ADR이 아니라 실제 구현 후 재보정.

### 제안 2 — 디노이즈 계층 연결 (`noise_classifier.py`)

`classify()`가 `RepetitionTracker`를 (문서 단위로 생성된) 선택적
인자로 받도록 additive 확장. 신호가 있으면 `HEADER_FOOTER` 판정에
반영, 없으면(기존 호출부) 지금의 단일 청크 휴리스틱만 사용 — 기존
동작 100% 보존.

### 제안 3 — 청킹 고수준 결과 연결 (`semantic_boundary_detector.py`)

6번째(임베딩) 다음 **7번째 feature** `PageHeaderArtifactFeature`로
추가. 다른 feature와 동일하게 `FeatureRegistry`에 등록하되, 이 feature만
유일하게 매 후보마다 `RepetitionTracker.observe()`를 호출해 내부
상태를 갱신한다 — "반복 감지됨 = boundary 아님"(음의 가중치, 
`tiny_fragment`의 -60.0과 같은 계열)으로 잘못된 semantic flush를 억제.

### 제안 4 — 실측 검증 순서 (ADR-007/008 원칙 계승)

이 ADR은 구현을 승인하지 않는다. 승인 시 순서:
1. `RepetitionTracker` 단위 테스트("2 Kings, Vol.13" 실제 반복 패턴
   재현) — production 무접촉.
2. `noise_classifier.py` 연결 + Profile B 문서 전체 재분류, HEADER_FOOTER
   판정 건수 before/after 실측.
3. `semantic_boundary_detector.py` 연결 + D5 3축(특히 Axis 3) 재측정
   — Level 3(ADR-008 제안 2, 완료)와의 상호작용도 함께 확인(러닝헤더가
   줄어들면 Level 3가 처리할 "진짜 unsplittable" 대상만 남아야 함).
4. 두 결과를 갖고 HQ가 프로덕션 반영 여부 판단.

---

## Consequences

### 이 ADR로 확정되는 것
- 없음 — 설계 제안과 두 미해결 이슈의 통합 근거만 문서화.

### 이 ADR로 확정되지 않는 것
- `RepetitionTracker`의 window/threshold 최종 수치.
- `noise_classifier.py`/`semantic_boundary_detector.py` 실제 연결 착수 여부·일정.
- 정규화 규칙(숫자 마스킹 외 추가 규칙 필요 여부 — 예: 쪽수가 로마
  숫자인 서문 페이지 등)은 실제 Profile B corpus 재검토 필요.

### 리스크
- Sliding window 상태를 잘못 관리하면(예: 여러 문서 처리 시 tracker
  재사용) 문서 간 오염 위험 — 반드시 문서 1개당 tracker 1개 인스턴스,
  재사용 금지를 구현 시 명시적으로 강제해야 한다.
- 유사도 임계값이 너무 낮으면 정상적으로 반복되는 표현(예: 설교/주석
  특유의 후렴구, "이는 ~을 의미한다" 같은 반복 문형)을 헤더로 오판할
  위험 — Phase 실측에서 반드시 오탐(false positive) 케이스를 별도로
  확인해야 한다.

---

## Next Steps (HQ 승인 대기)

1. `RepetitionTracker` 구현 + 단위 테스트 (제안 4 §1) — 승인 시 착수.
2. 승인 시 노출된 실측 결과를 갖고 제안 2/3 각각 별도 승인 요청.
