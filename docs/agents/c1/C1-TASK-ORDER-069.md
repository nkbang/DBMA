# C1 Task Order 069 — SermonArtifact 설계 검토 (신규 Architecture Layer, P1 착수 전)

- 발주자: CUE
- 일자: 2026-09-21
- 유형: **C1 Review — 설계 검토 (Pre-Implementation, 신규 Architecture Layer)**
- 근거: `docs/DBMA_SERMON_ARTIFACT_PIPELINE_DESIGN_v1.md` §8·§10 — "새
  Architecture Layer 추가"는 CLAUDE.md "C1 Review 요청 시점"에 명시적으로
  해당. **HQ가 D5(설계 방향)·D6(범위)·D8(P1 직후 P2) 승인 완료
  (2026-09-21)** — 남은 것은 D7(C1 Review)뿐이며, 이 문서가 그 요청이다.
- 구현 없음, 코드 변경 없음 — 설계 문서만 검토

---

## 배경

DBMA에 "설교 생성 후 저장·재열람" 기능이 없다는 구조적 공백을 메우기 위해
`SermonArtifact`라는 신규 영속 계층을 설계했다(`data/sermon_artifacts/
{sermon_id}.json` + `index.jsonl`). 이 계층 위에 예화 검색·강단 전달
모드·재활용·시리즈 뷰가 파생물로 얹힌다.

**리뷰 대상 문서**: `docs/DBMA_SERMON_ARTIFACT_PIPELINE_DESIGN_v1.md`
(전체, 357행) — 특히 §3(계층 구조), §4(데이터 설계), §5.1(예화 검색
경로), §8(아키텍처 준수 표).

---

## 질의 사항

### RQ-1. ADR-001(One Retrieval Engine) 준수 여부

§5.1의 예화 검색 흐름(174행 부근):

```
설교 대지 텍스트
  → QueryProcessor.process(대지 + 본문, k=30)     # ADR-001 준수, 기존 경로
  → 사후 필터: TSU.document_id → registry.doc_type == "설교"
  → 상위 3건을 [출처·저자·신뢰도]와 함께 제시
```

`core/retrieval.py::QueryProcessor.process()`의 실제 시그니처와 반환
타입(`RankedCandidate` 리스트로 추정)을 확인하고, 이 흐름이:
1. 새 검색 경로/병렬 랭킹 로직을 만들지 않고 기존 `process()`를 그대로
   통과하는가?
2. "doc_type == 설교" 필터가 검색 자체가 아니라 사후 필터(post-filter)로
   구현 가능한 지점(반환된 candidate 리스트에 대한 Python 필터)에서
   적용되는 구조인가, 아니면 실제로는 `core/retrieval.py` 내부 수정이
   필요한 구조인가?

### RQ-2. Metadata Model 무변경 주장 검증

§8(아키텍처 준수 표)은 "TSU/registry 스키마 무변경, artifact는 별도
저장소"라고 주장한다. 실제로 §4의 SermonArtifact 스키마
(`candidate_tsu_ids`, `evidence.retrieval`, `doctrine_report`,
`groundedness` 등)가 `core/tsu_builder.py`나
`core/identity_registry.py::register_document()`의 기존 필드 구조를
전혀 건드리지 않는 별도 저장소로 구현 가능한지 확인하라. 특히
`doc_type == "설교"` 필터(RQ-1)가 registry 조인만으로 가능한지, 아니면
TSU record에 없는 필드를 참조하는지 실제 `core/tsu_builder.py`의 TSU
record 스키마를 대조해 확인할 것.

### RQ-3. 기존 자산 재사용 주장 검증

§2 설계 원칙 3("기존 자산 재사용")이 나열한 함수들이 실제로 존재하고
설계가 주장하는 방식으로 재사용 가능한지 확인:

1. `core/multi_doc_splitter.py::SermonRecord`,
   `save_sermon_record(record, raw_dir)` — 실제 시그니처 확인. §5.6
   되먹임 설계(생성된 설교를 `save_sermon_record()`로 저장해 기존
   처리 파이프라인에 편입)가 이 함수의 실제 동작과 맞는가?
2. `core/evaluation/sermon_judge.py::judge_sermon_groundedness()` —
   실제로 `text_type` 파라미터를 받는가(§5.2가 이 파라미터만 바꿔
   재사용 가능하다고 주장)? 시그니처를 그대로 인용할 것.
3. `core/generation.py::SERMON_FORMATS`가 실제로 존재하고 설계가
   인용한 값과 일치하는가?

### RQ-4. 저장 위치·감사 추적 설계의 위험 요소

§4 "저장 위치: `data/sermon_artifacts/{sermon_id}.json` + 인덱스
`index.jsonl`"에 대해:

1. `.gitignore`에 `data/`가 포함돼 개인 설교 원고가 커밋되지 않는다는
   주장(140행)이 실제 `.gitignore` 설정과 일치하는가?
2. `identity_registry` 패턴을 차용한 `sermon_id` 식별자 생성 방식이
   기존 `core/identity_registry.py`의 document_id 생성 로직과
   충돌하거나 네임스페이스가 섞일 위험이 있는가(예: 같은 registry
   파일에 두 종류의 레코드가 섞여 들어갈 위험)?

---

## 확인 방법

`git checkout` 금지. `origin/dev/dbma-engine` 기준
`git show origin/dev/dbma-engine:<path>`로 확인. 설계 문서 자체는
같은 브랜치에 이미 병합돼 있다 — `git show
origin/dev/dbma-engine:docs/DBMA_SERMON_ARTIFACT_PIPELINE_DESIGN_v1.md`.

---

## 금지 사항

- 코드 작성/수정 금지 (설계 검토만)
- `git checkout` 금지
- RQ-1~4 외 범위 확장 금지(P2~P7 세부 구현 방식 검토는 이번 범위 아님 —
  P1 설계의 아키텍처 준수 여부만)

## 출력 형식

`docs/DBMA_SERMON_ARTIFACT_C1_REVIEW_RESULT_001.md`로 작성, 각 RQ마다
GREEN/YELLOW/RED + 근거 파일·행 인용. 종합 판정이 RED면 P1 착수를
보류하고 재설계, YELLOW면 CUE가 지적 사항을 반영한 설계 개정 후 재검토,
GREEN이면 CUE가 대조검증 후 즉시 P1 구현 착수.

```
STATUS:      C1 설계 검토 요청 (P1 SermonArtifact, 착수 전)
Changed:     이 문서 1건만
Next:        C1 RESULT_001 작성 → CUE 대조검증 → GREEN이면 P1 구현 착수,
             YELLOW/RED면 설계 개정
```
