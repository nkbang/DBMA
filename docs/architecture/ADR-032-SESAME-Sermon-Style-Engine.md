---
title: "ADR-032: SESAME — Sermon Style Extraction & Modeling Engine (초안 골격)"
category: architecture
status: Deferred — Post-Release Upgrade Item (SKELETON, 현재 Release 범위 제외)
based_on:
  - docs/architecture/DBMA-TLI-Architecture-Vision-v1.md (§4 Style Engine 슬롯)
  - docs/architecture/ADR-002-Document-Identity-and-Retrieval-Unit.md (내용/스타일 분리 패턴)
  - docs/architecture/ADR-009-SIL-Theology-Engine.md (설교 생성 통합 지점)
  - docs/architecture/ADR-012-DBMA-SEQ-Sermon-Evaluation-Quality.md (스타일 평가 계층)
  - docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md (설교 코퍼스 거버넌스)
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md (Retrieval 무변경)
  - docs/LOCAL_MODEL_SERMON_ALGORITHM_DESIGN.md (Algorithm 4 style transfer 스케치)
  - sermon_corpus/analyzer/ (frequency, keywords, book_themes, corpus_statistics — 읽기 전용 분석)
  - core/generation.py (SermonDraftService.style_examples — 읽기 전용 분석)
created: 2026-09-05
scope_modified: docs/architecture/ only — 코드·데이터·코퍼스·config 미수정
---

# ADR-032: SESAME — Sermon Style Extraction & Modeling Engine

| | |
|---|---|
| Status | **Deferred — Post-Release Upgrade Item (SKELETON)** |
| Date | 2026-09-05 |
| Deciders | Rev. Bang / HQ = Final Authority · CUE = Architecture/Design · C1 = Independent Review |
| Supersedes | — |
| Superseded by | — |
| Related | ADR-001 · ADR-002 · ADR-009 · ADR-012 · ADR-030 · DBMA-TLI-Architecture-Vision-v1 |

---

## 0. HQ Decision — Deferral (2026-09-05)

Rev. Bang / HQ 지시:

- **SESAME는 현재 Release 범위에 포함하지 않는다.** 진행 중인 Release 작업을
  우선 완료하고 배포한다.
- SESAME는 **Post-Release Upgrade Item**으로 보존한다.
- 향후 착수 시 CUE가 먼저 **기존 TLI Style Engine 슬롯, `sermon_corpus/analyzer`,
  ADR-002 / ADR-009 / ADR-012 / ADR-030과의 통합 관계를 재검토**한 후, 이
  ADR-032(본안 확장)부터 §11 Work Sequence를 단계적으로 진행한다.
- **현재 production mutation 및 SESAME 관련 선행 구현(스텁·스키마·데이터 포함)을
  금지한다.**

이 문서는 그 재검토·착수 시점까지 동결된 골격으로 보존된다. Proposed로도
승격하지 않으며, 다른 어떤 작업의 근거가 되지 않는다.

---

> **이 골격 문서 자체는 어떤 mutation도 수행하지 않는다.**
> Adoption mutation: Code 0 / Corpus 0 / TSU 0 / Embedding 0 / Qdrant 0 / Manifest 0 /
> Registry 0 / Config 0 / Migration 0. 구현 항목은 §11 Work Sequence에서 별도 Task Order로 분리된다.
> 이 문서는 **명명·범위·아키텍처 귀속·종속 계약**만 확정 후보로 제시하며, Proposed 상태에서는
> 다른 구현의 근거가 되지 않는다(Evidence Before Promotion Rule).

---

## 1. Context

HQ가 SESAME(Sermon Style Extraction & Modeling Engine)라는 작업을 설계했다. 목적은
설교자의 **전달 방식(how it is said)**을 추출·표현·모델링하고, 최종적으로 스타일 인식
설교 분석·생성을 가능하게 하는 전용 지능 계층을 두는 것이다.

핵심 구분:

```
TSU (Theological Semantic Unit)   →  "무엇을 말하는가" (신학적 내용·주장·근거)
SESAME (Sermon Style Engine)      →  "어떻게 말하는가" (구조·수사·문체·예화·적용 패턴)
```

저장소 조사 결과, SESAME가 요구하는 기능의 대부분은 이미 존재하는 계층에 물려야 하는
문제이며, 신규 top-level 파이프라인 신설은 System Charter의 One Pipeline 원칙과
충돌한다. 이미 존재하는 관련 자산:

| SESAME 요구 | 기존 자산 | 상태 |
|---|---|---|
| "how" 전용 계층 | **DBMA-TLI** 비전이 **"Style Engine"**을 Language Layer 슬롯으로 예약 | 보류(수요 시 Task Order) |
| 스타일 도메인 추출(구조·수사·어휘·예화) | `sermon_corpus/analyzer/` (frequency·keywords·book_themes·corpus_statistics) + collector + dashboard | 부분 구축 |
| 스타일 인식 설교 생성 | `core/generation.py::SermonDraftService.style_examples`("어투·문장 호흡만 참고") | 초보적 few-shot 가동 |
| style transfer 알고리즘 | `docs/LOCAL_MODEL_SERMON_ALGORITHM_DESIGN.md` Algorithm 4 | 설계 스케치, 미구현 |
| 스타일 평가(블라인드·유사도) | **DBMA-SEQ** (ADR-012, Proposed) | 평가 계층 소관 |
| 내용/스타일 분리 + provenance | **ADR-002** 관계 모델 · **ADR-021/030** raw 보존·admission ledger | 패턴·규율 확립 |
| 설교 코퍼스 수급 | **NAE** + **ADR-030** Sermon Corpus Governance | 거버넌스 존재 |
| SIL과의 관계 | **DBMA-SIL** (ADR-009) + `core/sermon/doctrine_filter.py` | 생성 엔진 존재 |

---

## 2. Decision — 이 ADR이 확정하는 것 (명명·범위·귀속만)

### 2.1 명명

- 프로젝트명: **SESAME (Sermon Style Extraction & Modeling Engine)**
- 이후 모든 DBMA/NAE 문서·코드에서 `SESAME`로 일관되게 참조한다.
- TSU 정식 명칭은 저장소 기준 **"Theological Semantic Unit"**이다(ADR-002 §3, ADR-009).
  SESAME Notice의 "Theological Structured Unit" 표기는 채택하지 않으며, 이 ADR로 교정한다.

### 2.2 범위

이 ADR은 다음만 확정 후보로 제시한다:

1. SESAME의 아키텍처 귀속(§4)
2. 기존 4개 ADR에 대한 종속 계약(§5)
3. OUT-OF-SCOPE 선언(§3)
4. style_profile 스키마의 **후보** 형태(§6) — 동결하지 않음
5. Work Sequence의 골격(§11)

이 ADR은 **어휘·임계값·최종 스키마·추출 알고리즘을 확정하지 않는다.** 그것들은
소규모 코퍼스 프로토타입(§11 P5) + 독립 검증(§11 P6) 이후 별도 승인 대상이다.

### 2.3 Adoption ≠ Implementation

이 ADR이 Proposed → Approved로 승격되어도, 그 자체로 production mutation을
수행하지 않는다(ADR-030 §Adoption mutation=0 패턴 준용). 구현은 §11의 개별
Task Order가 결정한다.

---

## 3. Non-Goals / OUT-OF-SCOPE

### 3.1 Voice Profile / TTS / 음성 복제 — 전면 제외

SESAME Notice §9의 Optional Voice Profile Module은 **이 ADR의 범위에서 완전히
제외한다.** optional module 형태로도 스키마·인터페이스·스텁을 만들지 않는다.

이유:
- 음성 복제는 rights·동의·윤리 거버넌스가 저장소에 전무하다.
- DBMA는 텍스트 RAG·생성 플랫폼이며 음성은 파이프라인 순서(추출→…→평가) 밖이다.
- 프로젝트 원칙: half-finished 구현 금지, 불필요한 추상화 금지.

Voice/TTS는 **별도 HQ 승인 + 별도 ADR**이 선행되지 않으면 착수·설계·스텁 생성
모두 금지한다.

### 3.2 "Write like Preacher X" 단순 프롬프트로의 축소 — 금지

SESAME는 few-shot 어휘 모방으로 환원되지 않는다. 재현 가능한(reproducible)
특성 — 구조 패턴, 수사 패턴, 담화 흐름, 적용 전개 — 을 모델링한다.
`style_examples`(현행) → `style_profile`(구조화) 승격이 목표다.

### 3.3 신규 Retrieval 경로 — 금지

SESAME는 검색 신호가 아니라 **생성 시점 입력**이다. `core/retrieval.py::RetrievalEngine`,
하이브리드 스코어, 랭킹, 벡터/BM25 경로를 일절 건드리지 않는다(ADR-001 유지,
ADR-009가 SIL을 retrieval 밖에 둔 것과 동일 원칙).

### 3.4 CLEAN 코퍼스 동결 위반 — 금지

ADR-030 §3의 3,319 verified TSU / `nae_tsu_v1` / `nae_ref_v1` CLEAN 영역을
SESAME를 이유로 재처리·재승인·migration하지 않는다.

---

## 4. Architecture Placement — DBMA-TLI "Style Engine" 슬롯

SESAME는 **DBMA-TLI(Theology Language Intelligence) Language Layer의 Style Engine
구성요소**로 귀속한다. `DBMA-TLI-Architecture-Vision-v1.md` §4가 이미 예약한
슬롯의 구체화다.

```text
Application Layer → Generation → Research → Retrieval → TLI → Dictionary → Storage
                                                        │
                                                  Style Engine  ── SESAME
```

TLI 원칙 준용:
- 어댑터 인터페이스 뒤에 둔다 — `core/tli/style_engine.py`가 인터페이스,
  구현체는 코퍼스 기반 프로파일 빌더.
- 스타일 규칙·특성 목록을 코드에 하드코딩하지 않고 리소스/데이터로 관리한다.
- 수요가 확인된 범위만 Task Order로 구현한다. 스텁 선제작 금지.

**미해결(HQ 확인 필요)**: 현재 TLI는 결정론적 언어 도구(Hunspell)만 담고 있다.
SESAME의 통계·코퍼스 모델을 TLI 범위 안에 두는지, 아니면 TLI **옆에** 서서
TLI를 소비하는 형제 계층으로 두는지 §12 O-1에서 HQ 결정을 요청한다.

---

## 5. Subordinate Contracts — 기존 ADR에 대한 종속

### 5.1 내용/스타일 분리 (ADR-002 패턴 재사용)

- `style_profile`은 코퍼스·설교 식별자를 **참조**만 한다. TSU 레코드·TSU 스키마를
  읽지도 쓰지도 변경하지도 않는다.
- 방향: `style_profile → (corpus sermon id)` 단방향. ADR-002의
  "두 독립 네임스페이스 + 단방향 참조" 패턴과 동일.
- `TSU + SESAME` 결합 생성 시에도 신학적 내용의 provenance와 스타일 제어의
  provenance를 분리 기록한다(§7).

### 5.2 코퍼스 수급 (ADR-030 경유)

- SESAME는 신규 ingestion path / collector 권한 / state machine을 만들지 않는다.
- 설교 코퍼스 자료의 편입은 ADR-030의 **Admission Decision**
  (`NAE/governance/corpus_admissions.jsonl`, append-only) 절차를 따른다.
- Track 분리 원칙 유지: SESAME 코퍼스는 TSU Track / Reference Track과 별개의
  **Style Corpus** 취급이며, "embedded" 용어로 뭉뚱그리지 않는다.
- 기존 `sermon_corpus/` 수집물의 SESAME 사용 가부도 Admission Decision 대상이다.

### 5.3 스타일 평가 (ADR-012 DBMA-SEQ 재사용)

- SESAME Notice §12·§13(블라인드 스타일 평가, 구조·수사·어휘·적용·담화흐름
  유사도)은 **DBMA-SEQ로 라우팅**한다. SESAME 내부에 병렬 평가 체계를
  신설하지 않는다.
- 역할 분담: **SESAME**가 `style_profile`을 생성 → **DBMA-SEQ**가 생성된 설교를
  프로파일 대비 채점. ADR-012 방향 #2("few-shot 예시 뱅크 공식화")의 backing
  모델이 SESAME `style_profile`이 된다.
- ADR-009 Doctrine Filter 선례 준용: **백분율 점수 금지**("Structural Similarity 87%"
  같은 정밀 숫자 안티패턴), "확실하지 않음"을 그대로 노출, 최종 판단은 목회자.

### 5.4 설교 생성 통합 (ADR-009 DBMA-SIL)

- 통합 지점은 `core/generation.py::SermonDraftService` 한 곳이다.
- 현행 `style_examples: str`(자유 텍스트 few-shot) → `style_profile`(구조화) **승격
  경로**를 설계한다. 기존 `style_examples` 경로는 fallback으로 유지(회귀 방지).
- SIL의 교리 필터·생성 프롬프트는 SESAME 범위 밖. SESAME는 SIL의 대칭축("how")
  이지 SIL의 대체가 아니다.

### 5.5 Retrieval 무변경 (ADR-001)

§3.3 재확인. 읽기 전용 참조도 `RetrievalEngine` 코드에 신규 의존을 만들지 않는다.

---

## 6. style_profile — 후보 스키마 (동결하지 않음)

기존 `sermon_corpus/analyzer` 산출물의 **rollup/consumer**로 정의한다. 신규 추출
로직은 갭이 확인된 축에만 최소로 추가한다.

```yaml
style_profile:
  profile_id: <string>            # SESAME 자체 네임스페이스, TSU/document_id와 무관
  preacher_ref: <string>          # 코퍼스 상 설교자 식별 (Admission Decision에 등재된 것만)
  corpus_scope:
    sermon_ids: [<string>, ...]   # 참조만 (ADR-002 단방향)
    sermon_count: <int>
  structure:      {}              # §4-A 서론→문제→본문→해설→교리→적용→복음→결론 (코퍼스 발견)
  rhetoric:       {}              # §4-B 수사 질문·반복·대조·점층·인용·직접 호명 빈도/배치
  language:       {}              # §4-C 문장/문단 길이 분포·어휘 선호·인용 밀도·인칭·능동/수동
  illustration:   {}              # §4-D 예화 유형·빈도·배치·논증상 기능
  application:    {}              # §4-E 교리→개인 확신→실천→회중 권면 전개
  transition:     {}              # 대지 간 전이 방식
  conclusion:     {}              # 결론 유형·마무리 강조
  provenance:     {}              # §7
  validation:     {}              # §8 재현성·안정성 근거
```

- 각 축의 내부 필드·값 표현은 P4(§11)에서 후보로 제시하고 P6 검증 후 승인 대상.
- 중복 필드 신설 금지 원칙(ADR-030 F-1 준용): `sermon_corpus/analyzer`가 이미
  내는 통계는 그대로 참조하고 재정의하지 않는다.

---

## 7. Provenance 요건

NAE 레코드와 **동일 형식**의 provenance 블록을 `style_profile`에 부착한다:

```yaml
provenance:
  source_corpus_ids: [<string>, ...]   # Style Corpus admission 기록과 대조 가능
  admission_ref: <string>              # NAE/governance/corpus_admissions.jsonl 항목
  extraction_run_id: <string>
  extractor_version: <string>
  validator_version: <string>
  created_at: <iso8601>
  content_style_separation: true       # 신학 내용 authority에 영향 없음을 명시
```

- `style_profile`은 신학적 authority를 부여하지 않는다. 스타일 프로파일이
  LLM 생성물이라는 이유만으로 authoritative로 취급하지 않는다.
- ADR-021/030의 raw 보존·append-only 규율을 Style Corpus에도 적용한다.

---

## 8. Verification Principle

유효한 스타일 특성은 다음을 만족하는 것을 선호한다:

```
반복 관찰됨  +  통계적/질적으로 유의미  +  다수 설교에 걸쳐 안정적  +  설교 소통에 의미 있음
```

- 한 편의 이례적 설교가 설교자의 스타일을 정의하지 않는다.
- 일반 설교에 흔한 특성을 특정 설교자에게 자동 귀속하지 않는다.
- 재현성 측정은 DBMA-SEQ harness(ADR-012 방향 #4 골든셋 패턴)를 재사용한다.

---

## 9. 코드 배치 (구현 시)

| 산출물 | 경로 | 성격 |
|---|---|---|
| 스타일 추출·분석 | `sermon_corpus/analyzer/style/` (기존 패키지 확장) | 신규 top-level 패키지 금지 |
| 스타일 엔진 인터페이스 | `core/tli/style_engine.py` | 어댑터 인터페이스 |
| 프로파일 조회/조립 | `core/tli/` 내 구현체 | 리소스/데이터 기반 |
| 생성 통합 | `core/generation.py::SermonDraftService` (기존 파일, 최소 변경) | `style_examples` → `style_profile` 승격 |
| 평가 | `core/evaluation/` (DBMA-SEQ, ADR-012) | SESAME 밖 |
| 프로파일 데이터 | 데이터 디렉터리(경로 P4 확정) | 코드 하드코딩 금지 |

스텁 선제작 금지 — 각 파일은 해당 Task Order 착수 시점에만 생성한다.

---

## 10. Risks

| # | 리스크 | 완화 |
|---|---|---|
| R-1 | `sermon_corpus/` 재발명 | §11 P2 자산 재고를 P4 앞에 강제 |
| R-2 | style_profile이 TSU/retrieval에 은근히 결합 | ADR-002 단방향 참조 + ADR-001 무변경, C1 검증 항목 |
| R-3 | 정밀해 보이는 유사도 % 남발 | §5.3 백분율 금지, 자연어 서술 |
| R-4 | Voice/TTS 범위 오염 | §3.1 전면 제외 선언 |
| R-5 | Proposed 상태 ADR을 근거로 조기 구현 | Evidence Before Promotion Rule, §2.3 |
| R-6 | 저작권 — 타 설교자 코퍼스 대량 학습 | ADR-030 Admission Decision + rights 필드, Style Corpus 별도 취급 |
| R-7 | TLI 범위 확장 여부 미정으로 배치 표류 | §12 O-1 HQ 결정 선행 |

---

## 11. Work Sequence (골격 — 각 단계 별도 Task Order)

```text
P0  이 ADR-032 골격 → 본안 작성 (명명·귀속·종속 계약·OUT-OF-SCOPE 확정)
P1  C1 독립 리뷰 (신규 Architecture Layer + Metadata Model → 필수 트리거)
P2  기존 자산 재고: sermon_corpus/analyzer 커버리지 vs §4 A~F 도메인 갭 (읽기 전용)
P3  Style Corpus 요건 정의 + ADR-030 Admission Decision 절차 적용안
P4  style_profile 스키마 후보 확정안 (analyzer 출력 rollup, provenance 블록 포함)
P5  소규모 프로토타입: 대표 설교 3~5편, sermon_corpus/analyzer/style/ 확장
P6  독립 검증(C1) + DBMA-SEQ harness로 프로파일 재현성·안정성 측정
P7  ADR-032 Approved 승격 (구현완료 + 회귀 PASS + C1 완료 + HQ 승인 4조건)
P8  core/tli/style_engine.py 인터페이스 + 프로파일 조회 구현
P9  SermonDraftService 통합: style_examples → style_profile 승격 (fallback 유지)
P10 (보류) Voice/TTS — 별도 HQ 승인 + 별도 ADR 전까지 착수 금지
```

Notice의 P0→P8 "concept to production" 도약 금지 원칙 유지. **P2를 P4보다 반드시
먼저** 수행해 R-1을 차단한다.

---

## 12. Open Questions — HQ 결정 필요 (이 골격이 단정하지 않는 것)

| # | 질문 | 기본값 제안 |
|---|---|---|
| O-1 | SESAME를 TLI **범위 안** Style Engine으로 둘지, TLI **형제 계층**으로 둘지 | 형제 계층(TLI를 소비), TLI 비전 §4는 슬롯 근거로만 |
| O-2 | Style Corpus에 타 설교자 자료를 포함할지, 특정 설교자(예: 본인) 단일 코퍼스로 한정할지 | 단일 설교자 코퍼스로 시작 |
| O-3 | `style_profile` 영구 저장 위치(파일/registry) 및 버저닝 정책 | 파일 + `profile_id` 버전 접미사, P4에서 확정 |
| O-4 | 기존 `sermon_corpus/` 수집물의 SESAME 사용을 소급 Admission으로 처리할지 | 신규 Admission 기록 작성(소급 승인 아님) |
| O-5 | ADR 파일명 접두: `SESAME` vs `NAE-` vs `DBMA-TLI-` | `SESAME`(본 골격 채택) |

---

## 13. C1 Review Triggers (CUE Operating Policy 대조)

이 작업은 다음에 해당하여 **C1 Independent Review 필수**:

- 새 ADR 작성 ✔
- 새 Architecture Layer 추가 ✔ (TLI Style Engine 구체화)
- Metadata Model 변경 ✔ (`style_profile` 스키마 신설)

따라서 SESAME Notice §10-2("CUE가 새 ADR 필요 여부를 판단")는 판단 여지 없이
**필수**로 확정한다.

---

## 14. Promotion Conditions (Proposed → Approved)

CUE Operating Policy의 4조건 전부 충족 시에만 승격:

1. 구현 완료 (P8~P9 최소 범위)
2. 회귀 테스트 통과
3. C1 독립 리뷰 완료
4. Rev. Bang / HQ 승인

4개 중 하나라도 미충족이면 Proposed 유지. 그동안 이 ADR은 다른 구현의 근거가
되지 않는다.

---

## 15. Immediate Disposition

§0 HQ Decision(2026-09-05)에 따라 **현 시점 처분은 "동결 보존"이다.**

- **HQ**: SESAME 착수 시점은 현재 Release 배포 완료 이후 HQ가 별도 지시한다.
- **CUE**: 이 골격을 보존만 한다. 착수 지시 전까지 본안 확장·Proposed 승격·P2 자산
  재고·스텁·스키마·데이터 등 SESAME 관련 선행 작업을 일절 수행하지 않는다.
  착수 지시 시 §11 P0(통합 관계 재검토 → 본안 확장)부터 시작한다.
- **C1**: 착수 후 본안이 나오면 §13 트리거로 독립 리뷰. 그 전에는 대기.

### 참고 — 착수 시 재검토 대상 (§0 지시)

- DBMA-TLI "Style Engine" 슬롯 (`DBMA-TLI-Architecture-Vision-v1.md` §4)
- `sermon_corpus/analyzer/` 커버리지 및 확장 지점
- ADR-002 (내용/스타일 분리 패턴) · ADR-009 (SIL 통합 지점) ·
  ADR-012 (DBMA-SEQ 평가) · ADR-030 (Sermon Corpus Governance)

---

*본 문서는 골격(SKELETON)이며 `docs/architecture/`만 대상으로 작성되었다. 어떤 코드·데이터·
코퍼스·config도 수정하지 않았다. §9·§11의 구현 항목은 결정 기록이 아니라 향후 Task Order
후보 목록이다.*
