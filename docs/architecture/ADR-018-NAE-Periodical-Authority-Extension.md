---
title: "ADR-018: NAE Periodical Authority Extension (Design Only)"
category: architecture
based_on:
  - docs/NAE_PERIODICAL_AUTHORITY_DESIGN_v1.md
  - docs/NAE_PERIODICAL_PILOT_REPORT_001.md
  - docs/NAE_PERIODICAL_AUTHORITY_REVIEW_001.md
  - docs/NAE_PERIODICAL_ARCHITECTURE_REVISION_001.md
  - docs/architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md
  - docs/architecture/ADR-017-NAE-ID-Governance-Standard.md
created: 2026-08-02
scope_modified: docs/ only — Schema YAML/Registry/RAW/코드 변경 없음
---

# ADR-018: NAE Periodical Authority Extension (Design Only)

| | |
|---|---|
| Status | Proposed |
| Date | 2026-08-02 |
| Deciders | 사용자 승인 대기 (설계 문서 단계) |
| Supersedes | — |
| Superseded by | — |

---

## 1. Context

Baptist Missionary Magazine Pilot(`NAE-PERIODICAL-AUTHORITY-PILOT-001`)이
RAW 실측으로 정기간행물 고유 문제(제호 변경, volume 번호 리셋, 발행
조직이 개인이 아님)를 발견했다. C1의 독립 검토
([Review-001](../NAE_PERIODICAL_AUTHORITY_REVIEW_001.md), APPROVED WITH
CONDITIONS)가 Entity Model(Option A)은 승인했으나 Organization Authority와
Title History 처리는 미해결로 남겼다. 이 ADR은 그 두 항목을 포함한
Periodical 확장 전체를 하나의 Architecture Decision으로 기록한다.

## 2. Problem

정기간행물을 기존 Author→Work→Edition→Volume→Source 모델 위에 어떻게
표현하되, (1) 발행 주체가 개인이 아닌 조직인 경우, (2) 발행 기간 중
제호가 여러 번 바뀌는 경우를 깨뜨리지 않고 수용할 것인가?

## 3. Decision

### 3.1 Entity Model — 안 1 채택

```
Author/Organization(author_type로 구분)
  └── Work(work_type: periodical)
        └── Volume
              └── Issue (신규, periodical 전용 조건부 Entity)
                    └── Source
```

Edition은 정기간행물에서 생략(이미 확립된 "Volume은 monograph에서
선택적 생략 가능" 원칙을 일반화). Article은 Registry Entity로 만들지
않는다(RAW가 article 단위 물리 파일을 제공하지 않음).

### 3.2 Organization Authority — `author_type` 필드

별도 `CorporateAuthor` Entity를 신설하지 않고, 기존 Author entity에
`author_type: person | organization` 필드를 추가한다.
`birth_year`/`death_year`는 organization일 때 항상 `null`(설립/해산
연도로 재해석하지 않음, `notes`에 자유 텍스트로만 기록).

발행 조직(publisher)은 `Work.author_id`로, 편집자(개인)는 신규 선택
필드 `Work.editor_id`(Author FK, `author_type=person`)로 분리 표현한다.

### 3.3 Title History — `title_history[]` + 경량 계승 관계

```yaml
title_history: [{title, start_date, end_date}, ...]
continues_work_id: string|null
continued_by_work_id: string|null
```

별도 Series Entity는 신설하지 않는다(Work 2개 사이의 단순 이전/이후
관계로 충분). 서지학적 계승 관계가 검증되지 않은 자료(예: Pilot의 1803/
1817 사례)는 `continues_work_id`를 비운 채 별도 Work로 유지한다 — 자동
병합하지 않는다.

### 3.4 TSU 필수 필드 예외

`work_type=periodical`인 자료는 TSU 생성 전 필수 필드에서
`edition_id`를 면제하고 `volume_id`+`issue_id`를 필수로 대체한다
(GOVERNANCE §6의 조건부 예외로 문서화).

### 3.5 Schema Version

`2.1.0 → 2.2.0`(Minor) 대상 — 전부 optional 필드 추가, 기존 데이터
무효화 없음. **이번 ADR은 실제 스키마 파일을 수정하지 않는다.**

## 4. Alternatives

| 대안 | 기각 사유 |
|---|---|
| 안 2: Organization→Periodical→Series→Volume→Issue→Source | Author→Work 인프라를 정기간행물 전용으로 중복 구축 — 과설계 |
| Organization을 위한 별도 `CorporateAuthor` Entity | `author_id` FK 대상이 두 테이블로 갈라져 참조 무결성 검사 이원화 |
| Title History를 Series Entity로 모델링 | 두 Work 사이 관계일 뿐 — 완전한 Entity로 만들 실익 없음 |
| Title History를 기존 `aliases`(평면 배열)로만 유지 | 표기별 사용 기간(시간 순서) 정보가 소실됨 |
| Issue를 모든 Work 유형에 정식 승격 | monograph에는 항상 빈 계층이 되어 스키마가 불필요하게 넓어짐 |

## 5. Consequences

- Schema/Registry/코드는 이 ADR로 변경되지 않는다 — 정책만 확정.
- 다음 정기간행물 Pilot(volume+issue 복수 검증 등)부터 이 모델을
  그대로 적용해야 한다.
- 1803/1817 두 periodical Work의 병합 여부는 여전히 미결(서지 검증
  선행 필요) — 이 ADR은 "병합할 수 있는 필드"만 마련했을 뿐 병합을
  결정하지 않는다.
- ADR-016/017 본문은 변경하지 않는다(소급 수정 금지 관례).
- ADR 번호 충돌 확인: 작성 시점 기준 001–017 존재, 018은 미사용 번호로
  충돌 없음.

## 6. Future Expansion

- `author_type`/`title_history`/`continues_work_id`/`editor_id`를
  실제 `modern/source_manifest.schema.yaml`(v2.2.0)에 반영
- Registry Validation Tool(설계만 존재)에 `author_type` 분기 검증 추가
- TSU 빌더에 `work_type` 기반 필수 필드 예외 로직 구현
- 정기간행물 3차 Pilot: 동일 volume 내 복수 issue 시나리오 검증
- 1803/1817 제호 계승 관계 서지 전문가 검증

## Validation

설계 문서이므로 코드/데이터 검증 대상 없음. 문서 정합성만 확인:

```
grep -r "ADR-018" docs/
```
