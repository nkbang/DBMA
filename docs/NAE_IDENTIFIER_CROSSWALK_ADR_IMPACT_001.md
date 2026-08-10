# NAE Identifier Crosswalk ADR Impact Analysis 001

**Project:** NAE-IDENTIFIER-CROSSWALK-DESIGN-001 Phase 4
**작성일:** 2026-08-05
**성격:** 검토만 수행 — ADR-001/014/015/016/017/018/019 어느 것도
수정하지 않는다.

---

## ADR-017 — canonical_id authority가 유지되는가?

**예, 완전히 유지된다.** Crosswalk Layer는 Registry `canonical_id`/
`legacy_id`를 조회만 할 뿐 정의하거나 변경하지 않는다(§Mapping Policy
Rule 1). `canonical_id`가 "정본 표기"라는 ADR-017의 권위는 그대로다 —
Crosswalk의 `source_identifier` 필드가 참조하는 것은 Registry의 기존
FK 문자열(`source_id`)이지 `canonical_id`가 아니다(Option B 원칙상
FK는 그대로 두고 canonical_id는 별도 필드로 병기됐으므로, Crosswalk도
그 구조를 그대로 따른다). **ADR-017 수정 불필요.**

---

## ADR-015 — Ingestion Pipeline에 Crosswalk 요구사항 추가 필요한가?

**당장은 불필요 — 단, 향후 신규 corpus 유입 시점에는 검토 대상이
될 수 있다.** ADR-015는 `scope_modified: docs/ only`로 아직 실행된
적이 없는 설계 문서 상태이며(Promotion Review에서도 "구현 근거
없음"으로 승격 보류됨), 3.1절의 10단계 Ingestion Lifecycle 자체가
아직 실제로 가동되지 않았다. 지금 발견된 Crosswalk 필요성은 **이미
존재하는(과거에 유입된) Pilot corpus**의 identifier 불일치 문제이지,
ADR-015가 규정하는 "새로 유입되는" corpus의 문제가 아니다. 다만
ADR-015가 실제로 구현되어 신규 corpus가 유입되기 시작하면, 그 10단계
Lifecycle에 "Crosswalk Record 생성" 단계를 추가할지는 그때 별도
검토가 필요하다 — 이는 **이번 Task의 권고 사항으로만 남기고, ADR-015
본문은 수정하지 않는다.**

---

## ADR-014 — Modern Corpus Layer와 동일 모델 사용 가능한가?

**부분적으로 가능 — 완전히 재사용하기엔 이르다.** ADR-014는
`source_type`/`copyright_status`/`usage_permission`/`access_control`
4개 필드를 도입했고(§69), 이는 Crosswalk의 `source_type`/`target_type`
enum 설계(§Schema §2)와 "같은 값을 여러 계층에 병기한다"는 유사한
패턴을 쓴다. 그러나 ADR-014 자체가 아직 Proposed(승격 보류, 구현
근거 없음)이므로, 그 위에 Crosswalk을 얹는 것은 **아직 존재하지
않는 기반 위에 짓는 것**이 된다. **ADR-014 수정 불필요**하나, Crosswalk
Layer의 실제 구현은 ADR-014가 Approved로 승격된 이후(또는 최소한
Modern Corpus Layer 실행이 시작된 이후)로 순서를 맞추는 것이 안전하다
— 지금은 Pilot corpus(legacy 유입분)만을 대상으로 Crosswalk을 먼저
정의하고, Modern Corpus용은 별도 시점에 재검토를 권고한다.

---

## 종합 판단

| ADR | 영향 | 수정 필요? |
|---|---|---|
| ADR-001(Retrieval Authority) | 없음 — Crosswalk은 Retrieval을 전혀 참조하지 않음 | 불필요 |
| ADR-014 | 패턴 유사성 있으나 기반 자체가 아직 미구현 | 불필요(순서만 뒤로) |
| ADR-015 | 향후 신규 corpus 유입 시 재검토 후보 | 불필요(지금은) |
| ADR-016 | Entity 모델 자체는 무관(Crosswalk은 Source 계층 아래, 즉 물리 파일 식별자 문제) | 불필요 |
| ADR-017 | canonical_id authority 완전 유지 확인 | 불필요 |
| ADR-018 | Periodical(volume+issue) 확장과 무관 — Crosswalk은 Source 단위로 동작 | 불필요 |
| ADR-019 | **저장 위치 후보 중 하나(Manifest 필드 확장)가 ADR-019 범위를 건드릴 수 있음**(§Schema §3) — 그러나 이번 Task는 저장 위치를 확정하지 않았으므로 현시점에는 수정 불필요, **저장 위치 결정 시점에 재검토 필요** | **조건부 — 결정 보류** |

**결론: 이번 설계 단계에서는 7개 ADR 전부 수정 불필요.** 유일한
조건부 항목(ADR-019, 저장 위치)은 Crosswalk 저장소 위치가 실제로
확정되는 다음 단계(Crosswalk Adapter 구현 착수 시점)에 다시 검토해야
한다 — 그 시점에 "Manifest 필드 확장" 방식을 선택한다면 ADR-019
Amendment가 필요할 수 있고, "별도 파일" 방식을 선택하면 필요 없을
가능성이 높다(§Schema §3 권고 참고).
