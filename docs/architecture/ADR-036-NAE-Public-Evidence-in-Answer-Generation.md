---
title: "ADR-036: NAE Public-Theology Evidence in Answer Generation (Chat/Research)"
category: architecture
based_on:
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md
  - docs/architecture/ADR-013-NAE-Vector-Store.md
  - docs/architecture/ADR-024-NAE-Production-Retrieval-Bridge.md
  - docs/architecture/ADR-028-NAE-Smith-Reference-Layer.md
  - docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md
  - docs/NAE_EUAT_001_RESULT.md
  - docs/NAE_EUAT_001_APPENDIX_A_CORPUS_INDEX_OBSERVATION.md
  - docs/NAE_EUAT_001_FU003_BUILD_REPORT.md
scope_modified: docs/architecture/ only — 코드 미수정 (본 ADR은 설계 결정 문서, 구현은 별도 작업 명령 필요)
---

# ADR-036: NAE Public-Theology Evidence in Answer Generation (Chat/Research)

| 항목 | 내용 |
|---|---|
| Status | **Proposed** — Approved 아님. 기존 Approved ADR(특히 ADR-024)을 변경·대체하지 않는다 |
| 작성 | CUE, 2026-09-29 (EUAT-001 후속 FU-001) |
| 결정권자 | Rev. Bang / HQ = Final Authority |
| 번호 | 036 (ADR-035는 `claude/adr-035-pastoral-library-automation`·`feat/peb-v0.1`에 이미 존재해 회피) |
| 승격 조건 | Evidence Before Promotion 4조건: 구현 완료 / 회귀 통과 / C1 독립 리뷰 / 사용자 승인 — 전부 충족 전까지 Proposed |
| 변경 없음(범위) | Retrieval Engine 랭킹, `nae_tsu_v1` 인덱스, ADR-024 §A/§F/§G/§H, corpus 등록·인덱싱 |

## 1. Context — 무엇이 문제인가

EUAT-001(2026-09-29, 실제 앱 UI)의 핵심 발견:

1. **채팅 답변은 내 서재 자료만 근거로 삼는다.** 채팅 출처 25건에 Dagg/Hiscox/Fuller가 0건이었고, 답변 경로(`ui/pages/chat.py`)는 `core.retrieval.QueryProcessor`와 Smith 사전(ADR-028)만 쓴다. 연구 탭도 같은 경로다(FU-006 확인).
2. **NAE 내장 코퍼스(`nae_tsu_v1`)는 별도 "내서재 공개 자료(Beta)" 패널에 근거 카드로만 나온다.** 그 근거로 답변을 생성하는 경로가 없다. 인덱스에는 Dagg 3,279·Hiscox 612건이 있고 검색도 동작하지만(FU-002 후), 사용자가 "내 서재/내장 자료를 근거로 답하고 출처를 밝혀 달라"고 물으면 답변에는 반영되지 않는다.
3. 이 분리는 **의도된 설계**다. ADR-024 §B가 그렇게 정했고, 그것을 코드로 고정하는 테스트가 있다(`tests/test_nae_f6_chat_wiring.py::TestNoMergeIntoGeneration` — `chat.generate_answer`와 `_handle_user_message`가 `bridge_query`/`NAE.retrieval_adapter`를 참조하면 실패).

따라서 EUAT-001의 "채팅이 TSU에 닿지 않음"은 **버그가 아니라 Approved ADR과 제품 기대 사이의 간극**이며, 코드 수정 전에 ADR 결정이 필요하다(Architecture Freeze Rule).

### 1.1 ADR-024 §B가 실제로 금지하는 것

원문 근거: "DBMA 결과(BM25+theological+vector)와 NAE 결과(vector-only)를 **같은 순위 리스트에 병합하지 않는다.** 서로 다른 스코어링 기준으로 만들어진 점수를 하나의 랭킹에 섞으면 랭킹 품질이 왜곡된다." 대신 "NAE corpus를 별도 결과 섹션으로 분리 표시"한다. 그리고 "이후 NAE에도 BM25/theological scoring을 구현해 진짜 hybrid 통합을 할지는 **별도 Architecture Decision(후속 ADR 대상)**으로 남긴다."

- 금지의 직접 대상은 **서로 다른 척도의 점수를 하나의 랭킹으로 섞는 것**이다.
- **생성 단계에서 근거를 어떻게 다룰지**는 §B가 명시적으로 다루지 않는다. 다만 `TestNoMergeIntoGeneration`이 "병합 금지"를 생성 경로에까지 확장해 코드로 고정해 두었다(테스트 docstring: "DBMA 결과와 NAE 결과를 같은 답변/랭킹에 병합하지 않는다").
- §H는 UI에서 NAE 결과에 출처 배지를 붙일 것, DBMA/NAE 중복 제거는 "의도적으로 없음"을 정한다.
- 이 ADR-036이 §B가 예고한 "후속 ADR"에 해당한다.

### 1.2 관련 선례와 제약

| 항목 | 내용 | 시사점 |
|---|---|---|
| ADR-028 (Accepted) | Smith 사전은 같은 LLM 컨텍스트에 **별도 `<reference>` 블록 + 계층 지시문**으로 주입한다. 순위 병합 없음 | "별도 블록으로 생성 컨텍스트에 넣는 것"은 이미 승인된 패턴이다. 단 Smith는 보조 자료이고 NAE 공개 자료는 1차 신학 문헌이라 역할이 다르다 |
| ADR-013 / 2026-08-16 격리 사고 | NAE는 `core/`와 분리된 서브시스템, 벡터 저장소도 별개(`nae_qdrant` 7333). Dagg 1건이 DBMA 등록부로 오염된 사고 이력 | 어떤 방안이든 **저장 계층 격리**(NAE 근거를 DBMA 등록부·인덱스·6333에 쓰지 않음)를 지켜야 한다 |
| ADR-001 | Retrieval Engine 단일 정본 | 랭킹·검색 엔진 변경은 범위 밖 |
| Grounded Synthesis AD-02 (HQ 승인, Option D) | Personal(1차) / Default(보조) 역할 정책은 **랭킹 병합이 아니라 역할 보존 병합**(post-processing role-aware merge), Personal rank 1 강제 금지 | 다만 그 "Default corpus"는 DBMA의 기본 코퍼스이며 NAE 공개 자료(`nae_tsu_v1`)가 아니다. 용어를 혼동하지 않는다. 역할 보존 병합 원칙은 참고 가능 |
| `core/evidence_unit.py`, `evidence_pool.py`, `evidence_adapters/` | 코퍼스 유형(`CorpusType`)을 보존하는 증거 모델이 main에 이미 있음 | 방안 C를 구현할 경우의 기반이 될 수 있음(이 ADR은 채택하지 않음) |
| ADR-030 Amendment A §6 | `historical_witness`(Fuller) 자료가 인용될 때 고정 KR/EN 고지 필수 | 어떤 방안이든 NAE 근거를 인용하는 답변 영역에 고지가 있어야 한다. FU-003이 소스별 고지로 정리함 |
| 코드 기준선 | 시험 앱은 `feat/peb-v0.1`이고 `main`과 분기됨(FU-007). 위 사실은 두 브랜치에서 같음을 확인(`chat.py`의 NAE/Smith/보류 참조 10건씩, 브리지 참조 0건) | 구현 착수 전에 기준 브랜치를 정해야 한다 |

## 2. 문제 진술과 비목표

**문제**: 사용자가 내장 신학 자료(Dagg, Hiscox)를 근거로 한 **출처 있는 답변**을 받을 방법이 UI에 없다. 근거 카드는 있지만 종합·답변이 없다.

**비목표**
- NAE에 BM25/신학 점수를 구현해 진짜 hybrid 랭킹을 만드는 것(§B가 별도 ADR로 남긴 더 큰 결정, 이번 범위 아님).
- Fuller·1689 인덱싱 범위 결정(FU-004), 인덱스 재구축, 중복 제거.
- `modules.nae_pd.enabled` 외의 새 스위치 추가(ADR-024 §F의 "스위치는 하나" 원칙 유지).

## 3. 선택지

### 방안 A — 현행 유지 + 안내 강화
채팅은 내 서재 기반 답변, 공개 패널은 근거 카드만. UI에 "이 답변은 내 서재 자료 기반이며 공개 신학 자료는 아래 별도 섹션에서 근거로만 제공됩니다"와 검색 범위 표시를 추가.

### 방안 B — 별도 "공개 자료 근거 답변" (권고)
공개 패널에서 사용자가 **명시적으로** 요청할 때(버튼), 그 패널이 이미 가져온 문단 근거(`bridge_query_paragraphs`)만으로 **두 번째 생성 호출**을 수행해 별도 섹션에 답변을 표시한다. 내 서재 답변과 **병합하지 않고**, 근거 목록·인용·고지·경고를 각각 따로 둔다.

- 근거 입력: 패널의 문단 근거 상위 N건(N은 구현 시 결정). 0건이거나 검색 실패(FU-003의 `last_retrieval_failure`)면 생성하지 않고 보류 문구를 표시.
- 프롬프트: 기존 근거 강제 지시문과 근거별 "출처:" 라벨 규칙을 재사용(신규 정책 없음).
- 표시: NAE 배지(ADR-024 §H), 소스별 고지(ADR-030 Amendment A §6, FU-003), 인용 검증 경고(FU-003), **검색 범위 문구**("검색 범위: Dagg, Hiscox — Fuller·1689는 인덱스에 없음").
- 구현 위치: 신규 함수를 NAE 계층(예: `NAE/…`)에 둔다. `chat.generate_answer`와 `_handle_user_message`는 브리지를 참조하지 않으므로 `TestNoMergeIntoGeneration`은 그대로 유효.
- 스위치: `modules.nae_pd.enabled` 하나. 새 플래그 없음. 롤백 = 그 값을 `false`.

### 방안 C — 단일 답변에 병합 (역할 표시 블록)
NAE 근거를 채팅 답변의 LLM 컨텍스트에 `<public_theology>` 같은 **역할 표시 블록**으로 함께 넣어 하나의 답변이 내 서재와 공개 자료를 함께 인용. 점수 병합은 하지 않는다(AD-02 Option D식 역할 보존).

## 4. 평가

| 기준 | A | B | C |
|---|---|---|---|
| ADR-024 §B(순위 병합 금지) | 충족 | 충족 (병합 없음, 별도 섹션·별도 답변) | 점수 병합은 없으나 **같은 답변에 결합** — §B의 "별도 섹션 분리" 취지와 `TestNoMergeIntoGeneration`에 저촉, **ADR-024 Amendment 필요** |
| ADR-024 §H(격리·배지) | 충족 | 충족 | 배지·출처 구분을 답변 안에서 지켜야 함(난이도 높음) |
| 저장 계층 격리(ADR-013, 격리 사고) | 충족 | 충족 (저장 변경 없음) | 충족 가능하나 컨텍스트 조립부(`core/`)가 NAE 근거를 받게 됨 |
| EUAT-01·02 (Dagg/Hiscox) | 해결 안 됨 | **해결**(근거 있는 답변 + 인용 검증) | 해결 |
| EUAT-03·04 (Fuller·1689) | 해결 안 됨 | 인덱스 부재로 여전히 유보 — 단 **범위 문구로 이유를 밝힘** | 동일 |
| EUAT-05 (복수 자료 종합) | 해결 안 됨 | **부분**: 두 답변이 나란히 놓일 뿐 종합은 사용자 몫 | **해결 가능**(단일 종합) — 단 신뢰 검증 난이도 최고 |
| 신뢰성(FU-003 검증기 적용) | — | 각 답변에 독립 적용 | 한 답변 안에서 출처 종류가 섞여 라벨 대조가 복잡 |
| 구현 규모·위험 | 최소 | 중간(신규 함수+UI 버튼, `core/` 무변경 가능) | 큼(`core/` 컨텍스트 조립·프롬프트 계층·테스트 가드 변경) |
| 되돌리기 | 쉬움 | 쉬움(모듈 스위치) | 어려움(프롬프트·가드 테스트 변경) |
| 사용자 이해 | 명확하나 답을 못 받음 | 두 답변의 관계 설명 필요 | 하나의 답변이라 단순 |

## 5. 권고: 방안 B (1단계), C는 근거 확보 후 별도 ADR

**권고 근거**
1. Approved ADR-024를 **바꾸지 않고** 이 간극을 메운다(별도 섹션 유지, 병합 없음, 스위치 하나).
2. 이미 있는 부품을 재사용한다: 문단 근거, 근거 강제 지시문, 소스별 고지, 인용 검증기, 실패 사유 신호(FU-003·FU-005).
3. EUAT의 직접 실패 2건(EUAT-01·02)을 해결하고, 미해결 2건(EUAT-03·04)은 원인(인덱스 부재)을 사용자에게 정직하게 밝힌다.
4. 방안 C가 필요한지는 B를 실제로 써 본 증거(사용자가 두 답변을 어떻게 쓰는지, 종합 요구의 크기)를 본 뒤 판단하는 것이 "근거 없이 구조를 바꾸지 않는다"는 프로젝트 원칙과 맞다. C는 ADR-024 Amendment와 `TestNoMergeIntoGeneration` 변경이 필요한 더 큰 결정이다.
5. 방안 A는 사용자가 원하는 답을 여전히 못 주므로 B를 채택하지 않을 경우의 대안으로만 둔다.

**B의 알려진 한계**: 종합(EUAT-05)은 해결하지 못한다. 두 답변이 나란히 있을 뿐이다. Fuller·1689는 인덱싱 결정(FU-004) 없이는 답변에 포함되지 않는다.

## 6. 수용 기준 (B 채택 시)

| ID | 기준 |
|---|---|
| AC-1 | EUAT-01·02를 UI에서 재시험: 공개 자료 근거 답변에 Dagg/Hiscox 인용이 있고 인용 검증 경고가 없거나 정당하게 표시됨 |
| AC-2 | EUAT-03·04: 답변 대신 보류 문구 + 검색 범위 문구(Fuller 0건, 1689 미포함 명시). 일반 지식으로 채우지 않음 |
| AC-3 | 근거 0건·검색 실패(timeout/error) 시 생성 호출이 일어나지 않음. 검색 실패를 "자료 없음"으로 표시하지 않음 |
| AC-4 | `TestNoMergeIntoGeneration` 두 테스트 무변경 통과. NAE 근거가 내 서재 답변의 출처 목록·컨텍스트에 섞이지 않음 |
| AC-5 | NAE 답변 영역에 소스별 고지와 NAE 배지 표시. Dagg/Hiscox에 Fuller 고지가 붙지 않음 |
| AC-6 | 저장 계층 무변경: `dbma_qdrant`(6333)·DBMA 등록부 접근 코드 없음(코드 리뷰), `nae_tsu_v1` 쓰기 없음 |
| AC-7 | `modules.nae_pd.enabled=false`에서 새 UI·생성 호출이 전혀 나타나지 않음(no-op) |
| AC-8 | 신규 스위치 없음. 전체 회귀 통과 |

## 7. 위험과 완화

| 위험 | 완화 |
|---|---|
| 생성 지연·GPU 경합(FU-005: 두 대형 모델 상호 evict) | 명시적 버튼(자동 실행 아님), 진행 표시, 재시도 안내. 경합 자체는 별도 운영 과제 |
| 인용이 붙은 환각 | FU-003 검증기 적용, 근거 강제 지시문, 0건이면 미생성 |
| 두 답변 간 혼동 | 섹션 제목·배지·범위 문구, 서로 다른 출처 목록 |
| 인덱스 범위 오해(Fuller 0, 1689 없음, CHANGED 17 보류) | 검색 범위 문구를 항상 표시 |
| 코드 기준선 분기(FU-007) | 구현 착수 전 기준 브랜치 결정 |
| 3초 하드 타임아웃(ADR-024 §G)이 콜드 로드에서 빈 결과 유발 | FU-003의 실패 사유 신호로 구분 표시. 타임아웃 값 변경은 이 ADR 범위 밖 |

## 8. 결정 요청

1. **방향**: A / B / C 중 선택(권고 B).
2. **B 채택 시 트리거**: 명시적 버튼(권고) vs 공개 검색 결과와 함께 자동 생성.
3. **ADR-024 문구**: B는 §B를 변경하지 않는다. 다만 `TestNoMergeIntoGeneration`의 docstring("같은 답변/랭킹에 병합하지 않는다")이 B와 일치함을 ADR-024에 각주로 남길지는 Approved 승격 후 별도 판단.
4. **구현 기준 브랜치**: FU-007 결과에 따름.

## 9. 다음 단계

- 사용자 결정 → C1 Review 요청(새 ADR 작성은 C1 Review 요청 시점에 해당) → 구현 Task Order(방안 확정 후) → 구현·회귀 → C1 재검토 → 사용자 승인으로 Approved 승격.
- 이 문서의 수치·경로 근거는 CUE가 직접 확인한 값이다(EUAT-001 보고서, 부록 A, FU-003 Build Report, 코드 열람).
