# NAE Metadata Architecture Revision Report 001

**Project:** NAE-METADATA-ARCHITECTURE-REVISION-001
**Date:** 2026-08-02
**Nature:** 설계 개정(Revision) — 실제 Metadata 생성/전체 Corpus 확대 아님
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. Executive Summary

Pilot-001(church_order)과 Pilot-002(Fuller 다권본) 검증 결과 나온 8개 발견
사항(R1~R8)을 정식 Architecture 문서 3건(GOVERNANCE/Modern Corpus/Ingestion
Standard)에 반영하고, 이번 개정 자체를 신규 [ADR-016](architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md)으로
기록했다. ADR-014/015 본문은 소급 수정하지 않고(기존 원칙 일관 적용) 최소
pointer만 추가했다. `Modern manifest schema`는 `2.0.0 → 2.1.0`(Minor,
하위 호환)으로 갱신했다.

8개 발견 사항 전부 결정 완료 — 미결정 항목 없음.

---

## 2. R1~R8 대응표

| # | 발견 | 결정 | 반영 위치 |
|---|---|---|---|
| R1 | `source_type` enum gap(2회 연속 발견) | `public_archive` 값 신규 추가, 기존 4개 값 유지 | GOVERNANCE §4.4 |
| R2 | Work:Edition 1:1 암묵 가정이 Fuller 사례로 반증됨 | "Work 1개 : Edition 1개 이상(1:N)" 관계로 명문화 | GOVERNANCE §5.1, Ingestion Standard Entity Model |
| R3 | Volume을 정식 Entity/필드로 승격할지 | **승격** — `volume_id`/`volume_number`를 선택(optional) 필드로 Schema v2.1.0에 추가 | GOVERNANCE §5.1/§5.2/§5.3, Modern Corpus Task 3 |
| R4 | `edition_id` TSU 필수 여부 문서 간 불일치 | **필수로 통일**(기존: 선택) — `volume_id`는 다권본에 한해 조건부 필수 | GOVERNANCE §6, Ingestion Standard Phase 8 |
| R5 | validator `content_genre` vs `category` 필드명 불일치(BLOCKER, Step 2 한정) | `schema_version`별 필수 필드 분기 요구사항으로 문서화(코드 미변경) | GOVERNANCE §7.3, Modern Corpus Task 3 정정 각주 |
| R6 | 제목 3원 불일치 시 우선순위 규칙 없음 | RAW 원문 title page를 canonical로, 나머지는 `title_variants`로 보존 | Ingestion Standard Work Authority |
| R7 | `archive_source` 필드가 RAW에 실제 없는 정보 요구(2회 연속) | **선택(optional)**으로 확정, 미충족 시 WARNING(FAIL 아님) | Ingestion Standard Phase 7 Quality Gate |
| R8 | ID(slug) 충돌 처리 규칙 없음 | 숫자 suffix(`-2`, `-3`…) 순차 부여 + 사람 확인 로그 | GOVERNANCE §7.4, Ingestion Standard ID 생성 규칙 |

미결정 항목: **없음.**

---

## 3. 변경 문서 목록 및 diff 요약

| 문서 | 변경 유형 | 요약 |
|---|---|---|
| [`docs/NAE_METADATA_GOVERNANCE_v1.md`](NAE_METADATA_GOVERNANCE_v1.md) | 수정 | §2(버전 정책), §4.4 신설(Source Type Rule), §5.1(Volume Entity, 1:N 관계), §5.2/§5.3(Volume 병합·레지스트리), §6(TSU 필드 개정), §7.3/§7.4 신설(Validator 요구사항, ID 충돌 규칙), §7.5(ADR-016 참조), 완료 조건 체크 하단에 개정 요약 표 추가 |
| [`docs/NAE_MODERN_CORPUS_ARCHITECTURE_v1.md`](NAE_MODERN_CORPUS_ARCHITECTURE_v1.md) | 수정 | Task 3 스키마 블록에 `edition_id`/`volume_id`/`volume_number` 필드 추가, `schema_version` 2.0.0→2.1.0, 값 체계 필드를 GOVERNANCE 참조로 전환(캡슐화), validator 실측 정정 각주 추가 |
| [`docs/NAE_CORPUS_INGESTION_STANDARD_v1.md`](NAE_CORPUS_INGESTION_STANDARD_v1.md) | 수정 | ID 생성 규칙에 `edition_id`/`volume_id` 및 충돌 규칙 추가, Entity Model 5단 확장 + 1:N 명문화, Work Authority에 제목 우선 원칙 추가, Duplicate Policy에 Volume Conflict 유형 추가, Quality Gate에 `archive_source` 정책 추가, TSU 필수 필드 개정(edition_id 승격) |
| [`docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md`](architecture/ADR-014-NAE-Modern-Corpus-Layer.md) | 최소 수정 | front-matter에 `partially_extended_by: ADR-016` pointer만 추가, 본문 불변 |
| [`docs/architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md`](architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md) | 신규 | 이번 개정 전체를 기록하는 ADR |
| `docs/NAE_METADATA_ARCHITECTURE_REVISION_REPORT_001.md` | 신규 | 본 보고서 |

ADR-015는 이번 개정에서 내용 변경이 필요한 부분이 없어(값 체계는 이미
GOVERNANCE로 위임된 상태) 수정하지 않았다.

---

## 4. Schema Version 변경 여부 및 사유

```
Modern manifest schema: 2.0.0 → 2.1.0  (Minor)
```

**사유**: `public_archive` enum 값 추가와 `volume_id`/`volume_number` 선택
필드 추가 모두 **기존 데이터를 무효화하지 않는 추가적 변경**이다(GOVERNANCE
§2.2 SemVer 정책: 필드 추가=Minor). 아직 실제 데이터가 생성되지 않은 설계
단계이므로 더 보수적으로 접근할 수도 있었으나, `2.1.0`으로 명시적으로
버전을 올려 "이 시점 이후 스키마가 Volume을 지원한다"는 사실을 추적
가능하게 하는 편을 택했다(CLAUDE.md "작업은 반드시 추적 가능해야 한다"
원칙).

---

## 5. ADR 처리 방식

**신규 ADR-016 채택**(기존 ADR-014/015 직접 개정 안 함). 근거는
ADR-016 §3.3/§4에 상세 — 요약하면, 이전 GOVERNANCE 개정 때 이미 "ADR은
소급 수정하지 않는다"는 원칙을 확립했고, 이번에도 동일 원칙을 적용하는
것이 문서 이력의 일관성을 지킨다. ADR-014에는 `partially_extended_by`
front-matter pointer만 추가했다(본문 불변).

---

## 6. 코드 구현 필요 항목 (이번 작업 범위 밖 — 후속 작업 목록만)

이번 작업은 설계 문서 개정까지이며, 아래는 실제 구현 시 필요한 항목을
나열만 한다(코드 수정 없음, Phase 5 Migration Simulation과 동일한 성격):

1. `scripts/source_validator.py`를 `schema_version`별 필수 필드 분기하도록
   확장(`content_genre` vs `category`) — GOVERNANCE §7.3 요구사항 참고.
2. `resources/theological_sources/modern/source_manifest.schema.yaml`
   실제 파일 생성(v2.1.0, `volume_id`/`volume_number` 포함).
3. `authority/authors.yaml`, `authority/works.yaml`(Volume/Edition 중첩
   포함) 실제 생성.
4. ID 생성 스크립트에 slug 충돌 감지 및 suffix 부여 로직 구현.
5. TSU 빌더가 `edition_id`(필수)/`volume_id`(조건부 필수) 누락 시 생성을
   차단하도록 구현.

이 5개 항목은 로드맵상 다음 단계인 **Schema Migration**(AFTER REVIEW)의
범위이며, 이번 승인과 별개로 착수 승인이 필요하다.

---

## 7. Remaining Risks

| # | 리스크 | 설명 | 완화 방향 |
|---|---|---|---|
| 1 | Volume Entity가 아직 실제 스키마 파일에 반영되지 않음 | 설계 문서상으로만 정의됨, `source_manifest.schema.yaml` 실물 파일 없음 | Schema Migration 단계에서 처리(§6 항목 2) |
| 2 | 정기간행물(volume+issue) 유형 미검증 | Pilot-002는 단행본 다권본만 다룸, Baptist Missionary Magazine류(volume+issue 조합)는 여전히 모델 밖 | ADR-016 Future Expansion에 3차 Pilot 후보로 기록 |
| 3 | `edition_id` 필수화가 기존 Pilot-001 산출물에 소급 적용되지 않음 | Pilot-001 church_order pilot 파일은 이미 커밋됨 — `edition_id` 필드 자체는 존재하나 "필수" 승격 이전 산출물이라 재검증 안 됨 | 실제 Migration 착수 시 Pilot-001 산출물도 새 요건으로 재검토 필요(경미, 이미 필드가 존재하므로 데이터 누락은 아님) |
| 4 | `archive_source` optional 확정이 데이터 품질 저하로 이어질 가능성 | 필드를 선택으로 낮추면 향후 등록자가 이 정보를 아예 채우지 않을 유인이 생김 | Quality Gate WARNING으로 계속 가시화(FAIL은 아니지만 무시되지 않도록 유지) |

---

## 완료 조건 답변

1. **R1~R8이 전부 결정되었는가?** — 예, 8건 전부 결정(§2).
2. **Schema Version은 갱신되었는가, 유지되었는가 — 사유는?** — 갱신됨, `2.0.0 → 2.1.0`(Minor, 하위 호환 추가 변경, §4).
3. **Volume Entity는 승격되었는가?** — 예, 선택(optional) Entity로 승격(§2 R3).
4. **ADR은 개정인가 신규인가?** — 신규(ADR-016), 기존 ADR-014/015는 pointer만 추가하고 본문 불변(§5).
5. **전체 Corpus Metadata Migration에 착수 가능한 상태인가, 아니면 Schema Migration이 먼저인가?** — **Schema Migration이 먼저다.** §6에 나열한 5개 구현 항목(validator 확장, 실제 스키마 파일 생성, Authority 레지스트리 생성, ID 충돌 로직, TSU 빌더 필드 검증)이 선행되어야 하며, 이번 작업(Architecture Revision)의 승인이 곧 Migration 착수 승인은 아니다.

---

## 로드맵 갱신

```
RAW Acquisition              ✅
Architecture Design          ✅
Governance                   ✅
Authority Plan                ✅
Church Order Pilot           ✅
Fuller Multi-volume Pilot    ✅
Architecture Revision        ✅ (이번 작업)
Schema Migration              NEXT (별도 승인 필요)
Corpus-wide Metadata Build    FUTURE
```

---

*Corpus 파일 수정, RAW 데이터 변경, Directory rename/생성, Metadata 실제
생성, Authority 파일 실제 생성, 코드 수정, TSU/Embedding 생성, Retrieval
변경, 전체 Corpus Migration 착수, Git Commit — 전부 수행하지 않음.*
