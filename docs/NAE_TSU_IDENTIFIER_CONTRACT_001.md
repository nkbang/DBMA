# NAE TSU Identifier Contract 001

**Project:** NAE-IDENTIFIER-CROSSWALK-DESIGN-001 Phase 5
**작성일:** 2026-08-05
**성격:** Interface 정의만 — 구현 금지. `NAE/pipeline/tsu/` 코드
무수정.

---

## 1. 현재 구조(재확인)

```
Manifest(TSU_ELIGIBLE 계산은 되지만 아무도 소비하지 않음)
    │
    │  (연결 없음 — NAE_TSU_PIPELINE_PREFLIGHT_REPORT_001.md §Phase1/3 확인)
    ▼
TSU Builder(canonical_root.iterdir()로 직접 identifier 열거)
```

## 2. 변경 제안 구조

```
Manifest
    │
    ▼
Crosswalk Resolver(신규 — 이번 Task는 인터페이스만 정의, 구현 없음)
    │
    ▼
TSU Builder(기존 로직 재사용 — parser.py/claim.py 등 무수정)
```

`Crosswalk Resolver`는 "Manifest entry 목록 → TSU Builder가 처리할
identifier 목록"으로 변환하는 단일 책임만 갖는다. 위치는
`NAE/pipeline/tsu/builder.py::build_tsu_for_all`이 지금
`canonical_root.iterdir()`를 호출하는 지점을 대체하는 것으로 상정한다
(그 함수 내부의 나머지 로직 — claim 추출, TSU 레코드 생성 — 은
전혀 건드리지 않는다).

---

## 3. 필수 전달값(Resolver → Builder)

```yaml
source_id: string        # Registry/Manifest 정본 FK(Option B 불변값)
canonical_id: string     # ADR-017 canonical 표기(참조용, Builder가 TSU 레코드에 기록할 수 있음)
legacy_id: array[string] # 참조용(선택)
crosswalk_id: string     # 이 대응 관계 자체의 식별자(Audit 추적용)
schema_version: string   # Manifest schema version(현재 v2.2.x) — TSU 레코드의 tsu_schema_version과는 별개 필드로 병기(§Contract Design 001에서 이미 두 버전 축이 독립적임을 확인)
```

이 5개 필드가 채워진 항목만 `identifier`(기존 TSU Builder가 기대하는
`canonical_root`/`raw_root` 조회 키)로 변환되어 `build_tsu_for_identifier`
에 전달된다. 변환 자체(즉 `source_id` → 실제 `identifier` 문자열
산출)는 Crosswalk 테이블(`mapping_status`) 조회로 이루어진다.

---

## 4. Gate 재확인(TSU Contract Design 001과 일치)

Resolver는 아래 조건을 **전부** 만족하는 Manifest entry만
`identifier` 목록에 포함시킨다:

```
1. manifest_validator.py::compute_tsu_eligible() == READY
2. Crosswalk Record가 존재 AND mapping_status == "manual-confirmed"
   (evidence-backed/verified 단계까지는 Gate 통과 불가 — Mapping
   Policy 001 Rule 3 "automatic-confidence-only 금지"와 동일 이유:
   사람이 최종 확인한 매핑만 실제 TSU 생성에 투입한다)
```

두 조건 중 하나라도 실패하면 그 Manifest entry는 이번 실행에서
제외되고, 제외 사유(BLOCKED 판정 원인 또는 Crosswalk 미확정)가
Resolver의 출력 로그에 기록되어야 한다(설계만, 로그 포맷은 구현
단계에서 확정).

---

## 5. 이번 Contract가 기존 TSU Builder에 요구하는 변경 범위

**없음(이번 설계 시점 기준).** `build_tsu_for_identifier`는 지금도
`identifier`를 입력받아 동작하므로, Resolver가 그 앞단에서 올바른
identifier 목록만 걸러서 넘겨주면 Builder 내부 로직은 무수정으로
재사용 가능하다 — 유일한 변경 지점은 `build_tsu_for_all`이
`canonical_root.iterdir()`로 직접 열거하던 부분을 Resolver 호출로
대체하는 것뿐이며, **이 대체 자체도 이번 Task에서는 구현하지
않는다**(Crosswalk Adapter 구현은 다음 단계).
