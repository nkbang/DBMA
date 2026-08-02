# NAE Corpus Ingestion Standard v1 (Design Only)

작성일: 2026-08-02
상태: 설계 단계 — 미구현 (파일 이동/삭제/다운로드/OCR/TSU/Embedding/Retrieval 코드 변경 없음)
선행 검토: [`NAE_DATA_ARCHITECTURE.md`](NAE_DATA_ARCHITECTURE.md), [`NAE_MODERN_CORPUS_ARCHITECTURE_v1.md`](NAE_MODERN_CORPUS_ARCHITECTURE_v1.md), [ADR-001](architecture/ADR-001-Retrieval-Engine-Authority.md), [ADR-013](architecture/ADR-013-NAE-Vector-Store.md), [ADR-014](architecture/ADR-014-NAE-Modern-Corpus-Layer.md)

---

## 0. 목적

매번 전체 Architecture Review를 반복하지 않고, 신규 자료(침례교 신학서/현대 신학/주석/
설교집/선교/교회행정/연구자료)를 **정해진 등록 파이프라인**으로 처리하기 위한 운영 표준.
현재 43GB+ 확보된 NAE-PD와 설계된 NAE-MODERN(ADR-014) 양쪽에 공통 적용된다.

## 0.1 기존 Architecture 확인 요약 (Phase 1)

| 확인 항목 | 근거 문서 | 이번 설계에 적용 |
|---|---|---|
| RAW 구조 | `NAE_DATA_ARCHITECTURE.md` §1 — RAW는 immutable, `data/nae/sources/`(실 데이터) + `resources/theological_sources/`(manifest)로 분리 | 신규 자료도 이 원칙 그대로 따름 — 실물은 RAW 트리, 메타데이터만 manifest |
| Metadata 정책 | `source_manifest.schema.yaml` v1.2(PD) / v2.0.0(ADR-014) | Phase 3 스키마는 두 버전 모두와 호환되도록 설계 |
| TSU 경로 | `NAE_DATA_ARCHITECTURE.md` §3 — `DEFAULT_TSU_DATASET_PATH` 하드코딩 위험, `--dataset-path`로 해결됨(2026-07-31) | Phase 8에서 동일 위험 재확인 — ingestion 표준에도 명시적 경로 지정을 규칙화 |
| Retrieval Authority | ADR-001 — `core/retrieval.py::RetrievalEngine`이 유일 정본, TSU 기반 in-memory 검색, 영구 vector store 없음(SPRINT20-H-3 정정) | Phase 9 Authority Weight 설계 시 RetrievalEngine과의 미연결 상태(ADR-013)를 전제로 함 — 코드 변경 없음 |
| Domain Separation | ADR-014 §3.1 — NAE-PD / NAE-MODERN / DBMA 3영역 독립 | 등록 파이프라인은 항상 자료가 어느 영역에 속하는지 첫 단계(Registration)에서 결정 |

---

## Phase 2. Corpus Ingestion Lifecycle

```
New Source
   ↓
Registration      — 신규 source_id 발급, 영역(PD/Modern) 및 category 1차 지정
   ↓
Validation        — 필수 필드 존재, source_id 유일성, 파일 존재 확인
   ↓
Classification    — Phase 5 규칙에 따라 최종 category/subcategory 확정
   ↓
Metadata Creation — Phase 3 스키마로 manifest entry 작성
   ↓
Quality Check     — Phase 7 Quality Gate (PASS/WARNING/FAIL)
   ↓
Clean Processing  — 정제(추출/정규화), 기존 DBMA 파이프라인 재사용(core/processing.py 계열, 이번 설계는 호출 지점만 지정, 코드 변경 없음)
   ↓
TSU               — Phase 8 정책에 따라 Full/Restricted/Citation-only TSU 생성
   ↓
Embedding         — TSU 확정 자료만 진행 (bge-m3, 기존 파이프라인 재사용)
   ↓
Index Update      — Phase 9 정책에 따라 Retrieval에 노출 (Authority Weight 부여)
```

### 단계별 책임/입출력

| 단계 | 책임 주체 | 입력 | 출력 | 실패 시 |
|---|---|---|---|---|
| Registration | 등록자(사람) + 등록 스크립트(향후) | 원본 파일 + 서지정보 | `source_id`, 임시 manifest entry(`status: PREPARED`) | 진행 불가, 처음부터 재등록 |
| Validation | `source_validator.py`(확장 필요, Phase 3 참고) | manifest entry | PASS/FAIL | FAIL 시 Registration으로 반려 |
| Classification | 등록자 + Phase 5 규칙표 | manifest entry | 확정 `category`/`subcategory` | 충돌 시 Phase 5 §충돌 규칙 적용 |
| Metadata Creation | 등록자 | 확정 분류 + Phase 3 스키마 | 완성된 manifest entry(`status: ACQUIRED`) | 필드 누락 시 Validation으로 반려 |
| Quality Check | Phase 7 체크리스트(향후 자동화 가능, Phase 10) | 파일 + manifest | PASS/WARNING/FAIL | FAIL 시 Clean Processing 진입 차단 |
| Clean Processing | 기존 DBMA 처리 파이프라인 | 원본 파일 | 정제된 텍스트(`status: VERIFIED`) | 실패 로그만 남기고 이전 단계 유지(원본 불변) |
| TSU | 기존 TSU 빌더 + Phase 8 정책 | 정제 텍스트 + governance 필드 | TSU 레코드(`status: INGESTED`) | 저작권 필드 누락 시 TSU 생성 차단 |
| Embedding | 기존 embedding 파이프라인 | TSU 레코드 | 벡터 | — |
| Index Update | Retrieval 통합 절차(별도 ADR 필요, ADR-014 §5) | 벡터 + Authority Weight | 검색 가능 상태 | — |

이번 설계에서는 각 단계의 **정의와 순서만** 확립하며, 실제 코드/스크립트 구현은 하지 않는다.

---

## Phase 3. Source Registration Standard

### 필수 항목 (요청 스키마 그대로 + 기존 필드 매핑)

```yaml
source_id: string          # 기존 v1.2 필드 재사용, 유일성 검사 대상
author_id: string          # ADR-014 v2.0.0 신규 필드 재사용
work_id: string            # ADR-014 v2.0.0 신규 필드 재사용
title: string
edition: string            # ADR-014 v2.0.0 신규 필드 재사용
publication_year: integer  # v1.2의 year를 개명 계승(ADR-014와 동일)
language: string           # ADR-014 신규 필드 재사용
category: string           # Phase 5 taxonomy 값
subcategory: array[string] # Phase 5 taxonomy 값
source_type: licensed | purchased | personal | reference   # ADR-014 Task 2 재사용
copyright_status: public_domain | copyright_restricted | fair_use_reference | unknown  # ADR-014 재사용
usage_permission: full_text_storage | excerpt_only | metadata_only | citation_only     # ADR-014 재사용
```

### 기존 `source_manifest.schema.yaml` 호환성

- v1.2(NAE-PD)는 `license`(단일 문자열, `public_domain*` 값 체계)를 사용 — 위 스키마의
  `copyright_status`와 값 체계가 다르다. **PD 자료는 `license` 필드를 유지하고,
  Registration 시 `copyright_status=public_domain`을 파생값으로 자동 매핑**한다
  (양방향 재작성이 아니라 PD는 기존 필드가 canonical, 신규 필드는 파생).
- Modern 자료는 ADR-014의 `schema_version: "2.0.0"`을 그대로 따르므로 추가 매핑 불필요.
- 결론: **스키마를 통합하지 않고 버전별로 병행 — Registration 표준은 두 스키마 위에
  얹히는 공통 절차**로 정의한다(스키마 자체의 재작성/마이그레이션은 이번 범위 밖).

### Versioning

- manifest entry 자체는 버전을 갖지 않고, 동일 `work_id`의 서로 다른 `edition`이
  서로 다른 `source_id`로 등록된다(Phase 4 Edition Authority 참고).
- 스키마 버전(`schema_version`)은 파일(디렉토리) 단위로 고정 — v1.2 파일과
  v2.0.0 파일이 다른 디렉토리에 공존(기존 원칙 유지).

### ID 생성 규칙

```
source_id  = "{denomination|domain}-{genre}-{sequence}"     예: baptist-confession-001 (기존 관례 계승)
author_id  = "{surname}_{givenname}" 소문자, 언더스코어      예: gill_john
work_id    = "{author_id}-{title_slug}"                      예: gill_john-body_of_doctrinal_divinity
```

`source_id`는 기존 방식대로 유일성만 검사(포맷 강제 없음, v1.2 스키마 주석과 동일 원칙).
`author_id`/`work_id`는 신규 — Phase 4 Authority 병합의 키가 된다.

---

## Phase 4. Authority Management

### Author Authority

같은 인물의 표기 변형(`John Gill` / `John_Gill` / `Gill, John`)은 등록 시점에 자유
텍스트(`author_name`)로 어떻게 들어오든, **`author_id`(canonical)로 통합**한다.

```yaml
# authority/authors.yaml (설계 제안, 미생성)
- author_id: gill_john
  canonical_name: "John Gill"
  aliases: ["John_Gill", "Gill, John", "J. Gill"]
```

병합 규칙: 신규 자료 등록 시 `author_name`을 기존 `aliases` 목록과 대조(정규화: 소문자,
공백/구두점 제거 후 비교) → 일치하면 기존 `author_id` 재사용, 불일치하면 사람이 신규
등록 여부 확인(자동 병합 금지 — 동명이인 위험).

### Work Authority

동일 저작의 다른 판본(예: `A Body of Doctrinal Divinity` 1810판/1839판)은
**같은 `work_id`, 다른 `source_id`**로 등록한다. `work_id`는 저작 단위 묶음 키이고,
검색 결과에서 "이 저작의 다른 판본 보기" 기능의 근거가 된다(구현은 범위 밖).

### Edition Authority

```yaml
# authority/works.yaml (설계 제안, 미생성)
- work_id: gill_john-body_of_doctrinal_divinity
  canonical_title: "A Body of Doctrinal Divinity"
  editions:
    - source_id: baptist-theology-014
      edition: "1810"
    - source_id: baptist-theology-015
      edition: "1839"
```

판본 간 우선순위(어느 판본을 검색 기본값으로 노출할지)는 등록자가 수동 지정
(`preferred: true` 플래그, 설계만 — 기본은 최신 판본).

---

## Phase 5. Classification Rule

```
Public Domain: confession | systematic_theology | commentary | sermons | history | missions | church_order
Modern:        theology | commentary | sermons | missions | ministry | apologetics | reference
```

### 분류 충돌 처리 규칙

1. **PD/Modern 경계 충돌** (예: 저작권 만료 여부 불확실) — `copyright_status=unknown`으로
   등록하고 `usage_permission=metadata_only`로 잠정 처리, 사람 확인 전까지 Quality Gate에서
   WARNING 처리(Phase 7). 확정 전에는 Full TSU로 넘어가지 않는다.
2. **category 중복 후보** (예: 주석이면서 설교집인 자료) — `category`는 주된 성격 1개만,
   나머지는 `subcategory`(array)에 병기. PD의 `content_genre`도 array이므로 동일 패턴.
3. **PD `missions` vs Modern `ministry`(Missions)** — ADR-014에서 이미 분리 확정: PD
   missions=고전 선교 문헌/역사, Modern ministry/Missions=선교 실무 자료. 등록 시
   `publication_year` 기준 저작권 만료 여부로 1차 판별.

---

## Phase 6. Duplicate Detection Policy

### 구분

| 유형 | 정의 | 처리 |
|---|---|---|
| Exact Duplicate | 동일 파일(해시 일치) | 신규 `source_id` 미발급, 기존 entry에 `local_path` alias만 추가 |
| Same Work Different Edition | 같은 `work_id`, 다른 판본 | 별도 `source_id`, Phase 4 Edition Authority로 연결 |
| Different Scan Same Edition | 같은 edition, 다른 스캔본(품질/출처 상이) | 별도 `source_id`, `aliases`에 상호 참조 기록 + `notes`에 스캔 출처 명시 |
| Derivative OCR | 동일 원본의 OCR 재처리본 | 원본 `source_id`에 `derived_from` 필드(신규)로 연결, 별도 저작 취급 안 함 |
| Supplement Material | 부록/색인 등 원저작의 보충 자료 | 별도 `work_id` 부여하되 `related_work_id`(신규)로 원저작과 연결 |

### 원칙

- **삭제하지 않는다** — RAW immutable 원칙(`NAE_DATA_ARCHITECTURE.md` §"원칙 적용 확인")과 일치.
- 관계는 Authority Layer(Phase 4)의 `aliases`/`related_work_id`/`derived_from` 필드로만
  관리 — 파일 시스템 정리(이동/삭제)로 해결하지 않는다.
- 자동 중복 탐지(해시 비교 등)는 Phase 10 Automation 후보로만 제안, 이번 설계는 규칙 정의까지.

---

## Phase 7. Quality Gate

### 검사 항목

| 범주 | 항목 |
|---|---|
| File | PDF 존재, TXT 존재, hOCR 존재, 파일 손상(0바이트/열기 실패) 여부 |
| OCR | OCR 품질 점수(임계치는 후속 정의), 페이지 누락(PDF 페이지 수 vs TXT 페이지 마커 수), 문자 오류율(비정상 문자 비율) |
| Metadata | 필수 필드(Phase 3) 전부 존재, Authority 연결(`author_id`/`work_id`가 Phase 4 authority에 등록됨) |

### 평가

```
PASS    — 전 항목 통과, Clean Processing 진입 가능
WARNING — 일부 항목 미충족이나 진행 가능(예: hOCR 없음, OCR 품질 애매) — 사람 확인 후 진행
FAIL    — 필수 항목 미충족(파일 손상, 필수 필드 누락, source_id 중복) — Registration으로 반려
```

구체적 임계값(OCR 품질 점수 기준 등)은 실제 샘플 데이터로 보정 필요 — 이번 설계는
검사 항목과 3단계 판정 체계까지만 확정한다.

---

## Phase 8. TSU Integration Policy

| 자료 유형 | TSU 방식 |
|---|---|
| Public Domain | Full TSU — 원문 청크 전체를 payload에 포함 |
| Modern Licensed(`usage_permission=excerpt_only`) | Restricted TSU — 발췌 범위만 payload, 전문 미포함 |
| Modern(`usage_permission=metadata_only`/`citation_only`) | Citation Only TSU — 원문 청크 없이 서지정보+위치 정보만 |

### 필요 Metadata (TSU payload에 전파)

```yaml
tsu_access: full | restricted | citation_only
citation_policy: string       # 인용 시 표기 형식 지정(저자/제목/출판사/연도/페이지)
source_restriction: source_manifest의 access_control 값을 그대로 전파
```

Quality Gate를 통과(PASS/WARNING)하고 `copyright_status`가 `unknown`이 아닌 자료만
TSU 단계 진입 — `unknown`은 Phase 5 §1 규칙에 따라 사람 확인 전까지 보류.
경로 충돌 방지: TSU 생성 시 항상 명시적 `--dataset-path` 사용(§0.1 참고, 이번
설계는 규칙화만, 실행 없음).

---

## Phase 9. Retrieval Integration Policy

### Authority Weight (기본 우선순위)

```
Primary Baptist Source (1차 사료, PD confession/theology)
   >
Historical Source (PD history/church_order)
   >
Modern Interpretation (Modern theology/commentary, licensed)
   >
Application Resource (Modern ministry/apologetics)
```

### 검토 결과

- **Source Priority**: 위 4단계 고정 랭킹을 기본값으로 하되, `tsu_access=citation_only`
  자료는 랭킹과 무관하게 본문 노출 없이 서지 정보만 반환(ADR-014 Task 7과 동일 원칙).
- **Domain Filter**: PD/Modern/DBMA 3영역은 항상 독립 필터로 노출 — 사용자가 명시적으로
  "현대 자료 포함" 옵션을 켜지 않는 한 기본 검색은 PD만 대상으로 한다(ADR-014 §Task 7 계승).
- **Index Update 시점**: TSU + Embedding이 완료되고 `access_control≠no_redistribution`인
  자료만 Index Update 단계 진입. `RetrievalEngine`(ADR-001) 자체 코드는 이번 설계에서
  변경하지 않으며, 실제 통합 시점에는 별도 ADR이 필요하다(ADR-014 §5 계승).

---

## Phase 10. Automation Candidate (제안만, 미구현)

| 후보 | 설명 |
|---|---|
| Metadata validation | `source_validator.py` 확장 — v1.2/v2.0.0 양쪽 스키마 + Phase 3 신규 필드 검사 |
| Duplicate detection | 파일 해시 비교로 Exact Duplicate 자동 탐지, Same Edition 여부는 제목+저자 유사도로 후보 제시(최종 판단은 사람) |
| File inspection | PDF/TXT/hOCR 존재 여부, 파일 손상 자동 체크(Phase 7 File 범주) |
| Category suggestion | 제목/목차 키워드 기반 Phase 5 category 후보 제시(확정은 사람) |
| OCR quality scoring | 문자 오류율/페이지 누락 자동 계산 → Phase 7 OCR 범주 채점 |

모두 제안 단계 — 이번 작업에서 스크립트를 작성하거나 실행하지 않는다.

---

## 최종 판단 기준에 대한 답

1. **새 책 추가 첫 단계**: Registration — `source_id`/`author_id`/`work_id` 발급 및 PD/Modern 영역 결정(Phase 2/3).
2. **저자명 표기가 다르게 들어오면**: Author Authority(`authority/authors.yaml`)의 `aliases`와 정규화 비교 후 기존 `author_id`로 통합, 불일치 시 사람이 동명이인 여부 확인(Phase 4).
3. **같은 책의 다른 판본**: 동일 `work_id`, 별도 `source_id`로 등록하고 `authority/works.yaml`의 `editions` 목록으로 연결(Phase 4).
4. **현대 저작권 자료 보호**: `source_type`/`copyright_status`/`usage_permission`/`access_control` 4필드로 등록 시점부터 관리, `no_redistribution`은 기본 `metadata_only`, TSU 단계에서 Restricted/Citation Only로 반영(Phase 3/8, ADR-014 계승).
5. **TSU Pipeline 진입 시점**: Quality Gate PASS/WARNING 통과 + `copyright_status≠unknown` 확정 후(Phase 7→8).
6. **Retrieval Index 추가 시점**: TSU+Embedding 완료 및 `access_control≠no_redistribution` 확인 후, Authority Weight(Phase 9) 부여와 함께 노출.

상세 결정 사항은 [`ADR-015-NAE-Corpus-Ingestion-Standard.md`](architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md) 참고.
