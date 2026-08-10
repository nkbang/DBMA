# NAE Source Registry Report — NAE-SOURCE-003

작성일: 2026-07-31
입력: `resources/theological_sources/baptist/source_candidates.csv`
산출: `resources/theological_sources/baptist/source_manifest.yaml`

## 1. Manifest 생성 결과

7건 등록 완료 — `scripts/source_validator.py` 실행 결과 **PASS=21, WARNING=0, FAIL=0**.

| source_id | status | license | content_genre |
|---|---|---|---|
| SLBC1689 | `approved_for_acquisition` | public_domain_original | confession |
| PBC1742 | `approved_for_acquisition` | public_domain_original | confession |
| NHBC1833 | `approved_for_acquisition` | public_domain_original | confession |
| TH1612 | `approved_for_acquisition` | public_domain_original | theology |
| AF1815 | `approved_for_acquisition` | public_domain_original | theology |
| BFM2000 | `permission_required` | copyright_restricted | confession |
| JS1608 | `verification_pending` | unknown (아래 참고) | history, church_practice |

원문 다운로드는 수행하지 않음 — 전 항목 `local_path: null`.

### 스키마/검증 스크립트 갱신

- `resources/theological_sources/source_manifest.schema.yaml`을 v1.0 → **v1.1**로 갱신: `tradition`/`theological_category` 필드 추가, `status` enum에 `approved_for_acquisition`/`permission_required`/`verification_pending` 3개 값 추가(기존 PREPARED/ACQUIRED/VERIFIED/INGESTED와 병존)
- `scripts/source_validator.py`의 `_VALID_STATUSES` 상수가 구버전(4개 값)이라 새 manifest가 전부 FAIL로 나오는 것을 발견 — 스키마 v1.1 기준으로 7개 값으로 갱신, 재검증 시 전체 PASS 확인

## 2. Metadata 검토

### tradition 매핑 (판단 필요했던 부분)

작업 지시의 3분류(`Particular Baptist`/`American Baptist`/`Baptist Evangelical`)는 CSV 원본의 `tradition` 컬럼(`Baptist (Second London)`, `Baptist (Reformed)` 등)과 1:1로 대응하지 않아 **신학사적 판단을 거쳐 배정**했습니다. 각 manifest 항목의 `notes`에 근거를 남겼으며, 요약:

- **SLBC1689 → Particular Baptist**: 영국 Particular(칼빈주의) 침례교의 대표 신앙고백 원문 자체 — 판단 여지 적음
- **PBC1742 → American Baptist**: 신학적으로는 SLBC1689와 거의 동일(Particular Baptist 계열)이나, "미국 최초의 독자적 침례교 연합 신앙고백"이라는 역사적 지위를 기준으로 분류 — **지리/역사 축과 신학 축이 섞인 판단이라 HQ 재검토 여지 있음**
- **NHBC1833 → American Baptist**: 미국 북부/서부에서 널리 채택, 이견 적음
- **TH1612 → Baptist Evangelical**: General(초기 아르미니안) Baptist 창시자 — 세 분류 중 Particular/American 어디에도 정확히 속하지 않아 나머지 선택지로 배정 (가장 불확실한 매핑)
- **AF1815 → Particular Baptist**: CSV 원표기가 "Baptist (Particular/Revival)"이므로 신학 계열(Particular) 기준 채택, 부흥/선교 측면은 `theological_category=[missions]`로 별도 반영
- **BFM2000 → American Baptist**: NHBC1833 계열의 현대화 문서라는 역사적 연속성 기준

**권장**: 이 3분류 체계 자체가 지리(American)/신학(Particular)/시대·성향(Evangelical) 축을 혼합하고 있어 구조적으로 상호배타적이지 않습니다. 이후 자료가 늘어나면 재정의가 필요할 수 있습니다.

### theological_category 배정

`content_genre`(문서 형식)와 별개 축으로, 각 문서의 실제 신학적 초점을 기준으로 배정했습니다. 신앙고백서 4건(SLBC1689/PBC1742/NHBC1833/BFM2000)은 `confession`을 공통 포함하되, 조항 구성에 따라 `ecclesiology`/`soteriology`를 추가 배정. 논고류(TH1612/AF1815)는 confession 태그를 부여하지 않고 주제 중심으로 배정(TH1612=ecclesiology[종교자유/정교분리], AF1815=soteriology+missions[Fullerism/현대선교 신학]).

### 데이터 품질 이슈 (CSV 자체)

- `source_candidates.csv`가 인용부호 없는 CSV이며, `SLBC1689`/`NHBC1833`의 `notes` 필드에 이스케이프되지 않은 쉼표가 있어 `csv.DictReader` 기준 초과 필드가 발생(내용 손실은 없음, notes 텍스트만 분할됨 — 무해)
- **`JS1608` 행은 심각합니다**: `language` 값 뒤에 `Dutch`라는 이스케이프되지 않은 추가 토큰이 있어 그 이후 모든 컬럼(license/availability/source_location/priority)이 한 칸씩 밀려 파싱됩니다. 원시 파일의 `license` 위치에는 사실 "Dutch"가, 실제 라이선스 값으로 보이는 "public_domain_possible"은 `availability` 위치로 밀려 들어와 있습니다.
  - 이 manifest에서는 밀린 값을 그대로 신뢰하지 않고 `license: unknown`으로 **보수적으로 기록**했습니다(추정값 "public_domain_possible"을 확정값으로 쓰지 않음).
  - CSV 자체의 `notes`에도 "Author died 1630. Verify Dutch copyright law (life + 70 years = 1700)"라는 미해결 저작권 질문이 있어, 데이터 정합성 문제와 무관하게 어차피 `verification_pending` 대상이었습니다.
  - **권장**: `source_candidates.csv`의 JS1608 행을 쉼표 이스케이프(따옴표 처리) 형태로 수정한 뒤 재확인 필요.

### 기존 산출물과의 source_id 불일치

`NHBC1833`은 이전 STEP5 계열 문서(`docs/tasks/reports/STEP5_SOURCE_REGISTRY_ENTRY.md` 등)에서 이미 `source_id: baptist-confession-001`로 다뤄진 동일 문서입니다. 이번 manifest는 CSV가 지정한 짧은 코드(`NHBC1833`)를 그대로 사용했습니다 — **두 source_id 체계가 병존**하게 되었으므로, 향후 통합 여부(또는 별칭 매핑) 결정이 필요합니다.

## 3. 다음 RAW acquisition 준비 상태

| 항목 | 상태 |
|---|---|
| Manifest 등록 | 완료 (7건, validator PASS) |
| 원문 확보(다운로드) | **미실행** — `approved_for_acquisition` 5건 모두 `local_path: null` |
| BFM2000 | 확보 보류 — SBC/Ligonier 등 권리 보유자 허가 검토 선행 필요 |
| JS1608 | 확보 보류 — CSV 데이터 정합성 수정 + 저작권(네덜란드법) 확인 선행 필요 |
| 도구 한계 | STEP5-B에서 확인된 `WebFetch` verbatim 확보 불가 문제([STEP5_SOURCE_COMPARISON.md](tasks/reports/STEP5_SOURCE_COMPARISON.md)) 동일하게 적용 — 5건 확보 시에도 사람이 직접 확보하는 절차([STEP5_HUMAN_ACQUISITION_GUIDE.md](tasks/reports/STEP5_HUMAN_ACQUISITION_GUIDE.md) 방식) 필요 |

**다음 단계 제안**: `approved_for_acquisition` 5건 중 우선순위(CSV `priority` 기준 P0 3건: SLBC1689/PBC1742/NHBC1833)부터 STEP5_HUMAN_ACQUISITION_GUIDE.md 절차로 사람이 직접 확보 → `scripts/source_validator.py`로 재검증 → `status: ACQUIRED`로 전환(STEP5_REGISTRY_TRANSITION.md 절차 재사용).
