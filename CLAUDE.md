# CLAUDE.md

## DBMA 프로젝트 개요

DBMA는 신학 문서 전용 RAG 시스템이다.
Python 기반으로 다양한 문서 형식을 처리하고, 추출, 정제, 청킹, 임베딩, 검색, 생성, 평가를 하나의 흐름으로 연결한다.
핵심 목표는 결과 정밀도, 추적 가능성, 유지보수성, 그리고 반복 개선이다.

DBMA의 공식 실행 진입점은 `dbma_ui.py`(→ `ui/app.py`)이며, Streamlit UI와 전체 처리
흐름을 오케스트레이션한다. 과거 legacy application entry였던 `dbma.py`와
`core/search.py`, `core/ingest.py`, `core/qdrant_init.py`는 `core/retrieval.py::RetrievalEngine`을
사용하지 않는 별도의 레거시 RAG 경로였으며, 2026-07-17 커밋 `ce6b05a`로
`archive/legacy/`로 이동(격리)되어 현재 프로젝트 루트에는 존재하지 않는다
(ADR-001, ADR-003, `docs/architecture/DBMA-Legacy-Code-Removal-Plan-v1.md` 참고).
프로젝트 루트는 `~/DBMA` 이다.

---

## 프로젝트 원칙

- DBMA는 신학 문서용 RAG 시스템이다.
- 결과 정밀도와 안정성을 우선한다.
- 작은 단위로 수정하고, 바로 검증한다.
- 작업은 반드시 추적 가능해야 한다.
- 로그는 읽기 쉽게 남긴다.
- md 파일을 사용해 상태와 과정을 문서화한다.
- `dbma_ui.py`(→ `ui/app.py`)를 시작점으로 연결 구조를 이해한다.
- 필요한 경우 함수 단위로 블록 다이어그램을 만든다.

---

## 기술 스택

- 언어: Python
- RAG 스택: LlamaIndex
- 기본 임베딩 모델: `bge-m3:latest`
- 기본 chunk size: `1200`
- 기본 overlap: `200`
- UI: Streamlit
- 개발 방식: 터미널 중심
- 문서 관리: Markdown 중심
- 목표 환경: MacBook Pro Max M5, 128 GB RAM

---

## 디렉터리 기준

기준 경로:
- 프로젝트 루트: `~/DBMA`
- 핵심 파일: `/Users/David/DBMA/dbma_ui.py` (→ `/Users/David/DBMA/ui/app.py`)

주요 모듈:
- `dbma_ui.py`: 공식 진입점 (thin launcher → `ui/app.py`)
- `dbma.py`: 제거됨 — `archive/legacy/dbma.py`로 이동 (2026-07-17, 커밋 `ce6b05a`,
  `docs/architecture/DBMA-Legacy-Code-Removal-Plan-v1.md` 참고)
- `core/`: 추출, 처리, 파일, 청킹, 유틸리티
- `ui/`: 탭 기반 인터페이스
- `tests/`: 테스트 코드
- `docs/`: 문서화
- `loops/`: 루프 엔지니어링 관련 산출물
- `scripts/`: 실행 및 평가 스크립트

---

## 작업 방식

1. 문제를 짧게 정의한다.
2. 관련 파일과 함수만 확인한다.
3. 필요한 경우 먼저 코드를 읽는다.
4. 수정은 최소 범위로 한다.
5. 실행 후 검증한다.
6. 결과를 md 파일에 기록한다.
7. 다음 반복에서 개선한다.

---

## 코드 구조 원칙

- 한 파일은 한 책임을 가진다.
- 한 함수는 한 역할을 가진다.
- 관련 없는 파일은 건드리지 않는다.
- 복사본 파일은 기준으로 쓰지 않는다.
- 임시 파일과 백업 파일은 혼동하지 않는다.
- 새 기능은 기존 흐름을 깨지 않게 넣는다.

---

## 파이프라인 순서

DBMA의 기본 흐름은 아래와 같다.

```text
원본 문서
→ 추출
→ 정제
→ 청킹
→ 저장
→ 임베딩
→ 검색
→ 생성
→ 평가
```

이 순서는 문서 처리, RAG, 평가 루프 전반의 기준이다.

---

## 문서화 규칙

- 진행 상태는 md 파일로 남긴다.
- TODO 목록에는 체크포인트와 진행률을 포함한다.
- 상태 기록은 짧고 읽기 쉽게 쓴다.
- 필요하면 파이프라인 문서와 설계 문서를 분리한다.
- 함수 연결 구조는 블록 다이어그램으로 정리한다.
- `dbma_ui.py`(→ `ui/app.py`)를 시작점으로 전체 연결을 문서화한다.

추천 문서 예시:
- `docs/ARCHITECTURE.md`
- `docs/PIPELINE.md`
- `docs/STATE.md`
- `docs/TODO.md`
- `docs/DBMA_MAP.md`

---

## 루프 엔지니어링 규칙

- 목표를 정하고 실행한다.
- 결과를 보고 수정한다.
- 다시 실행하고 비교한다.
- 이 과정을 안정될 때까지 반복한다.
- 실패는 기록하고 다음 시도에 반영한다.
- 진행률은 퍼센트로 표시한다.
- 가능한 경우 상태를 시각적으로 남긴다.

권장 항목:
- 목표
- 현재 상태
- 수정 내용
- 검증 결과
- 다음 조치
- 진행률

---

## 로그 규칙

- 로그는 읽기 쉬워야 한다.
- 처리 단계별로 핵심 로그를 남긴다.
- 원인과 결과를 구분해서 기록한다.
- 너무 길게 쓰지 않는다.
- 실패 시 재현 정보도 남긴다.

예시:
```text
[parse] started
[parse] success
[chunk] size=1200 overlap=200
[rag] failed: missing index
```

---

## UI 규칙

- UI는 탭 구조를 유지한다.
- Mac 친화적인 흐름을 우선한다.
- 처리 중 상태를 분명히 보여준다.
- 필요하면 다른 탭을 비활성화한다.
- 사용자가 현재 상태를 바로 알 수 있어야 한다.

---

## RAG 규칙

- LlamaIndex 기반으로 관리한다.
- 기본 임베딩은 `bge-m3:latest`를 사용한다.
- 기본 chunk size는 `1200`이다.
- 기본 overlap은 `200`이다.
- 문서별 특성에 따라 청킹은 조정 가능해야 한다.
- 헬라어와 히브리어 처리 가능성을 고려한다.
- 검색과 생성은 분리해서 다룬다.

---

## 테스트 규칙

- 변경 후 반드시 테스트한다.
- 테스트는 작은 단위부터 시작한다.
- 실패한 테스트는 바로 기록한다.
- 핵심 기능에는 회귀 방지 테스트를 붙인다.
- 가능하면 자동 테스트를 만든다.

---

## Cline 사용 규칙

- Cline은 보조 도구로만 사용한다.
- 한 번에 하나의 파일 또는 하나의 함수만 수정하게 한다.
- 복잡한 코드는 Claude 4.5 Sonnet 기준으로 다룬다.
- 불필요한 탐색과 넓은 수정은 피한다.
- 요청은 구체적으로 쓴다.
- 결과는 바로 검증 가능해야 한다.
- 디버깅은 가능하면 직접 확인한다.

---

## Cline 최적 프롬프트

```text
너는 DBMA 프로젝트의 코드 보조자다.
프로젝트 루트는 /Users/David/DBMA 이다.

작업 원칙:
- 한 번에 하나의 파일 또는 하나의 함수만 다룬다.
- 관련 없는 파일은 수정하지 않는다.
- 기존 구조를 최대한 유지한다.
- 추측하지 말고, 필요한 정보가 부족하면 먼저 질문한다.
- 변경 전과 변경 후를 짧게 요약한다.
- 복사본 파일이나 백업 파일을 기준으로 삼지 않는다.

현재 작업:
- 대상 파일: {파일 경로}
- 대상 함수: {함수명}
- 목표: {구체적 목표}

출력 형식:
1. 문제 요약
2. 수정 계획
3. 수정 코드
4. 변경 이유
5. 검증 단계
```

---

## 파일 관리 규칙

- 복사본 파일은 참고용일 뿐 기준이 아니다.
- 최신 본문을 기준으로 판단한다.
- 이름이 비슷한 임시 파일은 정리 대상이다.
- 프로젝트 기준 경로는 항상 `~/DBMA`로 본다.

---

## 상태 관리 규칙

- 현재 진행 상황을 항상 파악할 수 있어야 한다.
- TODO는 완료, 진행 중, 대기 중으로 나눈다.
- 가능하면 진행률을 퍼센트로 표시한다.
- 큰 작업은 체크포인트로 나눈다.

예시:
```md
- [x] 구조 확인
- [ ] 파싱 안정화
- [ ] md 산출물 복구
- [ ] UI 탭 개선
- [ ] RAG 개선
진행률: 35%
```

---

## 금지 사항

- 근거 없는 구조 변경 금지
- 한 번에 여러 큰 파일 무리하게 수정 금지
- 복사본 파일을 기준으로 삼는 것 금지
- 불필요하게 넓은 리팩터링 금지
- 설명보다 실행 가능한 결과를 우선

---

## 최종 기준

DBMA의 목적은 단순히 돌아가는 코드가 아니라,
신학 문서를 안정적으로 다루고,
문서 흐름을 추적 가능하게 유지하며,
반복 개선이 가능한 시스템을 만드는 것이다.
---

## 언어 규칙

- 모든 답변과 설명은 **한국어(한글)**로 작성한다.
- 코드, 변수명, 함수명은 영어 그대로 유지한다.
- 오류 메시지 인용 시에는 원문 유지 후 한글로 설명을 추가한다.

---

## CUE Operating Policy v1.0 (NAE/DBMA Development Workflow, 2026-08-03 채택)

CUE(이 저장소에서 작업하는 에이전트)는 본 프로젝트의 주 개발 엔진
(Primary Implementation Agent)이다. C1은 독립 검토(Audit) 담당이며
구현 작업은 하지 않는다.

### 기본 순서

요구사항 분석 → Architecture 확인 → ADR 확인 → 구현 → Test 작성 →
Regression Test → Build Report 작성 → **Git Commit** → **Git Push**.

### Git 자동화 범위(영구 정책)

- **Git Commit**: 완료 조건(구현 완료·Test PASS·Regression PASS·
  Architecture Rule PASS·ADR Conflict 없음·Build Report 작성)을
  만족하면 **사용자 승인 없이 자동 수행**한다. "커밋할까요?"를 묻지
  않는다.
- **Git Push**: 완료 조건을 만족하면 **사용자 승인 없이 자동
  수행**한다(대상: `origin` 현재 작업 브랜치). "Push할까요?"를 묻지
  않는다. **Force Push와 History Rewrite는 이 자동화에서 항상
  제외**된다 — 별도 승인 없이는 수행하지 않는다.
- Commit 메시지는 Conventional Commit(`feat:`/`fix:`/`refactor:`/
  `test:`/`docs:`/`chore:`)을 사용한다.

### 반드시 지켜야 하는 사항(명령 없이는 절대 변경 금지)

RAW 데이터, Retrieval Engine, Embedding Engine, TSU Pipeline, 기존
ADR, Production Registry. Architecture를 우회하는 구현을 금지한다.

### Architecture Freeze Rule

ADR가 Approved 상태가 되면, 해당 ADR는 이후 어떤 작업 명령에서도
**자동으로 변경하거나 우회해서는 안 된다** — 작업 명령서(사용자가
채팅으로 준 지시 포함)가 Approved ADR의 규칙과 다른 값·형식·정책을
암묵적으로 담고 있어도, CUE는 그것을 그대로 구현하지 않는다. 변경이
필요한 경우 반드시 새로운 ADR Amendment 또는 ADR Revision 문서를
먼저 작성하고 승인받은 후에만 구현한다.

작업 명령서와 Approved ADR/기존 승인 설계 문서가 충돌하는 것을
발견하면: 구현을 중단하고 충돌 내용을 구체적으로 제시한 뒤 사용자
확인을 받는다(예: NAE-ID-GOVERNANCE-IMPLEMENTATION-001에서
canonical_id 형식이 ADR-017 lowercase snake_case와 명령서의
UPPER_SNAKE_CASE 예시가 충돌해 AskUserQuestion으로 확인 후 ADR-017
기준으로 구현한 사례, 2026-08-03).

### C1 Review 요청 시점

새 ADR 작성, 새 Architecture Layer 추가, Metadata Model 변경,
Validator 추가, Migration 정책 변경, ID Governance 변경, Production
승격 직전, TSU Pipeline 진입 직전 — 이 경우에만 C1 Review를 요청한다.
사소한 버그 수정·테스트 보강은 C1 Review 없이 진행한다. C1의 승인
없이 구현을 중단하지 않는다.

### 예외 — 아래는 이 자동화로 수행하지 않고 항상 승인을 요청한다

`main`/`master` 직접 병합, Force Push, Git History 변경, Release Tag
생성, GitHub Release 생성, ADR 폐기, Retrieval Engine 변경, RAW 대량
수정, Corpus 전체 Migration, Production Registry 대량 변경.

### 판단 원칙

명령 범위 안에서 필요한 세부 구현은 스스로 결정하고, Architecture/ADR을
위반하지 않는 범위에서는 사용자에게 반복 확인하지 않는다. 불확실한
사항은 문서화하고 합리적인 기본값을 선택해 진행한다. 항상 최소
출력을 사용하고, 최종 보고는 핵심 결과만 작성한다(형식:
`STATUS/Changed Files/Tests/Regression/Git(Commit/Push)/Next`).
