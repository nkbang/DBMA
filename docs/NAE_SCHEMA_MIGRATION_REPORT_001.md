# NAE Schema Migration Report 001

**Project:** NAE-SCHEMA-MIGRATION-001
**Date:** 2026-08-02
**Nature:** Infrastructure 구축만 — 전체 Corpus Metadata 생성 아님
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. Executive Summary

ADR-016에서 승인된 Metadata Architecture를 실제 사용 가능한 Schema
Layer(스키마 파일 + Authority Registry 빈 템플릿 + Validator 요구사항
명세 + Migration Guide)로 구축했다. 기존 v1.2 manifest에 대해
`scripts/source_validator.py`를 실제로 실행해 **21 PASS / 0 FAIL**을
확인, 신규 디렉토리(`modern/`, `authority/`) 추가가 기존 검증에 아무
영향을 주지 않음을 실측으로 검증했다.

---

## 2. Phase별 결과

### Phase 1 — Schema v2.1.0 작성: **완료**

파일: [`resources/theological_sources/modern/source_manifest.schema.yaml`](../resources/theological_sources/modern/source_manifest.schema.yaml)

요청된 14개 필드(`author_id`, `work_id`, `edition_id`, `volume_id`,
`source_id`, `category`, `source_type`, `copyright_status`,
`usage_permission`, `access_control`, `tsu_access`, `citation_policy`,
`archive_source`, `volume_number`) 전부 포함, 추가로 ADR-016 이전부터
있던 필드(`title`, `publication_year`, `publisher`, `language`,
`subcategory`, `theological_position`, `denomination`, `license`,
`topics`, `scripture_reference`, `doctrine_tags`, `status`,
`local_path`, `aliases`, `author_name`, `title_variants`, `edition`)도
v1.2/기존 설계 문서와의 연속성을 위해 함께 정의했다. 값 체계는 전부
`NAE_METADATA_GOVERNANCE_v1.md`를 정본으로 인용(재정의하지 않음).

### Phase 2 — Authority Registry Template 작성: **완료**

파일 5개 전부 빈 템플릿(schema_version + 빈 배열, 예시는 주석):
- `authority/authors.yaml`
- `authority/works.yaml`
- `authority/editions.yaml`
- `authority/volumes.yaml`
- `authority/sources.yaml`

**실제 데이터 미입력 확인**: 5개 파일 전부 `sources: []` /
`authors: []` 등 빈 배열만 존재(예시는 YAML 주석 블록으로만 기재,
파싱 시 데이터로 인식되지 않음).

### Phase 3 — Validator Specification: **완료**

파일: [`docs/NAE_SOURCE_VALIDATOR_REQUIREMENTS_v1.md`](NAE_SOURCE_VALIDATOR_REQUIREMENTS_v1.md)

요청 항목 전부 포함: category↔content_genre 대응(§2, 타입 차이까지
명시 — array vs 단일 string), schema version 분기(§3), Required/Optional
Fields(§4), Error Code(§5, 8개 제안), Validation Flow(§6, 9단계).
**코드는 수정하지 않았다**(실측: `scripts/source_validator.py` 파일
내용 변경 없음, git diff 없음 — 아래 §4 검증 참고).

### Phase 4 — Migration Guide 작성: **완료**

파일: [`docs/NAE_SCHEMA_MIGRATION_GUIDE_v1.md`](NAE_SCHEMA_MIGRATION_GUIDE_v1.md)

Manifest→Authority→Validator→Pilot→Corpus 5단계 순서, 각 단계 전제조건/
산출물/실패 시 처리 정의. Rollback 절차 5단계 전부 포함(RAW 무손상
원칙 재확인). Corpus-wide Migration(Step 5) 착수 전 체크리스트 포함.

### Phase 5 — Directory Validation: **완료, PASS**

실측(`find` 명령):

```
resources/theological_sources/
├── authority/
│   ├── authors.yaml, works.yaml, editions.yaml, volumes.yaml, sources.yaml   ← 신규(빈 템플릿)
│   └── pilot/, pilot/fuller/                                                  ← 기존(Pilot 산출물, 유지)
├── baptist/
│   ├── source_manifest.yaml, source_candidates.csv                           ← 기존(v1.2, 무변경)
│   └── confessions/, history/, theology/
├── modern/
│   └── source_manifest.schema.yaml                                           ← 신규(스키마만, 데이터 없음)
└── source_manifest.schema.yaml                                                ← 기존(v1.2, 무변경)
```

ADR-016/GOVERNANCE §5.3/§1이 기술한 구조(`authority/`, `modern/`
신설, `baptist/` 무변경)와 **완전히 일치**.

### Phase 6 — Backward Compatibility: **완료, PASS**

`scripts/source_validator.py` 실행 결과(수정 전과 동일 커맨드,
코드 미변경):

```
=== 결과 요약: PASS=21 WARNING=0 FAIL=0 ===
```

- 기존 v1.2 manifest(`baptist/source_manifest.yaml`)가 이번 작업
  전후로 **동일하게** 21 PASS/0 FAIL — 회귀 없음 확인.
- `modern/source_manifest.schema.yaml`과 `authority/*.yaml` 5개는
  파일명이 `source_manifest.yaml`이 아니므로 validator의 `rglob`
  탐색 대상에 애초에 포함되지 않음(실측 확인) — v1.2 검증 경로와
  물리적으로 간섭하지 않는다.
- **결론**: v1.2와 v2.1.0은 동시에 사용 가능하다(실측 근거 있음,
  추론이 아님).

---

## 3. 산출물 목록

| 파일 | 상태 |
|---|---|
| `resources/theological_sources/modern/source_manifest.schema.yaml` | 신규 |
| `resources/theological_sources/authority/authors.yaml` | 신규(빈 템플릿) |
| `resources/theological_sources/authority/works.yaml` | 신규(빈 템플릿) |
| `resources/theological_sources/authority/editions.yaml` | 신규(빈 템플릿) |
| `resources/theological_sources/authority/volumes.yaml` | 신규(빈 템플릿) |
| `resources/theological_sources/authority/sources.yaml` | 신규(빈 템플릿) |
| `docs/NAE_SOURCE_VALIDATOR_REQUIREMENTS_v1.md` | 신규 |
| `docs/NAE_SCHEMA_MIGRATION_GUIDE_v1.md` | 신규 |
| `docs/NAE_SCHEMA_MIGRATION_REPORT_001.md` | 신규(본 보고서) |

---

## 완료 조건 답변

1. **Schema v2.1.0 작성 완료 여부** — 완료(§2 Phase 1).
2. **Registry Template 완료 여부** — 완료, 5개 파일 전부 빈 템플릿, 실제 데이터 없음(§2 Phase 2).
3. **Validator 요구사항 완료 여부** — 완료, 코드는 미수정(§2 Phase 3).
4. **Migration Guide 완료 여부** — 완료, Rollback 절차 포함(§2 Phase 4).
5. **v1.2 ↔ v2.1.0 호환 여부** — **호환 확인(실측)**. `source_validator.py` 실행으로 v1.2 21건 PASS/0 FAIL 재확인, 신규 파일이 검증 경로에 물리적으로 간섭하지 않음(§2 Phase 6).
6. **전체 Metadata Migration을 시작할 준비가 되었는가?** — **아니오, 아직 아니다.** Infrastructure(Schema/Registry/Guide)는 준비됐으나, Migration Guide Step 3(Validator 실제 코드 확장)이 아직 착수되지 않았다 — 이 Step 자체가 코드 구현이라 별도 승인이 필요하다(이번 작업 범위 밖, 금지 사항 "Validator 코드 수정"). Step 3 없이는 v2.1.0 데이터가 실제로 자동 검증되지 않으므로, Corpus-wide Migration(Step 5)에 앞서 최소한 Step 3(Validator 구현)과 Step 4(Pilot 재검증)를 먼저 별도 승인·수행해야 한다.

---

## 로드맵 갱신

```
RAW Acquisition                ✅
Architecture Design            ✅
Governance                     ✅
Authority Plan                  ✅
Church Order Pilot             ✅
Fuller Multi-volume Pilot      ✅
Architecture Revision          ✅
Schema Migration (Infra)       ✅ (이번 작업 — 스키마/템플릿/가이드까지)
  └─ Validator 실제 구현        NEXT (별도 승인 필요, Migration Guide Step 3)
  └─ Pilot 재검증(실제 도구)     NEXT (Migration Guide Step 4)
Corpus-wide Metadata Migration  ⏳ (Step 3/4 완료 후, 별도 승인 필요)
TSU 생성                        ⏳
Embedding 생성                  ⏳
Benchmark                       ⏳
NAE Theology RAG                ⏳
```

---

*Corpus Metadata 생성, RAW 수정, OCR/TSU/Embedding 생성, Validator 코드
수정, Retrieval 수정, Registry 실제 데이터 입력, Corpus Migration, Git
Commit — 전부 수행하지 않음. `scripts/source_validator.py`는 검증
목적으로 **실행**만 했고 **수정**하지 않았다(git diff 없음, §2 Phase 6에서 확인).*
