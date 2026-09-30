# FU-007 / GS — ADR-036 ARCHITECTURE CONTRACT CLEANUP BRIEF

- 작성: CUE · 2026-09-30
- 단계: HQ 결정 순서 ② ADR 정리(① 릴리스 라인 = `dev/dbma-engine` 확정 이후)
- 방법: 읽기 전용
  - 사용한 명령: `git log --all`, `git show <ref>:<path>`, `git grep <ref>`, `git ls-tree`, `git cat-file -e`, `git branch -r --contains`
  - checkout·fetch·ADR 수정은 하지 않았다.
- 표기: [CONFIRMED] git·문서로 확인 / [INFERRED] 추론 / [UNKNOWN] 미확인
- 임시 식별자
  - **ADR-036-A** = `ADR-036-Grounded-Synthesis-Boundary.md`
  - **ADR-036-B** = `ADR-036-NAE-Public-Evidence-in-Answer-Generation.md`
- **MUTATION: NONE.** 이 보고서 커밋만 한다.

> 이 문서는 추천하지 않는다. 번호·폐기·반영·개정은 HQ의 ② 결정이다.

## 1. BASELINE

| 항목 | 값 |
|---|---|
| 작업 트리 | `~/DBMA_wt/fu007` / `tmp/fu007-integration-trial` |
| 착수 확인 | HEAD `c9f64b2f`, STATUS 0 [CONFIRMED] |
| 조사 ref | `origin/main` `ced87898`, `origin/dev/dbma-engine` `195189b8`, `origin/claude/p4-final-validation-guide-b3af47`, `origin/claude/nae-end-user-acceptance-test-bd2fff` |

## 2. ADR-036 번호 중복

- [CONFIRMED] 전 ref의 이력에서 `docs/architecture/ADR-036*` 경로는 **정확히 2개**다(A, B).
- [CONFIRMED] 두 문서는 **같은 ref에 함께 있은 적이 없다**.
  - A: `p4-final-validation-guide` 브랜치에만 있음
  - B: main 계열(main, EUAT, FU-004, tmp 브랜치들)에 있음
- [CONFIRMED] **dev에는 ADR-036이 없다**(`ls-tree` 0건, `git grep 'ADR-036'` 0건).

## 3. ADR-036-A 계보 (GS 경계)

| 항목 | 값 | 근거 |
|---|---|---|
| 제목 | ADR-036: Grounded Synthesis Boundary | A L14 |
| 최초 커밋 | `f4cbbcae` 2026-09-27 20:05 "P3A~P12 단계별 작업지시서 + ADR-036 + 안전기준선" | `git log --all` |
| 최초·유일 ref | `origin/claude/p4-final-validation-guide-b3af47` | `branch -r --contains` |
| 상태 | **Accepted** (2026-09-27) | A L18 |
| 승인 | Deciders "HQ (승인, 2026-09-27)" / 승인 반영 커밋 `e69eda64` 22:11 "ADR-036 Accepted" | A L20, `git log` |
| main / dev / peb / EUAT 존재 | 없음 / 없음 / 없음 / 없음 | `cat-file -e` |
| 구성 | B1~B9 결정 + 검증 계획 + Consequences + Next Steps (159행) | A L40~L159 |

## 4. ADR-036-B 계보 (공개 자료 근거 답변)

| 항목 | 값 | 근거 |
|---|---|---|
| 제목 | ADR-036: NAE Public-Theology Evidence in Answer Generation (Chat/Research) | B L16 |
| 최초 커밋 | `dd5bd005` 2026-09-29 23:03 "ADR-036 초안(Proposed)" | `git log --all` |
| 구현 커밋 | `7173f57a` 09-29 23:19 "방안 B — 공개 자료 근거 답변" | 〃 |
| 승인 커밋 | `c9650a22` 09-30 00:35 "ADR-036 Approved 승격(방안 B)" | 〃 |
| 상태 | main판 **Proposed**, EUAT판 **Approved** (2026-09-30, Rev. Bang 승인, Evidence Before Promotion 4조건 충족) | B L20 (EUAT) |
| 승인판 위치 | `origin/claude/nae-end-user-acceptance-test-bd2fff`에만 있음(`0dd61822`·`c9650a22`는 main에 없음) | `branch -r --contains` |
| main / dev 존재 | 있음(Proposed판) / **없음** | `cat-file -e` |

## 5. NUMBERING CHRONOLOGY

| 시각 | 사건 | 근거 |
|---|---|---|
| 09-23 | ADR-035(목회자 서재 자동화, #76)가 dev에 들어옴. main에는 없음 | dev ADR 목록 |
| 09-27 20:05 | **A가 036 사용 시작**. 작성 브랜치 부모(`f4cbbcae^`)의 최대 번호는 ADR-034 | `ls-tree f4cbbcae^` |
| 09-27 22:11 | A Accepted(p4 브랜치). 이후 어떤 라인에도 병합되지 않음 | `branch -r --contains e69eda64` |
| 09-29 23:03 | **B가 036 사용 시작**. 작성 브랜치 부모(`dd5bd005^`)의 최대 번호도 ADR-034. A는 이 브랜치에 없었음 | `ls-tree dd5bd005^` |
| 09-30 00:35 | B Approved(EUAT 브랜치에만) | `c9650a22` |

- [CONFIRMED] **충돌 발생 시점은 B가 만들어진 09-29 23:03**이다. 그 전에는 A만 036을 쓰고 있었다.
- [CONFIRMED] B는 036을 고른 이유로 "ADR-035는 `claude/adr-035-pastoral-library-automation`·`feat/peb-v0.1`에 이미 존재해 회피"라고 적었다(B L23). A를 인지했다는 기록은 없다.
- [CONFIRMED] A 문서에는 번호 선택 근거가 없다(035·"번호" 검색 시 무관한 L33만 적중).
- [INFERRED] 두 작성 브랜치 모두 최대 번호가 034였는데 035를 건너뛴 것은, ADR-035가 다른 브랜치에 있음을 알고 피한 결과로 보인다. A는 확인되지 않았다.
- [CONFIRMED] 이후 번호를 바꾼 문서는 없다. 두 문서 모두 036을 유지하고 있다.

## 6. ADR-036 REFERENCE INVENTORY

### 6.1 ref별 규모

| ref | "ADR-036" 적중 파일 | 그중 코드(core·ui·scripts·tests) |
|---|---|---|
| origin/main | 23 (docs 12, 그중 GS 문서 8) | 10 (A식 "Bn" 24행 + B식 "방안 B" 2행) |
| origin/dev/dbma-engine | **0** | 0 |
| p4-final-validation-guide | 21 | 0 |
| EUAT | 24 | 10 |

### 6.2 코드 참조 (origin/main) — 어느 ADR-036을 가리키는가 [CONFIRMED]

| 파일:행 | 참조 절 | 대상 |
|---|---|---|
| `core/grounded_answer.py` L3, L16, L38, L82 | B8, B5·B8 | **A** |
| `core/grounded_citation.py` L9, L130 | B6 "결정적 검사" | **A** |
| `core/grounded_claims.py` L11, L18, L39, L65 | B1, B8, B4·B8, B4 | **A** |
| `core/grounded_synthesis_input.py` L4, L13, L19, L37, L53, L63, L77 | B8, B9, B3, B2 | **A** |
| `scripts/grounded_synthesis_integration_demo.py` L77, L83 | B3 | **A** |
| `tests/test_grounded_answer.py` L299, `test_grounded_claims.py` L252, `test_grounded_synthesis_input.py` L13·L327·L369 | B8, B9 | **A** |
| `ui/components/nae_public_section.py` L121 | "방안 B(Proposed)" | **B** |
| `tests/test_nae_public_answer.py` L1 | "방안 B" | **B** |

- [CONFIRMED] GS 코드가 인용하는 절은 **B1·B2·B3·B4·B5·B6·B8·B9**다(B7만 코드 인용 없음). 모두 A의 절 체계(A L42~L133)와 일치한다.
- [CONFIRMED] 코드 안에서 두 ADR은 **번호가 같고 절 표기로만 구별**된다("B4"류 = A, "방안 B" = B).
- [CONFIRMED] **main의 GS 코드가 main에 없는 문서(A)를 인용한다.** 경로로 A를 가리키는 main 문서는 1개이며, 그 문서는 A를 "review 브랜치의 파일"이라고 명시한다(C-03 brief L12~L13).
- [CONFIRMED] B의 경로를 가리키는 문서: main 2, EUAT 2.

## 7. DEV ADR STATE

| ADR | dev | 상태(dev판) | GS·생성 계약과의 관계 |
|---|---|---|---|
| ADR-001 Retrieval Engine Authority | 있음 | accepted | 검색 엔진 단일 정본(B가 범위 밖으로 명시, B L53) |
| ADR-009 SIL Theology Engine | 있음 | Architecture Decision(전체 확정) | 교리 필터 |
| **ADR-009 Amendment A** "교단 프로파일의 답변 생성 경로 확장" | 있음(main에도) | **Proposed** | **운영 생성 경로의 `_DENOMINATION_DIRECTIVE` 근거**(Amendment L45·L53, 커밋 `861ebdfa`·`1319a1c3` 09-10) |
| ADR-024 NAE Production Retrieval Bridge | 있음 | Approved | B가 "변경하지 않는다"고 명시한 상위 ADR |
| ADR-028 NAE Smith Reference Layer | 있음 | Accepted | B가 선례로 인용 |
| ADR-035 NAE 목회자 서재 자동화 | 있음(main 없음) | Approved (2026-09-23) | 생성 계약과 직접 관련 없음 |
| ADR-036-A (GS 경계) | **없음** | — | GS 코드의 계약 원본 |
| ADR-036-B (공개 자료) | **없음** | — | `nae_public_section` 경로의 계약 |
| C-03 결정 문서 | **없음** | — | GS "grounded" 의미 결정 |
| GS 코드·근거 계층 | **없음** | — | (① 결정 자료 5절) |

[CONFIRMED] dev 기준으로는 **GS·공개 자료 답변·C-03 관련 계약 문서가 하나도 없다.** 계약 문서는 모두 main 계열 또는 review 브랜치에 있다.

## 8. C-03 DECISION RELATIONSHIP

| 항목 | 값 | 근거 |
|---|---|---|
| 파일 | `docs/grounded_synthesis/GS-FINAL-RPV-C03-ARCHITECTURE-DECISION-BRIEF.md` | — |
| 최초 커밋 | `02400e38` 09-28 17:13 "GS-FINAL-RPV HOLD — C-03 Architecture Decision Brief" | `git log --all` |
| 위치 | main에 있음 / dev·p4 브랜치에 없음 | `cat-file -e` |
| 문서 성격 | **ADR이 아니다.** "정책 결정을 HQ에 요청. 구현하지 않음"인 Decision Brief | C-03 L1, L6 |
| 결정 기록 | 최종 보고서: HQ가 "구조적 검증과 의미적 지지 판정을 분리 유지"로 결정, corrective WO 대상에서 제외 | `GS-FINAL-RPV-FINAL-REPORT.md` L126~L133 |
| A와의 관계 | A B6(결정적 검사와 의미 지지 판정의 분리)을 **재확인**한 결정. A를 바꾸지 않음 | C-03 L10~L22, 최종 보고서 L118 "ADR-036 B6 원 설계 재확인" |
| 구현과의 관계 | `grounded` 상태 = 구조적 검증만 의미. `grounded_answer`·`grounded_citation` 코드 변경 없음 | 최종 보고서 L118 |

[INFERRED] 계층은 이렇게 정리된다: A B6(Accepted, 설계) → C-03(HQ 정책 결정, 재확인) → 구현(무변경). C-03은 A에 **종속**되는 결정 기록이며 독립 ADR이 아니다.

## 9. ARCHITECTURE FREEZE RULE

- [CONFIRMED] 원문 위치: `CLAUDE.md` L320~L335 "Architecture Freeze Rule". main판과 dev판이 동일한 blob이다.
  - 요지: "ADR가 **Approved** 상태가 되면 … 자동으로 변경하거나 우회해서는 안 된다 … 변경이 필요한 경우 반드시 새로운 ADR Amendment 또는 ADR Revision 문서를 먼저 작성하고 승인받은 후에만 구현한다."
- [CONFIRMED] `CLAUDE.md` L360~L363: "ADR 폐기"는 자동화로 하지 않고 항상 승인을 요청하는 예외다.
- [CONFIRMED] `docs/architecture/DBMA-Documentation-Rules.md`(dev)에는 일반 문서의 상태 전이(active/deprecated)만 있고, **ADR 번호 부여·재부여 규칙은 없다**.

| 질문 | 답 |
|---|---|
| 1. ADR 번호 변경이 architecture change인가 | **[UNKNOWN]** 규칙에 번호·메타데이터 언급 없음 |
| 2. ADR 내용 변경이 architecture change인가 | [CONFIRMED] Approved ADR의 규칙 변경은 Amendment/Revision을 먼저 요구 |
| 3. 단순 번호 충돌 해결도 freeze 대상인가 | **[UNKNOWN]** |
| 4. 승인된 ADR의 메타데이터 수정 취급 | **[UNKNOWN]** |
| 5. HQ 승인이 필요한 경우 | [CONFIRMED] Approved ADR의 변경(Amendment/Revision), ADR 폐기 |
| 추가: A의 상태는 "Accepted"이고 규칙 문구는 "Approved"다 | **[UNKNOWN]** 두 용어의 동일 취급 여부는 규칙에 없다. A는 HQ 승인(2026-09-27)을 적고 있으며, 자체 Next Steps에 "승격 조건을 P9 종료 시점에 한 번에 판단"(A L154~) 문구가 있다 |

## 10. CONTRACT RELATIONSHIP — 세 가지 구분

### 10.1 ADR NUMBER COLLISION
- [CONFIRMED] 있다. 같은 번호가 서로 다른 두 문서에 쓰였고, main 코드는 두 문서를 모두 "ADR-036"으로 인용한다(6.2절).
- 충돌은 문서가 서로 다른 ref에 흩어져 있어 **작성 당시 서로 보이지 않았기 때문에** 생겼다(5절).

### 10.2 ADR CONTENT / CONTRACT RELATIONSHIP
- **A가 규정하는 것**: GS 라이브러리의 경계
  - B1: P12까지 `ui/`·운영 생성 경로에 연결하지 않음. `generation.py`·`claim_guard.py`를 수정·대체·우회하지 않음. **운영 경로 교체는 P12 이후 새 ADR과 HQ 승인**
  - B2: LLM 입력은 EvidencePool뿐. 학습된 암묵 지식을 사실처럼 제시하는 것 금지
  - B3: 결정적 절단
  - B4: claim의 근거 ID는 manifest의 부분집합이어야 하며, 어기면 표시만 함
  - B5: 근거 부족은 정상 결과
  - B6: 결정적 검사와 의미 지지 판정의 분리
  - B7: 결정성
  - B8: 정본 데이터 구조
  - B9: 금지 import(`GenerationService` 포함)
- **B가 규정하는 것**: NAE 공개 자료로 **별도 두 번째 답변**을 만드는 운영 기능(방안 B)
  - 버튼 트리거, 스위치 하나, ADR-024 무변경
  - 생성은 **기존 운영 생성 경로의 근거 강제 지시문과 출처 라벨을 재사용**(B L99~L110)
- [CONFIRMED] **B는 A를 인용하지 않는다.** B가 인용하는 GS 쪽 문서는 "Grounded Synthesis AD-02(HQ 승인, Option D)" 하나다(B L54).
- [CONFIRMED] 두 문서의 대상이 다르다: A = 운영과 분리된 GS 라이브러리, B = 운영 생성 경로 위의 기능. **현재 서로 모순되는 규칙은 원문에서 찾지 못했다.**
- [INFERRED] **장래의 교차점**: GS를 운영 경로에 연결하면(A B1이 요구하는 새 ADR의 범위), B의 경로(`nae_public_section.py` L147, `generate_stream` 호출자)도 그 범위에 들어갈 수 있다. 그때 두 계약의 관계를 정해야 한다.

### 10.3 ARCHITECTURE DECISION CONFLICT
- [CONFIRMED] **A와 B 사이의 architecture decision 충돌은 원문에서 확인되지 않는다.**
- [CONFIRMED] 다만 ② 이후 결정과 직접 맞닿는 기존 결정이 있다.
  1. **A B1**: GS의 운영 연결은 "P12 이후 새 ADR과 HQ 승인" 사항이다. GS 통합은 A의 수정이 아니라 **새 ADR이 필요한 일**로 규정돼 있다.
  2. **A B6 + C-03**: 의미 지지 판정은 자동 채점과 분리한다. 자동 의미·교차언어 검증을 제품에 넣으면 이 결정과 맞닿는다(③ 교차언어 범위 결정의 전제).
  3. **A B9**: GS 모듈은 `GenerationService`를 import하지 않는다. 연결 방향에 대한 제약이다.
  4. **ADR-009 Amendment A(Proposed)**: 운영 생성 경로의 교단 지시문 근거가 아직 Proposed 상태다(P0-5의 교단 틀 문장과 관련, ④ 생성 계약의 전제).

## 11. UNKNOWN / UNVERIFIED

- ADR 번호 재부여·메타데이터 수정이 Architecture Freeze Rule의 대상인지(규칙에 명시 없음)
- "Accepted"(A)와 "Approved"(규칙 문구)의 동일 취급 여부
- A의 "P12" 조건이 충족됐는지(GS 여정 종결 문서와 A의 관계는 이번에 추적하지 않음)
- A를 작성할 때 035를 건너뛴 이유(문서에 기록 없음)
- B Approved판(`c9650a22`)을 main에 반영할 계획 여부(현재 EUAT 브랜치에만 있음)
- ADR-009 Amendment A가 Approved로 승격되지 않은 이유와 현재 효력

## 12. HQ DECISION OPTIONS (추천 없음)

| 선택지 | 내용 | 영향 범위(사실) |
|---|---|---|
| **A. 번호 재정리(한 문서 이동)** | A 또는 B 중 하나에 새 번호 부여 | **A를 옮기면**: main 코드 24행("ADR-036 Bn" 주석·docstring, core 4파일 17행, 데모 2행, 테스트 3파일 5행), main의 GS 문서 8건, p4 브랜치 문서 21건이 영향을 받는다. **B를 옮기면**: 코드 2행(`nae_public_section.py` L121, `test_nae_public_answer.py` L1)과 B 경로를 가리키는 문서 2건(main 기준). 두 경우 모두 이력 추적용 기록이 필요하다 |
| **B. 두 ADR 유지 + 역할 명시 후 번호 정리** | 두 문서의 architecture role(A = GS 라이브러리 경계, B = 운영 공개 자료 답변 기능)을 명시하고 번호 체계를 정리 | 선택지 A의 영향 + 역할 기록 문서. dev에는 두 문서가 모두 없으므로, dev 반영 경로(어느 판을 반영할지: A Accepted판, B Proposed판/Approved판)도 함께 정해야 한다 |
| **C. 현재 번호 유지 + 별도 정리** | 번호는 두고 식별 규칙(예: 파일명 전체 인용)으로 구분 | 변경 파일 최소. 현재 코드는 이미 절 표기로 구별 중이다(6.2절). 규칙상 가능 여부는 [UNKNOWN](9절: 번호 규칙 부재) |

선택지와 별개로, ② 결정에 **동반되는 사실**은 다음과 같다.
- dev(릴리스 라인)에는 A·B·C-03이 모두 없다 → 어느 선택지든 "dev 반영"이 따라온다.
- A B1에 따라, GS 운영 연결에는 **새 ADR**이 필요하다(번호 정리와 별개의 신규 문서).
- ADR 폐기는 CLAUDE.md상 항상 승인 사항이다.

## 13. MUTATION: NONE

- 조사 중 코드·ADR·git 변경 없음, checkout·fetch 없음
- 이 보고서의 커밋·푸시만 수행
