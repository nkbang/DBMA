# NAE Authority Validator Implementation Report 001

**Project:** NAE-AUTHORITY-VALIDATOR-IMPLEMENTATION-001
**Date:** 2026-08-03
**Nature:** Validator 코드 구현(Registry 전담) — Migration 아님
**Git Commit/Push:** 미수행 — 사용자 승인 대기

---

## 0. TSU_ELIGIBLE 모순 확인(선결 사항)

CUE(`verified`, READY 10/10)와 C1 리뷰(`validated`, tsu_eligible=false
"적절")는 **모순이 아니라 시점 차이**다. `NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md`
가 이미 `metadata_status` 정본 enum을 `verified`로 정의했고(설계 시점),
Pilot 데이터를 처음 만들 때 실수로 `validated`를 썼다(구현 시점 결함) —
C1은 그 결함이 있던 **정규화 이전** 데이터를 검토했고, 그 시점 기준으로는
C1의 "`tsu_eligible=false`가 적절하다"는 판단이 옳았다. 이후
`NAE-MANIFEST-PILOT-LIFECYCLE-NORMALIZATION-001`(커밋 `a8e4581`)에서
`validated→verified` 등 3개 필드를 정본 enum에 맞게 실제로 고쳤고,
그 결과 10/10 READY가 됐다 — **두 보고서 모두 각자 검토한 시점의 데이터
기준으로는 옳았다.** "최신 정본"은 처음부터 `verified`였고(Schema
Design v1), 어긋났던 쪽은 정본이 아니라 Pilot 실データ였다.

---

## 1. Executive Summary

`scripts/authority_validator.py`를 신규 구현해 Production Authority
Registry(`authority/{authors,works,editions,volumes,sources}.yaml`)를
검증했다. 8개 검사 항목(FK Integrity, Duplicate IDs, Legacy Alias,
Canonical ID, Broken Reference, Orphan Entity, Circular Reference,
Duplicate Canonical Name) 전부 구현·테스트했다. 실제 Registry 실행
결과 **FAIL 0건** — 단 ID Governance v1이 이미 알고 있던 비표준 ID
26건이 WARNING으로 재확인됐다(신규 발견 아님, 기존 결정과 일치).
신규 테스트 17개 전부 PASS, 3개 Validator(source/manifest/authority)
전체 회귀 확인 완료 — 이것으로 **3-Validator 체계
(source_validator.py/manifest_validator.py/authority_validator.py)가
전부 구현됐다.**

---

## 2. 구현 내용

`scripts/authority_validator.py` — `--registry-path`(기본:
`resources/theological_sources/authority`) 1개 인자.

| # | 검사 | 방식 |
|---|---|---|
| 1 | FK Integrity | `work.author_id`/`edition.work_id`/`volume.edition_id`/`source.edition_id`/`source.volume_id` 5개 엣지, 상위 entity 존재 확인 |
| 2 | Duplicate IDs | 각 entity 파일 내 ID 유일성(5개 파일) |
| 3 | Legacy Alias | alias가 다른 author의 canonical ID와 충돌하는지 + 두 author가 동일 alias를 공유하는지 |
| 4 | Canonical ID Format | ADR-017(lowercase snake_case) 준수 여부 — **WARNING만**(ID Governance v1이 즉시 rename을 보류하기로 이미 결정) |
| 5 | Broken References | FK Integrity와 동일 로직(#1), 메시지에 "Broken Reference" 명시로 구분 표시 |
| 6 | Orphan Entity | 어느 하위 entity에서도 참조되지 않는 Author/Work/Edition — WARNING |
| 7 | Circular Reference | `Work.continues_work_id` 체인의 순환(ADR-018) — 자체 구현 그래프 순환 탐지 |
| 8 | Duplicate Canonical Name | 서로 다른 author_id가 정규화된 동일 `canonical_name`을 가지면 WARNING(자동 병합은 하지 않음) |

`tests/test_authority_validator.py` — 17개 테스트(정상 1, FK 오류 3,
중복 ID 2, Legacy Alias 2, Canonical ID 2, Orphan 1, Circular
Reference 3, Duplicate Name 1, 실제 Production Registry 회귀 2).

---

## 3. 완료 조건 답변

### PASS/FAIL

```
authority_validator.py --registry-path resources/theological_sources/authority
=== 결과 요약: PASS=74 WARNING=26 FAIL=0 ===
```

**FAIL 0건.** WARNING 26건은 전부 Canonical ID Format 불일치(§4번
검사) — `FULLER-ANDREW-001`류 6개 entity 그룹(author 1 + work 3 +
edition 4 + volume 8 + source 10 = 26)이 ADR-017 표기와 다르다는,
**이미 ID Governance v1에서 알려진 사실의 재확인**이다(신규 결함
아님).

### Coverage

8개 요구 검사 항목 전부 구현 + 테스트로 커버(각 항목 최소 1개 이상
정상/실패 케이스). 실제 Production Registry(3 author/3 work/4
edition/8 volume/10 source)에 대해서도 전 항목 실행 확인.

### Regression

```
source_validator.py --root .../baptist   : 21 PASS / 0 WARNING / 0 FAIL (불변)
source_validator.py --root .(전체)         : 89 PASS / 0 WARNING / 0 FAIL (불변)
manifest_validator.py(Pilot 10건)           : 138 PASS / 0 WARNING / 0 FAIL (불변, 10/10 READY 유지)
authority_validator.py(Production Registry)  : 74 PASS / 26 WARNING / 0 FAIL (신규)

tests/test_source_validator_v2.py   15 passed
tests/test_validator_v22.py          19 passed
tests/test_manifest_validator.py     15 passed
tests/test_authority_validator.py    17 passed
합계                                  66 passed, 0 failed
```

기존 두 Validator는 이번 작업에서 **한 글자도 수정하지 않았다**(git
diff 없음).

### Remaining Risk

| # | 리스크 | 설명 |
|---|---|---|
| 1 | Canonical ID Format WARNING 26건 미해결 | ID Governance v1이 이미 "변경 필요, 실제 rename은 별도 승인"으로 분류해 둔 항목 — 이번 검증으로 범위(26건, 전체 Registry의 정확히 몇 %인지)가 정량 확인됨 |
| 2 | `_WORK_TYPE_FIELD_RULES`가 `source_validator.py`/`manifest_validator.py`/이번 `authority_validator.py`에는 **없음**(이번 도구는 work_type 조건부 규칙을 다루지 않음 — Registry 레벨 FK만 검사, work_type 규칙은 다른 두 도구의 책임으로 명확히 분리) | 의도된 설계, 위험 아님 — 명시적으로 기록만 |
| 3 | Duplicate Canonical Name 검사가 author만 대상 | Work의 `canonical_title` 중복 검사는 이번 구현 범위 밖(명령서가 Author 중심으로 지시) — 향후 확장 후보 |
| 4 | Circular Reference 검사가 `continues_work_id` 단일 체인만 대상 | 다른 순환 가능성(예: Edition↔Work 상호 참조 등 FK 구조상 원천적으로 불가능한 경우는 제외)은 검토 범위 밖 |

---

## 4. Migration Readiness

**BLOCKED 여전히 유지.** 3-Validator 체계는 완성됐으나, ID Governance
WARNING 26건 미해결, Manifest Layer가 여전히 Pilot 범위(10건)뿐,
Baptist Missionary Magazine(Periodical) Manifest 미생성 등 이전
보고서들이 남긴 조건이 그대로 남아 있다.

---

## 로드맵 갱신

```
Architecture (ADR-014~019)     ✅
Schema v2.2                    ✅
Authority Registry             ✅
Source Validator                ✅
Manifest Validator               ✅
Manifest Pilot                    ✅
Manifest Pilot Lifecycle 정규화     ✅
Authority Validator                 ✅ (이번 작업)

NAE-AUTHORITY-VALIDATOR-REVIEW-001(C1 독립 검증)   NEXT
Metadata Migration Readiness Review                  FUTURE
```

---

*RAW, Manifest, Corpus Manifest, TSU, Embedding, Retrieval, Migration
— 전부 수행하지 않음. Git Commit/Push는 사용자 승인 후에만 수행한다.*
