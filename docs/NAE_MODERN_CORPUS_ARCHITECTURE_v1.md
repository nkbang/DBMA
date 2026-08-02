# NAE Modern Corpus Architecture v1 (Design Only)

작성일: 2026-08-02
상태: 설계 단계 — 미구현 (디렉토리 생성/데이터 확보/TSU/Embedding/Retrieval 코드 변경 없음)
선행 검토 문서: [`docs/NAE_DATA_ARCHITECTURE.md`](NAE_DATA_ARCHITECTURE.md) — 기존 RAW/Processed/TSU/Vector DB 경로 원칙을 그대로 계승한다.

---

## 0. 전제: 세 영역의 독립

```
NAE-PD (Public Domain Corpus)     — 구축 완료. resources/theological_sources/, NAE/corpus/raw/archive_org/
NAE-MODERN (Modern Research Layer) — 이번 설계 대상. 신규 트랙, NAE-PD 대체 아님.
DBMA (Personal Ministry Archive)   — core/, data/RAW/. 별도 유지.
```

세 영역은 저장 위치, registry, retrieval 가중치가 각각 독립적이다. 이번 설계는 NAE-MODERN 신설만 다루며 나머지 두 영역의 기존 구조를 변경하지 않는다.

---

## Task 1. Modern Corpus Directory Architecture

### 최상위 구조

```
NAE/corpus/raw/
├── public_domain/     ← 기존 archive_org/를 의미상 이 이름 아래로 재분류(실제 이동은 별도 승인 필요, 이번 설계는 명명만 제안)
└── modern/
```

`docs/NAE_DATA_ARCHITECTURE.md`의 원칙에 따라 RAW는 `NAE/corpus/raw/` 트리 하나로 유지하고, `resources/theological_sources/`에는 modern 자료의 manifest(메타데이터)만 둔다. 실물 텍스트/PDF는 RAW 쪽에만 존재 — public_domain과 동일 패턴.

### modern/ 하위 구조 (제안 검토 결과: 원안 채택 + 1개 조정)

```
modern/
├── theology/
├── commentary/
├── sermons/
├── missions/
├── ministry/
├── apologetics/
└── reference/
```

검토 의견:
- 원안 7개 카테고리는 Task 4~6의 taxonomy(신학/주석/목회)와 1:1 대응되므로 그대로 채택.
- `ministry/`는 Task 6(Ministry Resource Taxonomy)의 6개 하위축(Preaching/Discipleship/Leadership/Counseling/Church Administration/Missions)과 `missions/`가 일부 중복된다 — **missions는 최상위 폴더(고전 선교 문헌·역사)로, ministry/missions는 "선교 실무 자료"로 의미를 분리**해 둘 다 유지한다(자료가 늘면서 재조정 여지는 남김).
- 폴더명은 값이 아니라 라우팅용 디렉토리이며, 실제 분류의 근거(source of truth)는 metadata(Task 3)이다 — 폴더 배치와 metadata가 어긋나면 metadata를 기준으로 한다.

---

## Task 2. Source Governance

### 구분 (source_type)

| 값 | 의미 |
|---|---|
| `licensed` | 출판사/저작권자로부터 이용권을 별도 취득 |
| `purchased` | 개인/기관이 정가 구매(전자책, 실물 스캔 등) |
| `personal` | 개인 소장 자료(설교노트, 강의안 등 제3자 저작권 없음) |
| `reference` | 인용/참조만 허용되는 자료(전문 저장 불가, 서지사항+발췌만) |

### 필드

```yaml
copyright_status: public_domain | copyright_restricted | fair_use_reference | unknown
usage_permission: full_text_storage | excerpt_only | metadata_only | citation_only
source_type: licensed | purchased | personal | reference
access_control: internal_only | user_only | no_redistribution
```

- `resources/theological_sources/source_manifest.schema.yaml`의 기존 `license` 필드(NAE-PD용, `public_domain*` 값 체계)는 그대로 두고, modern 전용 manifest에 위 4개 필드를 **추가** 필드로 둔다 — 기존 스키마 재작성이 아니라 병행.
- `access_control=no_redistribution`인 자료는 원문 텍스트를 RAW/Processed 어디에도 저장하지 않고 `metadata_only`로만 관리하는 것을 기본값으로 한다(저작권 리스크 최소화). 예외는 개별 승인 필요.

---

## Task 3. Metadata Schema

기존 `resources/theological_sources/source_manifest.schema.yaml`(schema_version 1.2)과 호환되도록 설계 — 기존 필드(`source_id`, `title`, `author`, `year`→`publication_year`, `content_genre`, `status` 등)를 재사용하고 modern 전용 필드를 추가한다.

```yaml
# resources/theological_sources/modern/{category}/source_manifest.yaml (신규 파일, 기존 스키마 확장)
schema_version: "2.0.0"   # NAE-PD 1.2와 구분되는 버전 — 혼동 방지

sources:
  - author_id: string          # 신규: 저자 canonical ID (동일 저자 다권 저작 묶음용)
    author_name: string        # 기존 author 대체
    work_id: string            # 신규: source_id와 별도로 "저작" 단위 식별(동일 저작의 개정판/역서 묶음)
    title: string
    edition: string            # 신규
    publication_year: integer  # 기존 year 대체
    publisher: string          # 신규
    language: string           # 신규 (ko/en/grc/heb 등 — CLAUDE.md 헬라어/히브리어 처리 고려)
    category: string           # modern/ 하위 7개 디렉토리 중 1
    subcategory: array[string] # Task 4/5/6 taxonomy 값
    theological_position: string   # 신규 (예: Reformed, Dispensational, Baptist Evangelical)
    denomination: string       # 신규
    source_type: licensed | purchased | personal | reference   # Task 2
    copyright_status: public_domain | copyright_restricted | fair_use_reference | unknown  # Task 2
    usage_permission: full_text_storage | excerpt_only | metadata_only | citation_only      # Task 2
    access_control: internal_only | user_only | no_redistribution                            # Task 2
    topics: array[string]
    scripture_reference: array[string]   # 예: ["Rom.8", "Eph.2:8-10"]
    doctrine_tags: array[string]         # 기존 theological_category 필드와 값 체계 공유
    status: PREPARED | ACQUIRED | VERIFIED | INGESTED | approved_for_acquisition | permission_required | verification_pending  # 기존 enum 그대로 재사용
    source_id: string          # 기존 필드, 유일성 검사 대상 그대로 유지
    local_path: string
    aliases: array[string]
```

기존 `scripts/source_validator.py`는 NAE-PD manifest(`resources/theological_sources/baptist/...`)만 검사 대상으로 하드코딩되어 있을 가능성이 높다(`docs/NAE_DATA_ARCHITECTURE.md`에서 확인된 "RAW 감시 스크립트가 `data/RAW`만 하드코딩" 패턴과 동일 위험). Modern manifest를 검증 대상에 포함시키려면 별도 확장이 필요 — 이번 설계에서는 **발견만 하고 구현하지 않는다.**

---

## Task 4. Modern Theology Taxonomy

```
Systematic Theology
Biblical Theology
Historical Theology
Apologetics
Ethics
Ecclesiology
Missiology
Pastoral Theology
```

원안 그대로 채택. `doctrine_tags`(Task 3)는 이 8개 중 하나 이상을 값으로 가지며, NAE-PD의 `theological_category`(confession/ecclesiology/soteriology/missions)와는 별도 축이므로 직접 매핑하지 않는다 — 필요 시 상위 표에서만 대응 관계를 문서로 남긴다.

---

## Task 5. Modern Commentary Taxonomy

두 축의 조합으로 분류(단일 enum이 아니라 배열):

```
범위: OT | NT | Whole Bible
성격: Exegetical | Theological | Pastoral
```

예: 「로마서 강해(주경적·목회적)」 → `subcategory: [NT, Exegetical, Pastoral]`

---

## Task 6. Ministry Resource Taxonomy

```
Preaching
Discipleship
Leadership
Counseling
Church Administration
Missions
```

원안 채택. `ministry/` 디렉토리(Task 1) 하위 자료의 `subcategory` 값으로 사용.

---

## Task 7. Retrieval Architecture 영향 분석

`docs/NAE_DATA_ARCHITECTURE.md` §5 결론(단일 Chroma 인스턴스 원칙)과 ADR-013(NAE 전용 Qdrant `nae_qdrant`, `core/retrieval.py::RetrievalEngine`과 미연결)을 전제로 분석한다.

| 항목 | NAE-PD | NAE-MODERN | DBMA |
|---|---|---|---|
| 검색 우선순위 | 원전/1차 사료 — 교리사·확증 인용 우선순위 최상위 | 최신 연구·해석 보조 — PD 인용과 충돌 시 PD를 authoritative로, modern은 "현대적 해석" 라벨 부기 | 개인 목회 적용 — 별도 authority 트랙, PD/modern과 혼합 랭킹하지 않음 |
| Metadata filtering | `content_genre`, `tradition` | `copyright_status`, `usage_permission`, `access_control`이 **1차 필터**(검색 전에 `no_redistribution`+`metadata_only`는 본문 미노출) | 없음(개인 자료) |
| Source weighting | 고정 가중치(공개 검증된 원전) | `theological_position`/저자 신뢰도에 따라 가변 가중치 — 아직 신뢰도 스코어 체계 없음, 별도 설계 필요 | N/A |
| Authority ranking | 최상위(1차 사료) | PD보다 낮은 기본 가중치, 사용자가 명시적으로 "최신 연구 포함" 옵션을 켤 때만 동률 검색 | 별도 트랙(개인 자료는 authority 랭킹 대상 아님, 참고용으로만 표시) |

**핵심 리스크**: `core/retrieval.py::RetrievalEngine`은 현재 NAE-PD/DBMA 어느 쪽과도 아직 통합되지 않은 상태([[project_charter_qdrant_conflict]], ADR-013)다. 세 영역을 한 번에 통합 검색하는 기능은 이번 설계 범위 밖이며, **modern 자료를 위한 retrieval 코드 변경은 이번 작업에서 수행하지 않는다** — 명령서 제한 사항 준수.

---

## Task 8. TSU Pipeline 영향 분석

| 검토 항목 | 결론 |
|---|---|
| 동일 TSU Schema 사용 가능 여부 | 가능 — NAE-PD와 동일한 `TSU_SCHEMA_VERSION` 체계(`NAE.pipeline.tsu.config`) 재사용. TSU 레코드 구조 자체는 저작권과 무관하므로 스키마 분기 불필요. |
| 추가 metadata 필요 여부 | 필요 — TSU 레코드 payload에 `copyright_status`/`usage_permission`/`access_control`을 전파해야 한다. 그래야 벡터 검색 결과 단계에서도(TSU 이후 단계에서도) 저작권 필터링이 유지된다. 현재 NAE-PD TSU 스키마에는 이 필드가 없음 — 확장 필요(이번 설계는 요구사항 식별까지만). |
| 저작권 제한 처리 | `usage_permission=metadata_only`/`citation_only`인 자료는 TSU 생성 단계에서 원문 청크를 payload에 포함하지 않고 서지 정보 + 출처 위치만 남기는 "citation-only TSU" 변형이 필요 — 별도 TSU 서브타입으로 설계 검토 필요(미구현). |
| Citation 방식 | 표준 서지 포맷(저자, 제목, 출판사, 연도, 페이지)을 TSU payload의 `citation` 필드로 통일 부여 — NAE-PD도 동일 필드를 갖도록 하면 modern 전용 분기 없이 공통 처리 가능. |

**경로 충돌 주의**: `docs/NAE_DATA_ARCHITECTURE.md` §3에서 확인된 `DEFAULT_TSU_DATASET_PATH` 하드코딩 문제(2026-07-31 `--dataset-path` 옵션으로 이미 해결됨)와 동일한 패턴이 modern corpus를 TSU화할 때도 재발할 수 있다 — modern 전용 TSU 산출 시 반드시 `--dataset-path`를 명시해 NAE-PD/DBMA 운영 TSU를 덮어쓰지 않도록 한다.

---

## Task 9. Modern Corpus 구축 우선순위 제안

| 우선순위 | 기준 | 예시 카테고리 |
|---|---|---|
| Priority 1 | 설교 준비 필수 | modern/sermons, modern/ministry(Preaching), 최신 주석(modern/commentary — Exegetical+Pastoral) |
| Priority 2 | 신학 연구 필수 | modern/theology(Systematic/Biblical), modern/apologetics |
| Priority 3 | 장기 연구 자료 | modern/reference, modern/theology(Historical), modern/missions |

우선순위는 자료 확보 착수 순서를 위한 가이드일 뿐이며, 이번 작업 범위(설계)에서는 실제 확보를 진행하지 않는다.

---

## Task 10. 관계 정리 — 기존 로드맵과의 연결

기존 NAE-PD 로드맵([[project_nae_corpus_builder_roadmap]]):

```
Corpus Collection → Audit → Metadata → TSU → Embedding → Benchmark
```

NAE-MODERN은 이 파이프라인을 대체하지 않고 **동일 파이프라인을 modern 자료에도 적용 가능하도록 병행 확장**하는 별도 Architecture Track이다. NAE-PD는 현재 단계(Phase 5 Benchmark 대기)를 그대로 진행하며, 이번 설계는 그 진행을 지연시키지 않는다.

상세 결정 사항은 [`docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md`](architecture/ADR-014-NAE-Modern-Corpus-Layer.md) 참고.
