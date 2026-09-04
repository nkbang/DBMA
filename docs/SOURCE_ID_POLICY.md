# Source ID Policy — NAE-SOURCE-DEDUP-001

작성일: 2026-07-31

## 원칙

**하나의 원문 = 하나의 canonical source_id.** 동일한 실제 문서를 가리키는 source_id가 시간이 지나며 여러 개 생겨도, 기존 ID는 **삭제하지 않고 alias로 보존**한다 — 기존 DBMA 문서 lineage(어떤 리포트/작업이 어떤 ID로 그 문서를 다뤘는지)는 감사(audit) 목적으로 항상 추적 가능해야 한다.

## 조사 — 현재 중복 source 목록

`docs/`, `resources/`, `data/` 전체를 대상으로 source_id 성격의 식별자를 grep한 결과, 중복은 **1건**만 발견됨:

| 문서 | ID 체계 A | ID 체계 B | 최초 사용 시점/맥락 |
|---|---|---|---|
| The New Hampshire Confession of Faith (1833) | `baptist-confession-001` | `NHBC1833` | A: STEP4 Pilot 단계에서 CUE가 NAE_SOURCE_SCHEMA_v1.md의 원 제안 포맷(`{denomination}-{genre}-{sequence}`)에 따라 채번(`STEP4_PILOT_SOURCE_ENTRY.md`, `STEP5_SOURCE_REGISTRY_ENTRY.md` 등 7개 문서에서 사용). B: NAE-SOURCE-003 단계에서 C1이 작성한 `source_candidates.csv`(및 이를 변환한 `source_manifest.yaml`)의 짧은 코드 포맷으로 등장 |

다른 6건(SLBC1689/PBC1742/TH1612/JS1608/AF1815/BFM2000)은 이번이 최초 등장이라 중복 없음. `data/nae/metadata/`는 비어 있어(`.gitkeep`만 존재) registry 레벨의 실제 중복 등록은 없음 — 이번 중복은 순수하게 **문서/manifest 레벨**에서만 발생했다.

## 결정 — Canonical source_id

**`NHBC1833`을 canonical id로 지정한다.**

근거:
1. `NHBC1833`은 `source_manifest.yaml`(스키마 검증을 통과한 살아있는 등록소, `scripts/source_validator.py` PASS 확인됨)에 실제로 등록된 형식이며, 나머지 6건의 Baptist 자료(SLBC1689 등)와 **일관된 명명 체계**를 이룬다 — 향후 자료가 늘어날수록 짧은 코드 체계가 실무적으로 유지보수하기 쉽다.
2. `baptist-confession-001`은 STEP4 시점의 제안 포맷이었을 뿐, 실제 등록소(manifest)에 반영된 적이 없다 — 문서(리포트) 안에서만 존재했던 임시 식별자에 가깝다.
3. 다만 `baptist-confession-001`은 7개의 기존 STEP4/STEP5 리포트에서 이미 사용되었으므로, 그 기록들의 정확성(lineage)을 위해 **삭제·수정하지 않고 alias로 보존**한다.

## 기록 — 조치 내역

- `resources/theological_sources/source_manifest.schema.yaml`을 v1.1 → **v1.2**로 갱신: `aliases: array[string]` (optional) 필드 추가
- `resources/theological_sources/baptist/source_manifest.yaml`의 `NHBC1833` 항목에 `aliases: [baptist-confession-001]` 추가, notes에 dedup 결정 근거 기록
- 기존 STEP4/STEP5 리포트 7건(`docs/tasks/reports/STEP4_PILOT_SOURCE_ENTRY.md`, `STEP5_SOURCE_REGISTRY_ENTRY.md`, `NAE_SOURCE_SCHEMA_v1.md`, `NAE_SOURCE_REGISTRY_SCHEMA_v1.md`, `STEP5_SOURCE_ACQUISITION_RECORD.md`, `STEP5_HUMAN_ACQUISITION_GUIDE.md`, `docs/NAE_SOURCE_REGISTRY_REPORT.md`)는 **수정하지 않음** — `baptist-confession-001` 표기 그대로 유지, 원칙에 따른 의도적 보존
- `scripts/source_validator.py`로 재검증 — PASS=21, WARNING=0, FAIL=0 유지 확인(aliases 필드는 optional이라 기존 검사 로직에 영향 없음)

## 향후 신규 등록 규칙

1. 새 문서를 manifest에 등록하기 전, 반드시 `docs/SOURCE_ID_POLICY.md`(본 문서)와 기존 `source_manifest.yaml`을 확인해 동일 원문이 이미 다른 ID로 존재하는지 확인한다.
2. 중복이 발견되면, **먼저 등록된 것이 아니라 더 널리 쓰이고 있는(또는 더 활성 상태인 등록소에 실제로 존재하는) ID를 canonical로 우선 고려**하되, 사례별로 판단한다(이번 사례가 정확히 그 기준을 따름).
3. Canonical로 채택되지 않은 기존 ID는 canonical 항목의 `aliases` 배열에 추가한다 — 어디에서도 삭제하지 않는다.
4. `source_validator.py`의 source_id 중복 검사는 **`source_id` 필드만** 검사하며 `aliases`는 검사 대상이 아니다 — 향후 동일 alias가 서로 다른 canonical 문서에 중복 배정되는 것을 막는 자동 검사는 아직 없음(사람이 본 정책 문서 기준으로 관리). 필요성이 커지면 `scripts/source_validator.py`에 alias 중복 검사를 추가하는 것을 향후 과제로 남긴다.

## 향후 과제 (이번 범위 밖)

- `scripts/source_validator.py`에 alias 교차 중복 검사 추가 여부
- `NAE_SOURCE_SCHEMA_v1.md`/`NAE_SOURCE_REGISTRY_SCHEMA_v1.md`(STEP2/STEP4-A 산출물)의 원 제안 포맷(`{denomination}-{genre}-{sequence}`)을 완전히 폐기할지, 혹은 `source_manifest.yaml`의 짧은 코드 체계와 병행 허용할지 — 이번 정책은 "기존 발생한 충돌 1건의 해소"만 다루며, 명명 규칙 전체의 최종 통일은 별도 결정 필요
