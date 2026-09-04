# NAE ADR-019 Impact Review 001

**Project:** NAE-CROSSWALK-STORAGE-LOCATION-DESIGN-001
**작성일:** 2026-08-05
**성격:** 검토만 수행 — `docs/architecture/ADR-019-NAE-Corpus-Manifest-Layer.md`
본문은 이번 문서로 수정하지 않는다.

---

## 1. ADR-019가 정의한 범위 재확인

ADR-019 §3.2/§3.3 실측:

```
Manifest Entry는 Source의 확장이 아니라 별도 Entity, source_id FK로 1:1 연결.
manifest_id = source_id.

필수 필드: manifest_id, source_id, work_id, edition_id(조건부),
volume_id(조건부), issue_id(조건부), processing_status, tsu_access,
schema_version.
```

Crosswalk의 8개 필드(`crosswalk_id`/`source_identifier`/`source_type`/
`target_identifier`/`target_type`/`mapping_status`/`confidence`/
`evidence`/`created_at`/`verified_at`)는 이 목록에 **하나도 없다** —
ADR-019는 애초에 "identifier 번역"이라는 책임을 다루도록 설계된 적이
없다(ADR-019 §2 Problem: "이 자료가 지금 파이프라인의 어느 단계에
있는가"를 추적하는 계층 — Crosswalk의 목적인 "이 identifier가 다른
계층에서 뭐라고 불리는가"와는 다른 질문).

---

## 2. 질문별 답변

### 기존 ADR 유지 가능한가?

**예, 완전히 유지 가능.** Option B(Dedicated Crosswalk Store)를
채택하면 ADR-019가 정의한 Manifest Entry 구조·필드·Lifecycle 중
어느 것도 건드리지 않는다 — Crosswalk은 `NAE/metadata/crosswalk/`라는
ADR-019가 전혀 언급하지 않는 별도 위치에 존재하므로, ADR-019 본문의
"범위"(Authority Registry와 TSU 사이의 처리 상태 추적)를 그대로
둔 채로 그 옆에 새 계층이 하나 더 생기는 구조다.

### Amendment 필요한가?

**본문 Amendment는 불필요. 단, 문서 상호 참조 추가를 권고.**
ADR-019를 "고쳐야 할" 이유는 없지만(§Option A를 선택했을 때만
Amendment가 필요했을 것 — Option B를 선택했으므로 해당 없음),
향후 누군가 ADR-019만 읽고 "Manifest가 TSU까지의 전체 경로를 커버
한다"고 오해하지 않도록, ADR-019 본문에 **1줄짜리 pointer**(예:
"Manifest → Corpus/TSU identifier 번역은 별도 Crosswalk Layer가
담당하며, 이는 ADR-019 범위 밖이다 — `NAE_IDENTIFIER_CROSSWALK_
SCHEMA_001.md` 참고")를 추가하는 것을 권고한다. **이는 이번 Task에서
실행하지 않는다**(ADR 파일은 절대 변경 금지 목록에 있음) — 별도
승인된 작업으로 이관한다.

---

## 3. 결론

```
ADR-019 본문 수정: 불필요
ADR-019 Amendment: 불필요(Option B 채택 시)
권고(실행하지 않음): ADR-019에 Crosswalk Layer를 가리키는 상호 참조 1줄 추가
```

Option A(Manifest Extension)를 선택했다면 이 판단은 반대가 됐을
것이다 — Manifest Entry에 없던 필드(`crosswalk`)를 ADR-019가 정의한
필수 필드 집합에 새로 넣어야 하므로, 그 경우엔 Amendment가 필요했다.
이것이 §Storage Decision 001에서 Option B를 최종 채택하는 핵심 근거
중 하나다.
