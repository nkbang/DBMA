# NAE Periodical TSU Field Readiness Report 001

작성일: 2026-08-02
Project: NAE-PERIODICAL-CONDITION-RESOLUTION-001 Phase 1
목적: C1 Review-002 BLOCKER("TSU 필요 필드 확인") 해소
성격: **검증(읽기 전용)** — TSU 생성/스키마 변경 없음

---

## 1. 확인 자료

실측 대상(전부 읽기 전용 조회):

```
resources/theological_sources/authority/*.yaml          (Production Registry)
resources/theological_sources/authority/pilot/*          (Pilot-001, church_order)
resources/theological_sources/authority/pilot/fuller/*    (Pilot-002, Fuller)
resources/theological_sources/authority/pilot_periodical/* (Periodical Pilot)
resources/theological_sources/modern/                     (Production corpus manifest 위치)
resources/theological_sources/baptist/source_manifest.yaml (v1.2)
```

---

## 2. Monograph 필수 필드 확인

요구: `edition_id`, `source_id`, `work_id`, `author_id`

| 계층 | 위치 | 확인 결과 |
|---|---|---|
| Registry(authority/*.yaml, Production) | `sources.yaml`에 `edition_id`/`source_id` 직접 존재. `work_id`/`author_id`는 `edition_id → editions.work_id → works.author_id` 체인으로 유도 가능(FK, Registry Build-001 §Phase4에서 14/14 참조 무결성 PASS 확인됨) | **필드 존재(직접+유도) — PASS** |
| **TSU 소비용 corpus manifest**(`resources/theological_sources/modern/{category}/source_manifest.yaml`) | **존재하지 않음** — `modern/` 하위에는 스키마 파일(`source_manifest.schema.yaml`)만 있고, church_order/missions 카테고리 디렉토리 자체가 생성되지 않음(실측: `find resources/theological_sources/modern -type f` → 스키마 파일 1개뿐) | **FAIL — Production 레벨에서 TSU 입력 자체가 없음** |
| Pilot-level manifest(`authority/pilot/source_manifest.yaml`, `authority/pilot/fuller/source_manifest.yaml`) | `edition_id`/`source_id`/`author_id`/`work_id` 전부 flat 필드로 존재(Pilot Manifest Fix-001에서 확인 완료, validator 실행 결과 68 PASS/0 FAIL) + `citation_policy`/`tsu_access`도 존재 | **PASS(Pilot 범위 한정)** |

**Monograph 결론**: **Pilot 데이터는 TSU 필드를 전부 갖췄으나, Production
corpus manifest(`modern/`)에는 아직 어떤 자료도 승격되지 않았다** —
TSU를 실제로 생성하려면 Pilot 범위(Dagg/Hiscox/Fuller 10건)에 한해서만
가능하고, 그 이상(전체 Corpus)은 Production manifest 자체가 없어 불가능.

---

## 3. Periodical 필수 필드 확인

요구: `work_id`, `volume_id`, `issue_id`, `source_id`

| 계층 | 위치 | 확인 결과 |
|---|---|---|
| Registry(`authority/pilot_periodical/sources.yaml`) | `source_id`/`issue_id`는 flat 존재. `volume_id`는 **flat 필드 없음** — `issue_id → issues.volume_id` 체인으로만 유도 가능. `work_id`는 `issue_id → issues.volume_id → volumes.periodical_id`(=work_id 동등물) 체인으로 2단계 더 유도해야 함 | **필드 존재하나 유도 경로가 monograph보다 1단계 더 깊음 — WARNING** |
| **TSU 소비용 corpus manifest** | **존재하지 않음** — 게다가 Registry Design v1 §2.5 원칙(Registry Source는 `citation_policy`/`tsu_access` 등 TSU 필드를 의도적으로 갖지 않음)에 따라, Periodical Pilot은 애초에 **corpus manifest 계층 자체를 만들지 않았다**(Pilot-001/002와 다른 점 — 그쪽은 `source_manifest.yaml`을 별도로 만들었으나 Periodical Pilot Report-001/Design v1 어디에도 corpus manifest 생성이 포함되지 않았음, 실측 확인) | **FAIL — TSU 입력 계층이 아예 없음, Pilot-001/002보다 진행도가 낮음** |

**Periodical 결론**: Registry 계층(Author/Work/Volume/Issue/Source)은
구축됐으나, **실제 TSU가 읽을 corpus manifest 계층이 단 한 건도
만들어지지 않았다** — monograph Pilot 대비 진행도가 한 단계 뒤처져
있다(신규 발견, C1 Review-002에는 명시적으로 지적되지 않았던 사항).

---

## 4. 부족 필드 종합

| 항목 | Monograph | Periodical |
|---|---|---|
| Registry 필드 완비 | PASS | WARNING(유도 경로 깊음) |
| Production corpus manifest 존재 | **FAIL** | **FAIL** |
| Pilot corpus manifest 존재(TSU 필드 포함) | PASS(Dagg/Hiscox/Fuller 10건) | **FAIL(전무)** |

---

## 5. Migration 전 보완 필요 여부

**예, 필요하다.** 구체적으로:

1. Periodical Pilot에도 Pilot-001/002와 동일한 성격의
   `source_manifest.yaml`(corpus manifest, `citation_policy`/`tsu_access`
   포함)을 별도로 만들어야 TSU 생성이 가능한 상태가 된다 — 현재는
   Registry만으로는 TSU를 생성할 수 없다(구조적으로 불가능, Registry
   Design v1 §2.5의 의도된 역할 분리 때문).
2. Monograph/Periodical 공통으로, `modern/` 하위에 실제 카테고리
   디렉토리와 Production manifest가 하나도 없어 **전체 Corpus는 물론
   Pilot 범위를 벗어난 어떤 자료도 TSU 생성이 불가능**하다.

**C1 BLOCKER("TSU 필요 필드 확인") 해소 여부**: **부분 해소** — 필드
"정의"는 확인됐으나(§2/§3), 실제 "데이터 존재" 기준으로는 Periodical
쪽에 신규 gap이 발견되어 **BLOCKER는 완전히 해소되지 않았다**(§6
최종 보고서에서 재확인).
