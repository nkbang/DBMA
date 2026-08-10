# NAE Corpus Recovery Execution Report 001

**Project:** NAE-CORPUS-RECOVERY-EXECUTION-001
**작성일:** 2026-08-07
**성격:** RAW/Metadata 복원 + Canonical 재생성 — Crosswalk/TSU/Activation
전부 미수행.
**Git Commit/Push:** 미수행(add도 미수행) — 전부 미커밋 상태 유지.

---

## 1. Summary

`~/NAE_CORPUS_RAW/raw/archive_org/`(git 비추적 백업)에 있던 Dagg/
Hiscox/Fuller(8권) 10건을 `NAE/corpus/raw/archive_org/`(git 추적)로
복원하고, Registry 실측값으로 `metadata.json`을 생성한 뒤(10/10
Registry와 자동 대조 검증 완료), 기존 Canonical Generator(무수정)로
`NAE/corpus/canonical/`을 재생성했다. Validator Drift 0, Regression
304 passed(감소 없음), Crosswalk/TSU 어느 것도 생성하지 않았다.

---

## 2. Files

### 생성(신규 RAW/Canonical 데이터)

```
NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/          (원본 3파일 + metadata.json)
NAE/corpus/raw/archive_org/church_order/Hiscox_Standard_Manual/     (원본 3파일 + metadata.json)
NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol01~08/ (권당 원본 2파일 + metadata.json)
NAE/corpus/canonical/Dagg_Church_Order/                              (canonical.json/txt, normalize_report.json)
NAE/corpus/canonical/Hiscox_Standard_Manual/
NAE/corpus/canonical/Fuller_Complete_Works_Vol01~08/
docs/NAE_CORPUS_RECOVERY_EXECUTION_REPORT_001.md
```

### 변경

없음 — `NAE/pipeline/canonical/*`(Parser), `scripts/crosswalk/*`,
`resources/theological_sources/*` 전부 무수정. (`NAE/pipeline/tsu/
runner.py`의 `M` 표시는 이전 작업(NAE-TSU-PIPELINE-WIRING-
IMPLEMENTATION-001)에서 이미 만들어진 미커밋 변경이며, 이번 Recovery
작업이 만든 것이 아니다 — git 이력상 diff 없음 재확인.)

---

## 3. Phase 1 — Backup Inventory Final Verification

| 항목 | original.pdf | ocr.txt | hocr.html | metadata.json(복원 전) |
|---|---|---|---|---|
| Dagg Church Order | 있음(16.3MB) | 있음(0.7MB) | 있음(17.2MB) | 없음 |
| Hiscox Standard Manual | 있음(10.9MB) | 있음(0.2MB) | 있음(5.2MB) | 없음 |
| Fuller Vol01~08(8권) | 있음(권당) | 있음(권당) | **없음**(전권) | 없음(전권) |

---

## 4. Phase 2 — RAW Recovery

```
복원 대상: NAE/corpus/raw/archive_org/{church_order,missions}/
복원 원본: ~/NAE_CORPUS_RAW/raw/archive_org/{church_order,missions}/
```

기존 디렉토리 구조(`church_order/`, `missions/` 하위 identifier명)
그대로 유지, identifier/파일명 변경 없음. 체크섬 대조(원본 3건
샘플: Dagg/Hiscox/Fuller-Vol01 `original.pdf`) 전부 일치 확인.

---

## 5. Phase 3 — Metadata Recovery(Q3)

10건 전부 Registry 실측값(`authors.yaml`/`works.yaml`/
`editions.yaml`/`volumes.yaml`/`sources.yaml`)만 사용해 `metadata.json`
생성 — **추측 없음.** 생성 직후 Registry와 자동 교차 검증(스크립트로
`publisher`/`publication_place`/`creator`/`work_id`/`edition_id` 5개
필드 전부 대조):

```
BAP-CHURCH-DAGG-001: OK
BAP-CHURCH-HISCOX: OK
BAP-MISS-FULLER-VOL01~08: OK(8건)

MISMATCHES: none
```

**10/10 일치.**

---

## 6. Phase 4 — Canonical Regeneration

```
$ git diff --stat NAE/pipeline/canonical/
(출력 없음 — Parser 무수정 확인)
```

기존 `NAE/pipeline/canonical/pipeline.py::normalize_item()`을 그대로
호출해 10건 전부 생성:

```
Dagg_Church_Order:            OK (source=hocr, page_count=314)
Hiscox_Standard_Manual:       OK (source=hocr, page_count=192)
Fuller_Complete_Works_Vol01~08: OK (source=ocr, page_count=1, 8건 전부)
```

**전건 성공(status="ok").** 단, Fuller 8권은 `hocr.html`이 없어
`ocr.txt`(form-feed 페이지 구분 없음)로 폴백 처리됐다 — extract.py
자체 docstring이 경고하는 대로 `page_count=1`로 뭉쳐 처리됐고, 헤더/
푸터/페이지번호 제거 등 페이지 단위 휴리스틱이 온전히 작동하지
않았을 가능성이 있다(§10 WARNING). Dagg/Hiscox는 `hocr.html`이 있어
정상적으로 다중 페이지(314/192)로 처리됐다.

---

## 7. Phase 5 — Validation

```
source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## 8. Phase 6 — Regression

```
$ pytest tests/test_crosswalk*.py tests/test_tsu_pipeline_wiring.py \
         tests/test_source_validator_v2.py tests/test_validator_v22.py \
         tests/test_manifest_validator.py tests/test_authority_validator.py \
         tests/test_authority_validator_canonical.py tests/test_migration_lock.py \
         tests/test_migration_checkpoint.py tests/test_migration_engine.py \
         tests/test_registry_adapter.py tests/test_manifest_adapter.py \
         tests/test_pilot_executor.py tests/test_comment_preservation.py -q
304 passed(직전 baseline과 동일, 감소 없음)
```

전체 프로젝트 테스트 스위트(1700여 개)도 별도로 백그라운드 실행 —
이전 세션들과 동일하게 `tests/test_nae_embed.py`의 사전 존재 실패
2건(이번 작업과 무관) 외에는 전부 통과할 것으로 예상되며, 결과는
확인되는 대로 별도 공유한다.

---

## 9. Phase 7 — Architecture Audit

```
$ git status --short core/ scripts/adapters/ scripts/migration_engine.py \
    scripts/crosswalk/tsu_gate.py scripts/crosswalk/resolver.py \
    scripts/crosswalk/storage/yaml_repository.py NAE/pipeline/tsu/builder.py \
    NAE/pipeline/canonical docs/architecture/ resources/theological_sources/
 M NAE/pipeline/tsu/runner.py   ← 이전 작업(Wiring)에서 이미 존재하던 미커밋 변경, 이번 Recovery가 만든 것 아님
?? scripts/crosswalk/resolver.py    ← 이전 작업에서 이미 존재하던 미커밋 파일(내용 무변경)
?? scripts/crosswalk/tsu_gate.py    ← 동일
```

`core/`, `scripts/adapters/`, `scripts/migration_engine.py`,
`NAE/pipeline/canonical/`(Parser), `docs/architecture/`,
`resources/theological_sources/` — **이번 Recovery로 인한 변경
0건.** `crosswalk_id` 레코드 여전히 0건, `NAE/corpus/tsu/`도
`.gitkeep`만 존재(TSU 생성 0건).

---

## Required Questions

| 질문 | 답변 |
|---|---|
| Q1. Recovery 대상이 모두 정상 복원되었는가? | **예.** 10건(Dagg 1 + Hiscox 1 + Fuller 8) 전부 `NAE/corpus/raw/archive_org/`로 복원, 체크섬 대조 확인. |
| Q2. Canonical이 정상 생성되었는가? | **예.** 10건 전부 `status="ok"` — 단 Fuller 8권은 hocr 부재로 `page_count=1`(품질 저하 가능성, §6 WARNING). |
| Q3. metadata.json이 Registry와 일치하는가? | **예, 10/10, 자동 대조로 확인.** 추측 없이 Registry 실측값만 사용. |
| Q4. Validator Drift는 0인가? | **예.** 89/0/0, 138/0/0, 128/26/0 전부 baseline 일치. |
| Q5. Regression 감소는 없는가? | **없음.** 304 passed, 감소 없음(전체 스위트는 백그라운드 확인 중). |
| Q6. Crosswalk 생성은 수행하지 않았는가? | **예, 0건.** `crosswalk.yaml` records 여전히 0. |
| Q7. TSU는 생성되지 않았는가? | **예, 0건.** `NAE/corpus/tsu/`에 `.gitkeep` 외 파일 없음. |
| Q8. 다음 단계(Manual Crosswalk Population)를 수행할 준비가 되었는가? | **예, 조건부.** Source Evidence + File Evidence를 이제 갖춘 진짜 후보(예: `BAP-CHURCH-DAGG-001` ↔ `Dagg_Church_Order`)가 최초로 저장소 안에 존재한다 — 단 Fuller 8권은 canonical 품질 저하(page_count=1) 가능성이 있어, Candidate로 쓰기 전 재확인을 권고(§6). |

---

## 완료 보고

```
STATUS: COMPLETE (RAW/metadata recovery + canonical regeneration only — no Crosswalk/TSU/Activation)

FILES CREATED:
NAE/corpus/raw/archive_org/church_order/{Dagg_Church_Order,Hiscox_Standard_Manual}/(원본+metadata.json)
NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol01~08/(원본+metadata.json)
NAE/corpus/canonical/{Dagg_Church_Order,Hiscox_Standard_Manual,Fuller_Complete_Works_Vol01~08}/
docs/NAE_CORPUS_RECOVERY_EXECUTION_REPORT_001.md

FILES MODIFIED:
(없음 — 이번 작업으로 인한 수정 0건)

RAW RECOVERY:
10/10 복원 완료, 체크섬 대조 일치(샘플 3건)

CANONICAL:
10/10 생성 완료(status=ok). Dagg/Hiscox는 hocr 기반 정상 품질(314/192 페이지). Fuller 8권은 hocr 부재로 ocr 폴백 처리(page_count=1, 품질 저하 가능성)

METADATA:
10/10 생성, Registry와 자동 대조 검증 100% 일치(publisher/publication_place/creator/work_id/edition_id 5개 필드)

VALIDATOR:
source 89/0/0, manifest 138/0/0, authority 128/26/0 — 전부 baseline 일치

REGRESSION:
304 passed(핵심 회귀 스위트, 감소 없음). 전체 프로젝트 스위트는 백그라운드 실행 중, 결과 확인되는 대로 별도 보고

ARCHITECTURE AUDIT:
PASS — core/, scripts/adapters/, scripts/migration_engine.py, NAE/pipeline/canonical/(Parser), docs/architecture/, resources/theological_sources/ 전부 무변경. Crosswalk 0건, TSU 0건 유지

BLOCKER:
0

WARNING:
1 (Fuller Complete Works 8권 전부 hocr.html 부재로 canonical page_count=1 — 페이지 단위 구조 정리 휴리스틱이 온전히 작동하지 않았을 가능성. Manual Crosswalk 후보로 쓰기 전 canonical.txt 품질 육안 확인 권고)

NEXT STEP:
Manual Crosswalk Population 재개 — 이번에 확보된 실제 File+Source Evidence(Dagg/Hiscox/Fuller 10건)를 근거로 Pilot 1건(우선 Dagg 또는 Hiscox 권장, hocr 기반이라 품질 확실) manual-confirmed 레코드 생성 시도

GIT:
NOT PERFORMED(add 포함 전부 미수행 — 워킹트리에만 존재)
```
