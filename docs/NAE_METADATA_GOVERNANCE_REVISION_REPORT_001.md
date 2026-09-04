# NAE Metadata Governance Revision Report 001

작성일: 2026-08-02
Project: NAE-METADATA-GOVERNANCE-REVISION-001
성격: Governance Revision (설계 문서 수정, 구현 아님)
Git Commit: 미수행 — 사용자 승인 대기

---

## 1. 변경 문서 목록

| 문서 | 변경 유형 | 요약 |
|---|---|---|
| [`docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md`](architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md) | 수정 | §3.7 Dataset Isolation Rule 신설, Consequences에 R6 대응 완료 기록, front-matter에 revised 이력 추가 |
| [`docs/NAE_CORPUS_INGESTION_STANDARD_v1.md`](NAE_CORPUS_INGESTION_STANDARD_v1.md) | 수정 | Phase 3 값 체계 정정 + License Rule 설명 추가, Phase 4 Edition entity 승격(edition_id), Phase 8 TSU 필수 9필드 명문화, 최종 답변 3/4번 갱신 |
| [`docs/NAE_METADATA_GOVERNANCE_v1.md`](NAE_METADATA_GOVERNANCE_v1.md) | 신규 | Metadata Philosophy~Migration Policy 7개 섹션, License/Copyright/Authority 값 체계의 단일 정본 |
| `docs/NAE_METADATA_GOVERNANCE_REVISION_REPORT_001.md` | 신규 | 본 보고서 |

ADR-014, `NAE_MODERN_CORPUS_ARCHITECTURE_v1.md`는 명령서 허용 범위(ADR-015/
Ingestion Standard/신규 Governance 문서)에 포함되지 않아 **수정하지 않았다** —
초기 값 목록이 남아 있으며, 새 정본에 대한 참조는 §7에서 설명.

---

## 2. C1 지적사항 대응표

| C1 항목 | 원 판정 | 대응 문서 | 대응 내용 | 상태 |
|---|---|---|---|---|
| R1 | WARNING | NAE_METADATA_GOVERNANCE_v1 §4.1 | `copyright_status` 값 체계를 `public_domain\|copyrighted\|licensed\|unknown`으로 정정, License→Copyright 매핑표 제공 | 해소 |
| R2 | WARNING | NAE_METADATA_GOVERNANCE_v1 §4.2 | `usage_permission` 값 체계를 `research\|citation_only\|internal_use\|no_redistribution`으로 정정 | 해소 |
| (access_control 미구현) | WARNING | NAE_METADATA_GOVERNANCE_v1 §4.3 | `access_control: public\|restricted\|private` 정의, usage_permission과의 축 분리 명시 | 해소(설계 레벨) |
| R3 | WARNING | NAE_METADATA_GOVERNANCE_v1 §2.2 | `schema_version 2.0-modern` → `2.0.0`, SemVer Major/Minor/Patch 기준 문서화 | 해소 |
| R4 | WARNING | NAE_METADATA_GOVERNANCE_v1 §5.1, NAE_CORPUS_INGESTION_STANDARD_v1 Phase 4 | `author_id` 구조화 — 표기 변형 통합 규칙 유지, 이번 개정에서는 재확인만(기존 설계가 이미 반영) | 기해소 확인 |
| R5 | WARNING | NAE_METADATA_GOVERNANCE_v1 §5.1 | `work_id`뿐 아니라 `edition_id`를 신규 entity로 승격 — Work/Edition/Source File 3단 분리로 판본 관리 완전화 | 해소(기존보다 강화) |
| R6 | **BLOCKER** | ADR-015 §3.6–3.7 | `--dataset-path` 필수 조건 명시(기존 반영) + Dataset Isolation Rule 신규 조항으로 일반화(implicit path inference 금지, pipeline별 boundary 유지) | 해소 |

---

## 3. Schema 변경 내용

### 3.1 값 체계 정정 (Major 구조 변경 아님 — 설계 단계 정정, §2.2 원칙)

| 필드 | 이전(ADR-014 초안) | 이후(정본: NAE_METADATA_GOVERNANCE_v1) |
|---|---|---|
| `copyright_status` | `public_domain\|copyright_restricted\|fair_use_reference\|unknown` | `public_domain\|copyrighted\|licensed\|unknown` |
| `usage_permission` | `full_text_storage\|excerpt_only\|metadata_only\|citation_only` | `research\|citation_only\|internal_use\|no_redistribution` |
| `access_control` | `internal_only\|user_only\|no_redistribution` | `public\|restricted\|private` |
| `schema_version` | `"2.0-modern"` | `"2.0.0"` |

### 3.2 License Rule 신규

`license` 필드를 `source_value`(원본 표기 보존)/`normalized_value`(=`copyright_status`,
파생값) 2단 구조로 재정의. 기존 v1.2 `license` 필드 자체는 변경하지 않음.

### 3.3 Entity 승격

`edition_id`를 Work와 Source File 사이 독립 entity로 신설 — Author→Work→
Edition→Source File 4단 계층 확정.

---

## 4. Authority Layer 정의

```
Author  (author_id)   — 저자 canonical, aliases로 표기 변형 통합
  ↓
Work    (work_id)     — 저작 단위
  ↓
Edition (edition_id)  — 판본 단위 [신규 승격]
  ↓
Source  (source_id)   — 파일 단위
```

- 자동 병합 금지 원칙 유지(동명이인 오탐 방지, 항상 사람이 최종 확인).
- 레지스트리(`authority/authors.yaml`, `authority/works.yaml`)는 설계만 —
  이번 작업에서 실제 생성하지 않음(금지 사항 준수).
- `NAE_CORPUS_INGESTION_STANDARD_v1.md` Phase 6(Duplicate Detection)의
  "Different Scan Same Edition" 유형이 `edition_id` 도입으로 canonical key를
  갖게 됨 — 이전에는 문자열 `edition` 필드만 있어 그룹핑 근거가 약했음.

---

## 5. TSU 영향 분석

- TSU 생성 전 필수 필드를 9개로 확정(§6 NAE_METADATA_GOVERNANCE_v1) —
  `source_id`/`author_id`/`work_id`/`category`/`publication_year`/
  `source_type`/`copyright_status`/`citation_policy`/`tsu_access`.
- `copyright_status`×`usage_permission` 조합별 TSU 방식(Full/Citation
  Only/보류/차단) 매트릭스 신설 — 이전에는 `usage_permission` 값만으로
  판단했으나, 이번 개정으로 두 축의 조합을 명시적으로 규정.
- Dataset Isolation Rule(ADR-015 §3.7)에 따라 TSU 생성 호출은 항상 명시적
  `--dataset-path`를 사용해야 하며, 이 조건이 R6 BLOCKER 해소의 핵심.
- **주의**: 이 모든 정의는 설계 문서 상의 규칙이며, 실제 TSU 빌더 코드
  (`pipeline/tsu/builder.py` 등)가 이 9개 필드를 검증하도록 구현하는 작업은
  이번 범위 밖(Migration Policy §7.2 Step 4와 별개의 후속 구현 과제).

---

## 6. Migration 계획

```
Step 1. v1.2 manifest entry에 copyright_status(파생) 필드 추가
Step 2. Modern 신규 등록분부터 schema_version 2.0.0 전체 필드 적용
Step 3. NAE-PD 기존 entry에 author_id/work_id/edition_id 점진적 소급 부여(사람 확인)
Step 4. source_validator.py를 v1.2/v2.0.0 + 신규 값 체계 검증하도록 확장
```

원칙: RAW 변경 금지, 기존 v1.2 데이터 재작성 금지(파생 필드만 추가), 일괄
변환이 아닌 점진적 적용. 상세는 `NAE_METADATA_GOVERNANCE_v1.md` §7.

---

## 7. Remaining Risks

| # | 리스크 | 설명 | 후속 조치 |
|---|---|---|---|
| 1 | ADR-014 원문 불일치 | ADR-014 §3.3/§3.4에는 여전히 구 값 목록이 남아 있음 — 이번 명령서가 ADR-014 수정을 허용 범위에 포함하지 않아 소급 수정하지 않음 | ADR-014를 직접 수정할지, 아니면 현재처럼 "새 정본 참조" 방식으로 유지할지 별도 결정 필요 |
| 2 | source_validator.py 미확장 | 설계된 값 체계/9개 TSU 필드를 실제로 검증하는 코드가 아직 없음 | Migration §7.2 Step 4, 별도 구현 작업 필요 |
| 3 | Authority 레지스트리 미생성 | `authority/authors.yaml`/`authority/works.yaml` 파일이 존재하지 않아 현재는 Author/Work/Edition 통합을 수동으로만 확인 가능 | 별도 구현 승인 필요(이번 명령서 금지 사항) |
| 4 | Quality Gate 임계값 미정 | OCR 품질 점수 등 구체적 수치가 여전히 미정(이전 보고서에서도 지적됨) | 실제 샘플 데이터로 보정 필요, 이번 작업 범위 밖 |
| 5 | Retrieval 미통합 | `tsu_access`/`access_control`을 실제 검색 필터로 적용하는 `RetrievalEngine` 코드는 여전히 미구현 | ADR-001/013 개정 별도 ADR 필요(ADR-014/015 Future Expansion과 동일) |

---

## 완료 조건 답변

1. **ADR-015 BLOCKER가 제거되었는가?** — 예. §3.6(--dataset-path 필수) + §3.7(Dataset Isolation Rule)로 문서 레벨에서 해소.
2. **Metadata Schema v2.0.0 준비가 되었는가?** — 설계 레벨에서 예(값 체계 정정 완료, SemVer 원칙 문서화). 실제 스키마 파일 생성/검증 코드는 범위 밖.
3. **Author/Work/Edition/Source 모델이 정의되었는가?** — 예. `NAE_METADATA_GOVERNANCE_v1.md` §5, Edition을 독립 entity로 승격.
4. **TSU Pipeline에 필요한 Metadata가 확정되었는가?** — 예. 9개 필수 필드 + copyright_status×usage_permission 조합 매트릭스로 확정.
5. **추가 자료가 들어와도 동일 Pipeline으로 처리 가능한가?** — 예. `NAE_CORPUS_INGESTION_STANDARD_v1.md`의 10단계 Lifecycle 구조는 이번 개정으로 변경되지 않았고, 값 체계/Entity 모델 정정만 반영되었으므로 신규 자료도 동일 절차로 처리 가능.

---

*이번 작업은 Governance Revision이며 구현 단계가 아니다. Git Commit은 사용자 승인 전까지 수행하지 않았다.*
