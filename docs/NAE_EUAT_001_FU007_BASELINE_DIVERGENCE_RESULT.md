# FU-007 결과: 코드 기준선 분기 조사 (`feat/peb-v0.1` ↔ `main` ↔ `dev/dbma-engine`)

기준일 2026-09-29. 근거: [후속 Task Order](NAE_EUAT_001_FOLLOWUP_TASK_ORDERS.md) FU-007. **읽기 전용** 조사다. 병합·리베이스·푸시·브랜치 변경을 하지 않았다. 병합 충돌은 `git merge-tree --write-tree`(작업 트리·ref를 바꾸지 않는 예측)로 계산했다.

## 결론

1. **통합 라인이 둘이다.** 기본 브랜치 `main`과 `dev/dbma-engine`이 서로 84/82커밋 분기했다. 어느 쪽도 상대의 상위 집합이 아니다.
2. **배포(베타) 계보는 `dev/dbma-engine` 쪽이다.** 최신 베타 태그 `beta-v1.3.0-rc6`은 `dev/dbma-engine`과 `feat/peb-v0.1`의 조상이지만 **`main`의 조상이 아니다.** 사용자 화면(NAE Phase 1 화면 통합, 온보딩), 배포 파이프라인, 코퍼스 기준선이 그쪽에 있다.
3. `main`에는 Grounded Synthesis 통합과 EUAT 후속 수정(FU-003)이 있고, 그쪽에는 없다.
4. **같은 결함을 양쪽이 따로 고쳤다.** 2026-09-26에 한국어 질의 검색 실패를 `main`은 한→영 용어 번역 4커밋으로, `dev`는 번역 전처리 1커밋(`398bc5cd`)으로 각각 고쳤다. 두 쪽 모두 `core/query_translation.py`를 새로 만들어 병합 시 충돌한다.
5. 병합 충돌은 **3개 파일**(`core/query_translation.py`, `core/candidate_generator.py`, `core/hybrid_candidate_pipeline.py`)뿐이며 모두 검색 경로다.
6. **시험·운영 앱이 도는 로컬 체크아웃에 위험 요소가 있다**: 푸시되지 않은 커밋 1개, 미커밋 검색 코어 변경.

## 1. 브랜치 지형

| 브랜치 | 위치 | 비고 |
|---|---|---|
| `main` (`35a842f9`) | GitHub 기본 브랜치 | Grounded Synthesis(PR #90·#93), EUAT 문서, FU-002·003 문서·코드 |
| `dev/dbma-engine` (`195189b8`) | 원격 | 끝이 "Merge PR #87 from feat/peb-v0.1". 베타 태그 계보 |
| `feat/peb-v0.1` 원격 (`912e6789`) | 원격 | dev보다 22커밋 앞섬 |
| `feat/peb-v0.1` 로컬 (`c2cdf147`) | `~/DBMA` (앱 구동 중) | 원격보다 1커밋 앞섬(**미푸시**) + 미커밋 18개 |

분기 규모(`origin/main` 기준): main에만 82커밋, peb에만 105커밋(분기점 2026-09-25 `39026424`). `dev/dbma-engine`과 `main`은 84/82, `dev/dbma-engine`과 `feat/peb-v0.1`은 1/22.

패치 동등성(`git cherry`): peb 커밋 105개 중 14개는 같은 패치가 이미 `main`에 있고 71개(비병합 기준)는 `main`에 없다. `main` 커밋 중 53개가 peb에 없다.

## 2. 무엇이 어느 쪽에만 있는가

| 구분 | 내용 |
|---|---|
| peb/dev에만 (71개) | NAE Phase 1 화면 통합(#75), 목회자 서재 자동화 ADR-035(#76), 온보딩 수정 다수, 베타 배포 파이프라인(rc6, 코퍼스 GitHub Release 자산), PEB v0.1 사용자 인수 하네스, 한국어 조사 토큰화, **한국어 질의 번역 전처리(`398bc5cd`)**, 오염 문자 표식+고지, Fuller F3 검수, P0-5 채점 결과 |
| main에만 (53개) | **Grounded Synthesis**(scope `grounded-synthesis` 47커밋: AD-01/AD-02 앱 통합 포함), 검색 개선 6커밋(한→영 용어 번역, 구절 질의 번역·가중, book_id UNK 폴백, 권말 색인 강등), EUAT 후속 문서·FU-003 코드 |
| 양쪽에 동등한 패치 | 14개 |

## 3. 병합 충돌 예측

| 병합 | 결과 |
|---|---|
| `main` + `origin/dev/dbma-engine` | 충돌 3개: `core/candidate_generator.py`, `core/hybrid_candidate_pipeline.py`, `core/query_translation.py` |
| `main` + `feat/peb-v0.1`(로컬) | 충돌 4개: 위 3개 + `core/evidence_adapters/tsu_adapter.py` |

- `core/generation.py`는 **텍스트 충돌이 없다**(FU-003의 +27줄과 peb의 큰 변경이 자동 병합). 의미상 겹침(오염 문자 처리 방식 vs 인용 검증)은 병합 후 회귀로 확인해야 한다.
- 충돌 3개는 검색 경로이며 Retrieval Engine 소관이다. 두 번역 방식 중 무엇을 살릴지는 코드 조립이 아니라 **선택 결정**이다(둘을 합치면 이중 번역 위험).

## 4. 로컬 앱 체크아웃(`~/DBMA`)의 위험

| 항목 | 내용 |
|---|---|
| 푸시되지 않은 커밋 | `c2cdf147`(2026-09-28 "HOTFIX: 하드코딩 절대경로 제거 15곳 + 재귀 가드 테스트", 5파일). 원격 어디에도 없어 **디스크 손실 시 사라진다** |
| 미커밋 스테이징 6개 | `config.yaml`(`nae_pd.enabled` false→true), `core/candidate_generator.py`(+31), `core/hybrid_candidate_pipeline.py`(+149, "[P1 최적화] `tsu_by_id` lazy loading"), 스크립트 3개 신규 |
| 미커밋 비스테이징 5개 | `core/document_context.py`, `core/identity_registry.py`, `core/processing.py`, `scripts/grounded_synthesis_integration_demo.py` 등 |
| `incremental_state.json` | FU-002-A로 수정됨(미커밋) |

스테이징된 검색 코어 변경은 `main`의 수정을 이식한 것이 아니다(main과의 차이 154/301줄, peb HEAD와의 차이 30/134줄). 별개의 성능 최적화 작업이 진행 중인 것으로 보이며 작성 주체는 확인하지 못했다.

**EUAT 결과 해석에의 영향**: 시험 앱은 "peb + 미커밋 검색 코어 변경"이었다. 이 상태는 커밋된 어떤 브랜치와도 일치하지 않아 시험 결과를 특정 커밋으로 재현할 수 없다(결과서 환경란에 반영).

## 5. 선택지 (미실행, 사용자 결정 사항)

| 방안 | 내용 | 장점 | 위험 |
|---|---|---|---|
| I | `dev/dbma-engine`을 `main`에 병합 | 기본 브랜치가 배포 계보를 포함 | 충돌 3개(검색) 해결 필요, main의 GS·검색 수정과 dev의 번역 방식 중 선택 |
| II | `main`을 `dev/dbma-engine`에 병합 | 배포 계보 유지, GS·FU-003 유입 | 동일 충돌, dev가 릴리스 라인이므로 회귀 부담 |
| III | 선별 반영(체리픽)으로 필요한 것만 이동 | 범위 작음 | 분기가 계속 벌어짐, 동일 문제 재발 |

**권고 절차(이 조사에서는 실행하지 않음)**
1. 두 브랜치 어느 쪽도 건드리지 않는 **임시 통합 브랜치**에서 병합을 시도하고 충돌 3개를 해결한다.
2. 한국어 질의 번역은 두 방식을 같은 질의 집합(P0-5 24건 등)으로 비교해 하나를 정한다.
3. 전체 회귀와 검색 재현 확인 후 방안 I/II 중 최종 결정.

**병합 방향 자체는 릴리스 라인이 어디인지에 대한 HQ 판단이 필요하다.** 태그 계보는 `dev/dbma-engine`을 가리키지만, GitHub 기본 브랜치와 최근 PR(#90~#101)은 `main`을 가리킨다.

## 6. 즉시 필요한 보호 조치 (승인 필요, 미실행)

1. 로컬 미푸시 커밋 `c2cdf147`을 원격으로 푸시(내 작업이 아니므로 확인 후).
2. 미커밋 18개의 소유자 확인과 보존(커밋 또는 stash는 이 조사에서 하지 않음).

## 7. 이 조사가 구현 결정에 주는 영향

- ADR-036 방안 B는 `NAE/*`와 `ui/components/nae_public_section.py`가 중심이며, 이 파일들은 `main`과 `dev/dbma-engine`이 서로 충돌하지 않는다(충돌 3개에 없음). 따라서 B는 `main` 기준으로 구현해도 이후 병합이 깨끗할 것으로 예측된다.
- 다만 사용자가 실제 앱에서 보려면 `main`의 변경이 릴리스 라인에 도달해야 하므로 위 병합 결정이 선행 조건이다.
