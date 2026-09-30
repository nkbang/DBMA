# NAE EUAT-001 후속 Task Order

근거 문서: [NAE_EUAT_001_RESULT.md](NAE_EUAT_001_RESULT.md), [부록 A](NAE_EUAT_001_APPENDIX_A_CORPUS_INDEX_OBSERVATION.md)
작성일: 2026-09-29 / 상태: **초안 (착수 전, 전 항목 사용자 승인 대기)**

## 0. 우선순위와 의존 관계

| ID | 제목 | 성격 | 승인 필요 | 선행 |
|---|---|---|---|---|
| FU-001 | 채팅–TSU 결합 여부 ADR 결정 | 설계(ADR) | 사용자 결정 + C1 Review | 없음 — **ADR-036 초안 작성, 사용자 결정 B(2026-09-29), 방안 B 구현 완료(C1 검토·승격 대기).** [ADR-036](architecture/ADR-036-NAE-Public-Evidence-in-Answer-Generation.md), [Build Report](NAE_EUAT_001_FU001_B_BUILD_REPORT.md) |
| FU-002 | Dagg·Hiscox 증분 재인덱싱 | 데이터 변경 | **사전 승인** (Embedding/Qdrant 쓰기) | FU-002-P(사전점검) — **완료(선택지 B): 신규 572건 적용, CHANGED 17건 보류.** [결과](NAE_EUAT_001_FU002A_OPTION_B_RESULT.md) |
| FU-003 | 신뢰 표시 결함 수정 (인용 검증·출처 고지·표시 품질) | 구현 | 부분(아래 참조) | 없음 — **구현 완료(C1 검토 대기).** [Build Report](NAE_EUAT_001_FU003_BUILD_REPORT.md) |
| FU-004 | Fuller·1689 인덱싱 범위 결정 | 설계/조사 | 사용자 결정 | 없음 |
| FU-005 | 콜드 상태 검색 실패 원인 규명 | 조사(읽기 전용) | 불필요 | 없음 |
| FU-006 | 미시험·미확인 항목 마감 | 조사(읽기 전용) | 불필요 | 없음 |
| FU-007 | 코드 기준선 정리 (`feat/peb-v0.1` ↔ `main` 분기) | 조사/결정 | 사용자 결정 | 없음 — **조사 완료(2026-09-29): 통합 라인이 둘(main / dev/dbma-engine)로 분기, 병합 방향은 HQ 결정 필요.** [결과](NAE_EUAT_001_FU007_BASELINE_DIVERGENCE_RESULT.md) |

권장 순서: FU-005·006(즉시 가능) → FU-002 → FU-003 → FU-001·004(결정 후).

## FU-007. 코드 기준선 정리 (`feat/peb-v0.1` ↔ `main`)

**배경 (FU-001 조사 중 발견)**: 운영·시험 앱이 구동되는 `~/DBMA`는 `feat/peb-v0.1`(+미커밋 18개)이며 `origin/main`과 분기되어 있다(main에 없는 커밋 105개, main에만 있는 커밋 82개). 실행 경로 변경이 양쪽에 따로 있다.

| 구분 | 내용 |
|---|---|
| peb에만 있음 | `398bc5cd` 한국어 질의 번역 전처리·빈 게이트 폴백(코퍼스 영어 vs 질의 한국어 어휘 불일치 해소), `2a326b2b`·`78e51c7e` 오염 문자 표식+고지, `64286013` 한국어 조사 토큰화, `311babd7`·`1b2dc035` ADR-035·Phase 1 화면 통합 등 |
| main에만 있음 | FU-003(인용 검증·고지·표시 품질), Grounded Synthesis 통합(PR #93), 기타 82커밋 |

**IMPACT**: 사용자가 보는 앱에 FU-003 수정이 없고, main에는 한국어 질의 검색 복구가 없다. 어느 쪽도 완전하지 않다.

**범위(제안)**: 읽기 전용 조사로 분기 내용을 분류(어느 커밋이 어느 쪽에만 있는지, 충돌 예상 파일)하고, 통합 방향(peb를 main에 병합 / main을 peb에 병합 / 선별 반영)을 사용자에게 제시한다. 병합·리베이스는 이 TO에서 하지 않는다.
**금지**: 분기 브랜치 변경, force push, 커밋 이력 재작성.

---

## 1. 공통 원칙

- 구현 주체는 CUE, 검증은 C1(독립). 근거 문서의 수치는 CUE가 직접 실측한 값이며, C1 보고는 항상 CUE가 교차검증한다(V0-V9 규칙).
- Architecture Freeze Rule: Approved ADR과 충돌하는 구현은 ADR Amendment/Revision 승인 전에는 하지 않는다.
- 보호 대상(RAW, Retrieval Engine, Embedding Engine, TSU Pipeline, 기존 ADR, Production Registry)은 명시 승인 없이 변경하지 않는다.
- 각 TO는 완료 시 Build Report를 남기고, 이 문서의 상태 표를 갱신한다.

---

## FU-001. 채팅–TSU 결합 여부 ADR 결정

**배경 (EUAT Issue 1)**: 채팅 답변 경로(`ui/pages/chat.py`)는 내 서재만 검색하고, Dagg/Hiscox는 별도 패널(`nae_public_section.py`)에 근거 카드만 표시된다. 사용자는 "내 서재 자료를 근거로 답하고 출처를 밝혀 달라"고 물었으나 내장 TSU 기반 답변을 받을 수 없다.

**충돌 (반드시 먼저 읽을 것)**: ADR-024(Approved, 2026-08-17) §B는 DBMA 결과와 NAE 결과를 **병합하지 않고 별도 섹션으로 병렬 표시**한다고 명시하고, 병합은 "별도 Architecture Decision(후속 ADR 대상)"으로 남겼다(§B, §H). 따라서 채팅 답변에 TSU를 연결하는 것은 ADR-024를 우회하는 구현이며 **이 TO에서는 코드를 쓰지 않는다**.

**범위**: 후속 ADR(또는 ADR-024 Amendment) 초안 작성까지.
- 선택지 비교: (A) 현행 유지 + UI 안내 강화, (B) 공개 패널 근거를 입력으로 하는 별도 "공개 자료 답변" 생성, (C) 채팅 답변에 TSU 근거 병합.
- 각 선택지의 영향: ADR-001(Retrieval Engine Authority), ADR-013(벡터스토어 분리), 격리 사고(2026-08-16 dbma-core-nae-isolation-violation) 재발 방지, 인용 신뢰성(FU-003).
- 업계 표준 패턴 확인 후 채택안 근거 명시.

**금지**: 코드 수정, 기존 ADR 문구 변경, Retrieval Engine 변경.
**완료 조건**: ADR 초안(Proposed) + C1 Review 요청. Approved 승격은 Evidence Before Promotion 4조건을 따른다.
**사용자 결정 필요**: 방향(A/B/C) 선호. 없으면 C1 Review 결과를 근거로 권고안 제시.

---

## FU-002. Dagg·Hiscox 증분 재인덱싱

**배경 (EUAT Issue 3, 부록 A-2·A-3)**: verified인데 미인덱싱 Dagg 321·Hiscox 251건(9/15~9/16 승인), 내용이 바뀐 CHANGED 17건(claim 오염 교정). Hiscox 권징 근거 45건 누락. 원인은 인제스트가 8/11 이후 재실행되지 않은 것.

**FU-002-P (사전점검, 읽기 전용, 승인 불필요)**
1. 메인 체크아웃(`~/DBMA`)의 미커밋 수정 17개 중 보호 파일(`embed/client.py`, `tsu/builder.py`, `tsu/runner.py` 등) 포함 여부 확인. 포함 시 `--apply`는 ADR-030 §14 위반이므로 **중단하고 보고**.
2. ~~TSU-0002210 헬라어 삭제 확인~~ — FU-006 원문 대조로 해소: 원문에 헬라어 없음, 삭제된 "Ευχαριστία"는 모델 도입 표기(부록 A-3 참조). 이 항목은 불필요.
3. 재승인 정책(승인 후 claim 수정 17건)에 대한 사용자 판단 요청.
4. `nae_incremental_ingest.py --dry-run` 재실행으로 NEW 321/251, CHANGED 14/3이 유지되는지 확인.

**FU-002-A (실행, 사전 승인 필요)**
- `python scripts/nae_incremental_ingest.py --identifier Dagg_Church_Order --apply`, 이어서 `Hiscox_Standard_Manual` (Dagg → Hiscox 순).
- 기존 벡터는 건드리지 않는 증분 upsert 경로만 사용(`index_all()` 금지).
- 실행 전 Qdrant `nae_tsu_v1` 상태(points 3,319)와 `incremental_state.json` 백업 위치를 기록.

**완료 조건**
- `nae_tsu_v1` points = 3,319 + 572 = **3,891** (Dagg 3,279, Hiscox 612), Fuller 0 유지.
- 재실행 dry-run 결과 NEW 0, CHANGED 0.
- CHANGED 17건의 Qdrant payload claim에 타 문자가 남아 있지 않음(스캔).
- Regression: `tests/test_nae_incremental_ingestion.py` 및 NAE 관련 회귀 통과.
- EUAT-01·02를 UI에서 재시험해 결과 변화를 기록(공개 패널 기준).

**중단 조건**: 보호 파일 미커밋 수정 발견, upsert 오류, points 수가 예상과 다름.
**C1 Review**: Production 승격 성격이 아니므로 사후 검증 1회(V1~V3 유형)로 충분.

---

## FU-003. 신뢰 표시 결함 수정

**배경 (EUAT Issue 4·5·6·7)**

| 결함 | 근거 | 조치 방향 |
|---|---|---|
| 근거 없는 인용 (EUAT-05의 1689 문장에 Spurgeon 인용) | 인용 원문에 1689 언급 없음 | 인용-원문 일치 검증 (생성 후 인용 문구가 해당 출처 청크에 실제 존재하는지 확인, 없으면 인용 제거 또는 경고) |
| 출처 고지 오표기 (Dagg/Hiscox 카드에 "Andrew Fuller…" 고지) | `citation_disclosure.py:get_disclosure()`가 `historical_witness`이면 Fuller 고정 문구 반환, 코드 주석이 "현재 이 등급은 Fuller 한 소스뿐" 가정 | 고지를 소스(source_id/author)별로 생성. 소스별 문구가 없으면 일반 문구 + 저자 필드 사용 |
| 관련성 ☆☆☆☆☆, 깨진 청크 제목, "주장 검증:" 빈 라벨 | UI 관찰 | 표시 로직 점검, 빈 라벨은 숨김, 깨진 청크(문자 비율 기준) 필터 |
| 한국어 외 문자 혼입("□" 치환) | 5건 중 2건(EUAT-02, EUAT-05; 초안의 3건은 부정확했음) | 원인 분석 우선(모델/프롬프트/토크나이저) — 이 TO에서는 진단까지, 수정은 별도 |

**제약**
- 인용 검증은 Generation/Retrieval의 신뢰 경계에 닿는다. **Retrieval Engine 자체는 변경하지 않고** 생성 후 검증 계층에서만 처리한다. Retrieval Engine 변경이 필요해지면 중단하고 승인 요청.
- 출처 고지는 ADR-0xx(Citation Disclosure 관련)의 Approved 규칙을 먼저 확인한다. 고지 문구·정책을 바꾸는 것은 ADR Amendment 대상일 수 있으므로, 구현은 "고지가 잘못된 소스를 가리키지 않게 한다"는 최소 범위로 한정한다.
- "예화 생성 절대 금지" 규칙: 검증 실패 시 생성 폴백을 만들지 않는다. 자료에 없으면 없는 대로 표시한다.

**완료 조건**: 각 결함별 회귀 테스트(인용 불일치 케이스, 소스별 고지 케이스), EUAT-05 재시험에서 근거 없는 인용 0건, Dagg/Hiscox 카드에 Fuller 고지 0건.
**C1 Review**: 새 Validator 추가에 해당하므로 요청.

---

## FU-004. Fuller·1689 인덱싱 범위 결정

**배경 (EUAT Issue 3)**: Fuller 8권(29,015 TSU)은 인덱스 0건이며 기존 기록상 processing HOLD. `SLBC1689`는 디스크에만 있고 인덱스에 없다(기존 기록상 N-8 BROKEN). 두 자료 모두 EUAT 질문(EUAT-03·04)의 직접 원인이다.

**범위**: 조사와 결정 자료 작성까지. 인덱싱 실행은 이 TO에 포함하지 않는다.
1. Fuller: 8권별 verified 수, 게이트 통과 수, HOLD 사유(ADR-030 관련 기록), 오염 claim 비율을 집계해 인덱싱 가능 범위를 산정.
2. 1689: `NAE/corpus/canonical/SLBC1689`의 상태와 N-8 BROKEN 기록의 근거 확인, 복구 가능성 평가.
3. 사용자에게 (a) 인덱싱 재개, (b) 범위 축소, (c) 보류 유지 중 결정을 요청.

**금지**: Corpus 전체 Migration, RAW 변경, TSU 재생성, Production Registry 변경. (이들은 항상 사전 승인 대상.)
**사용자 결정 필요**: 인덱싱 재개 시점과 범위. 결정은 "배포 버전 완성 최우선"이라는 기존 방침과의 우선순위를 고려해 내린다.

---

## FU-005. 콜드 상태 검색 실패 원인 규명 (읽기 전용)

**배경 (EUAT Issue 2)**: 첫 질문 성공 후 채팅 4회가 "검색 중 문제가 있었습니다", 공개 패널 최소 7회 "결과 없음"(대조군 "아브라함" 포함). 신규 프로세스의 어댑터 호출과 워밍 후 UI는 정상. bge-m3가 Ollama에 상주하지 않던 정황만 있음.

**범위**
1. 앱 로그 확보 경로 확인(Streamlit stdout 위치, 로거 설정). 로그가 남지 않으면 그 사실 자체를 결함으로 기록.
2. `NAE/retrieval_adapter.py`의 `limit_check`·deadline·timeout(Qdrant `timeout=2` 등)과 임베딩 호출 타임아웃을 읽고, bge-m3 콜드 로드 시간이 deadline을 초과하는지 계산.
3. 재현 실험(읽기 전용): 모든 Ollama 모델 언로드 상태에서 어댑터를 신규 프로세스로 호출해 지연·결과를 측정. 앱 프로세스는 건드리지 않는다.
4. 결과를 OBSERVED → EVIDENCE → IMPACT → RECOMMENDATION으로 보고.

**금지**: 코드·설정 수정, 앱 재시작, Ollama 설정 변경.
**완료 조건**: 원인 확정 또는 "확정 불가 + 필요한 로그 항목" 보고.

---

## FU-006. 미시험·미확인 항목 마감 (읽기 전용)

| 항목 | 방법 |
|---|---|
| "연구" 탭 AI 답변 | EUAT-01~05를 연구 탭에서 시험. `research.py`의 검색 경로가 채팅과 같은지 코드로도 확인 |
| CHANGED 17건 교정 시점·주체 | 9/14 재추출 보고서, 9/26 v1.1.0 커밋 이력으로 특정 |
| 생성 지연(90초~8분) 원인 | 모델 재로드 구간(첫 토큰까지 최대 5분)과 keep-alive 설정 확인 |
| 공개 패널 관련성 (권징 p.95·p.103이 상위 10건에 들지 않음) | 순위 요인(점수 분포, 문단 강화 로직) 분석. 개선은 Retrieval Engine 변경이므로 **분석만** |

**완료 조건**: 각 항목 결과를 EUAT 부록 A-5의 미확인 표에 반영(문서 갱신 커밋).

---

## 2. 사용자 결정이 필요한 항목 요약

1. FU-001: 채팅–TSU 결합 방향(A/B/C) 또는 C1 Review 후 결정 위임.
2. FU-002-P: 승인 후 claim 수정 17건의 재승인 정책, `--apply` 실행 승인.
3. FU-004: Fuller·1689 인덱싱 재개 여부와 범위.

## 3. 이번 초안에서 확인하지 못한 것

- Citation Disclosure를 규정하는 Approved ADR의 정확한 번호와 조항(FU-003 착수 전 확인 필요).
- 메인 체크아웃 미커밋 파일 17개의 상세 목록(FU-002-P에서 확인).
- Fuller의 게이트 통과 수와 HOLD의 정확한 사유(FU-004에서 확인).
