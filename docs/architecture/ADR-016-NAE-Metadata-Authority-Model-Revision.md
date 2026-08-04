---
title: "ADR-016: NAE Metadata Authority Model Revision (Design Only)"
category: architecture
based_on:
  - docs/NAE_METADATA_GOVERNANCE_v1.md
  - docs/NAE_METADATA_AUTHORITY_PLAN_REVIEW_001.md
  - docs/NAE_METADATA_PILOT_REPORT_001.md
  - docs/NAE_METADATA_PILOT_002_FULLER_REPORT.md
  - docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md
  - docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md
created: 2026-08-02
scope_modified: docs/ only — Corpus/RAW 변경, Directory rename, Metadata 실제 생성, 코드 수정 없음
---

# ADR-016: NAE Metadata Authority Model Revision (Design Only)

| | |
|---|---|
| Status | Approved |
| Date | 2026-08-02 |
| Approved | 2026-08-03 (NAE-ADR-PROMOTION-001) |
| Deciders | 사용자 승인 완료 (2026-08-03) |
| Supersedes | — (ADR-014/015는 직접 개정하지 않음, §5 참고) |
| Superseded by | — |

---

## 1. Context

`NAE_METADATA_GOVERNANCE_v1.md`(ADR-014/015 기반)로 확정한 Metadata
Authority Model을 두 차례 Pilot으로 실증했다:

- Pilot-001(church_order, Dagg/Hiscox): Work:Edition=1:1인 단순 사례에서
  4단 Reference Integrity 전부 PASS.
- Pilot-002(Fuller Complete Works, 8권): 다권본 실증 결과 기존 모델의
  암묵적 가정(Work:Edition=1:1) 이 깨지는 실사례를 발견했고, 이후
  Architecture Revision 검토(`NAE_METADATA_ARCHITECTURE_REVISION_REPORT_001.md`)에서
  `source_type` enum gap, `edition_id` 필수 여부 등 추가 결정 사항이 확정됐다.

## 2. Problem

Pilot에서 실증된 8건의 개선 필요 사항(R1~R8, Revision Report §2 대응표
참고)을 정식 Architecture 문서에 어떻게 반영할 것인가 — 기존 ADR-014/015를
직접 개정할 것인가, 신규 ADR로 기록할 것인가?

## 3. Decision

### 3.1 반영 내용 요약 (상세는 `NAE_METADATA_GOVERNANCE_v1.md` 2026-08-02 개정 참고)

| 변경 | 유형 | 근거 |
|---|---|---|
| `source_type`에 `public_archive` 추가 | 값 추가(Minor) | Pilot-001 F-P1, Pilot-002 §9 — 2회 연속 발견 |
| Work:Edition = 1:N 관계 명문화 | 서술 명확화 | Pilot-002 §3, Fuller 실증(1820 Charlestown vs 1824-25 New Haven) |
| Volume Entity 신설(`volume_id`, `volume_number`, 선택) | 필드 추가(Minor) | Pilot-002 §4/§9 |
| `edition_id` TSU 필수 승격 | 요건 강화 | Plan Review-001 F2, Pilot-002 §9 재확인 |
| `volume_id` TSU 조건부 필수 | 요건 추가 | Pilot-002 §7 |
| Validator `schema_version`별 필드 분기 요구사항 명문화 | 요구사항 문서화(코드 미변경) | Plan Review-001 F1(BLOCKER, Step 2 한정) |
| RAW 원문 제목 우선 원칙 | 절차 명문화 | Pilot-001 F-P2 |
| `archive_source` 필드 optional 확정 | 정책 결정 | Pilot-001 F-P4(2회 연속 정보 없음 확인) |
| ID(slug) 충돌 시 suffix 부여 규칙 | 절차 추가 | Plan Review-001 F3 |

### 3.2 Schema Version

`Modern manifest schema: 2.0.0 → 2.1.0`(Minor). 전부 하위 호환 추가(기존
필드 의미 변경 없음, 기존 값 무효화 없음)이므로 Major bump 불필요 — 아직
실제 데이터가 생성되지 않은 설계 단계라는 점도 근거(GOVERNANCE §2.2 원칙).

### 3.3 ADR 처리 방식 — 신규 ADR 채택 (Phase 7 결정)

ADR-014/015를 직접 개정하지 않고 **이 신규 ADR-016으로 기록**한다.

**근거**: `NAE_METADATA_GOVERNANCE_v1.md` §7.3(구 §7.5)에 이미 "ADR은 결정
시점의 기록이므로 소급 수정하지 않는다"는 원칙이 확립되어 있고
(NAE-METADATA-GOVERNANCE-REVISION-001에서 ADR-014에 동일하게 적용됨), 이번
개정도 동일 원칙을 일관되게 적용하는 것이 문서 이력의 일관성을 지킨다.
ADR-014에는 이 ADR을 가리키는 최소한의 pointer(`partially_extended_by`
front-matter 필드)만 추가했다 — 본문 내용은 변경하지 않았다.

## 4. Alternatives

| 대안 | 기각 사유 |
|---|---|
| ADR-014/015를 직접 개정 | 기존에 이미 "ADR 소급 수정 금지" 원칙을 세워두고 신규 값을 GOVERNANCE 문서로 이관한 선례(NAE-METADATA-GOVERNANCE-REVISION-001)와 모순됨 — 일관성 훼손 |
| GOVERNANCE 문서 개정만 하고 ADR 신설 생략 | 이번 개정은 Entity 계층(Volume 추가) 변경을 포함해 "Architecture Decision"에 해당하는 무게가 있음 — GOVERNANCE는 값 체계 정본이지 결정 기록 형식이 아니므로, 결정 자체는 ADR에 남기는 것이 기존 관례(ADR-014/015가 유사 결정을 ADR로 남긴 선례)와 일치 |

## 5. Consequences

- `NAE_METADATA_GOVERNANCE_v1.md`, `NAE_MODERN_CORPUS_ARCHITECTURE_v1.md`,
  `NAE_CORPUS_INGESTION_STANDARD_v1.md` 3개 문서가 이번 개정 내용으로
  갱신됐다(상세 diff는 Revision Report 참고).
- ADR-014/015 본문은 변경되지 않았다 — ADR-014에 pointer만 추가.
- 실제 코드(`scripts/source_validator.py` 등) 변경은 이번 ADR 범위 밖 —
  요구사항만 문서화(GOVERNANCE §7.3).
- 다음 단계(Schema Migration)는 이 ADR 승인과 별개로 추가 승인이
  필요하다 — 로드맵상 "AFTER REVIEW" 단계.
- ADR 번호 충돌 확인: 작성 시점 기준 001–015 존재, 016은 미사용 번호로 충돌 없음.

## 6. Future Expansion

- 정기간행물(volume+issue, 예: Baptist Missionary Magazine) 대응을 위한
  3차 Pilot 및 `issue_number`/`series_id` 필드 검토
- `scripts/source_validator.py` 확장 구현(GOVERNANCE §7.3 요구사항 반영)
- Authority 레지스트리(`authority/authors.yaml`, `authority/works.yaml`)
  실제 생성 — 이번 ADR도 여전히 미생성 상태 유지
- early_baptist_collection(1,416파일) 전용 sub-plan — 계속 별도 트랙 유지

## Validation

설계 문서이므로 코드/데이터 검증 대상 없음. 문서 정합성만 확인:

```
grep -r "ADR-016" docs/
```

## Promotion Evidence (NAE-ADR-PROMOTION-001, 2026-08-03)

Evidence Before Promotion Rule(CLAUDE.md) 4조건 충족 확인:

1. **구현 완료** — Authority Registry(`authority/{authors,works,editions,
   volumes,sources}.yaml`) 실제 구축(`NAE_AUTHORITY_REGISTRY_BUILD_REPORT_001.md`)
2. **회귀 테스트 통과** — `tests/test_authority_validator.py`,
   `tests/test_authority_validator_canonical.py`(3-Validator 회귀 포함)
3. **독립 리뷰(C1) 완료** — `docs/NAE_C1_ARCHITECTURE_DESIGN_REVIEW_FINAL_001.md`
   (최종 판정: APPROVED WITH CONDITIONS)
4. **사용자 승인** — 2026-08-03 NAE-ADR-PROMOTION-001

`scope_modified`(frontmatter)는 작성 시점 "docs/ only"였으나, 이후
Registry 실제 구축으로 범위가 확장됨 — 위 Evidence 문서가 실행 근거.
