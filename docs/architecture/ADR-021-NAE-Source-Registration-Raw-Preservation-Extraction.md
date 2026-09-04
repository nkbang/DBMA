---
title: "ADR-021: NAE Source Registration → Raw Preservation → Extraction (Upstream Ingestion Layer v1)"
category: architecture
based_on:
  - docs/NAE_CORPUS_INGESTION_STANDARD_v1.md
  - docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md
  - docs/architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md
  - docs/architecture/ADR-020-NAE-Incremental-Ingestion-Architecture.md
  - docs/NAE_METADATA_GOVERNANCE_v1.md
created: 2026-08-11
revised: 2026-08-13 (Approved — Phase A~F 전체 완료, Final Evidence Freeze 통과)
scope: 신규 모듈 NAE/pipeline/registration/ (구현 완료, Phase A~D). 기존
  NAE/pipeline/canonical/*, NAE/pipeline/tsu/*, NAE/pipeline/ingest/*,
  NAE/pipeline/index/*, NAE/pipeline/embed/*, NAE/collectors/*,
  core/dataset_registry.py 무수정 — 전량 재사용만.
---

# ADR-021: NAE Source Registration → Raw Preservation → Extraction (Upstream Ingestion Layer v1)

| | |
|---|---|
| Status | **Approved** (2026-08-13, 4개 조건 — 구현완료/회귀PASS/C1리뷰/사용자승인 — 전부 충족) |
| Date | 2026-08-11 (최초), 2026-08-11 (FINAL-DRAFT 개정) |
| Deciders | Rev. Bang, CUE |
| Extends | ADR-020(Incremental Ingestion, downstream 절반 — 이미 Approved/GREEN) |
| Formalizes | `NAE_CORPUS_INGESTION_STANDARD_v1.md`(설계 단계, 2026-08-02)의 Phase 2 "Registration → Validation → Classification → Metadata Creation → Quality Check" 구간을 코드로 승격 |
| Supersedes | — |
| Superseded by | — |

**Evidence Before Promotion Rule 적용**: 본 ADR은 구현 완료·회귀 테스트
통과·C1 독립 리뷰(1차 CONDITIONAL GREEN 완료, 2차 Final Review 대기)·사용자
승인 4개 조건을 모두 충족하기 전까지 Proposed 상태를 유지하며, 다른 구현의
근거로 사용하지 않는다. 이번 개정에서도 **즉시 Approved로 전환하지 않는다**
— 구현이 아직 없기 때문.

---

## 1. Context

ADR-020(Approved, GREEN GATE)은 **TSU 레코드가 이미 Production에 존재하는
시점부터** 시작하는 downstream 절반(hash 판정 → state → embedding → Qdrant
append)만 다룬다. ADR-020 §12는 이렇게 명시했다:

> "discovery→registration→OCR→first-TSU 파이프라인은 out of scope"

이 앞단은 `NAE_CORPUS_INGESTION_STANDARD_v1.md`(2026-08-02)가 **절차/스키마
수준으로는 이미 설계**되어 있으나(Phase 2~10, Registration ID 규칙·Authority
Model·Quality Gate·TSU Integration Policy까지 확정), **코드로 구현된 적은
없다**.

본 ADR의 목적은 그 설계 문서의 Phase 2~7(Registration/Identity/Raw
Preservation/Extraction까지)을 **코드로 승격**하는 것이다. Phase 8(TSU
Integration)부터는 기존 `NAE/pipeline/tsu/builder.py`와 ADR-020의
`NAE/pipeline/ingest/`를 그대로 호출·재사용하며, 이 두 하위 시스템의
코드는 수정하지 않는다.

## 2. Decision — Pipeline Shape

```
NEW SOURCE (Public-Domain 원자료)
       ↓
Source Registration        — source_id/author_id/work_id/edition_id 발급
       ↓
Identity Resolution        — Authority registry 대조 (§4, 자동 병합 금지)
       ↓
Raw Preservation            — 체크섬 기록 + 원본 immutable 취급 (§6)
       ↓
Source Validator             — Raw/Metadata/Provenance/Integrity 검사 (§5)
       ↓
Extraction Adapter          — 기존 extract.py 그대로 호출 (§7)
       ↓
Quality Gate                 — PASS/WARNING/FAIL (§8)
       ↓
Registration Manifest + Audit/Evidence
       ↓
(TSU Builder / ADR-020 incremental pipeline로 인계 — 본 ADR 범위 밖)
```

기존 `NAE/pipeline/canonical/*`, `NAE/pipeline/tsu/builder.py`,
`NAE/collectors/archive_org/*`, `core/dataset_registry.py`는 **코드
무수정, 호출만** 한다. ADR-020 downstream(`NAE/pipeline/ingest/*`,
`NAE/pipeline/embed/*`, `NAE/pipeline/index/*`)도 무수정.

## 3. 재사용 vs 신규

| 구성요소 | 상태 | 처리 |
|---|---|---|
| ID 생성 규칙 | 설계 확정(`NAE_CORPUS_INGESTION_STANDARD_v1.md` Phase 3) | 그대로 구현 |
| `source_manifest.schema.yaml` v1.2 | 기존 스키마 존재 | 재사용, 값 자체는 무수정 |
| Author/Work/Edition Authority | 설계만, 파일 미생성 | 신규 생성 (Option C, §4) |
| OCR/텍스트 추출 | `extract.py` 완전 구현·재사용 중 | **무수정 재사용** |
| Raw 디렉토리 구조 | `NAE/corpus/raw/archive_org/{category}/{work}/` 관례 | 그대로 계승 |
| Immutability 강제 | 정책만 존재(코드 강제 없음) | **신규**, §6 |
| Duplicate Detection | 규칙 설계만(Phase 6) | **신규**, 2계층, §9 |
| Quality Gate | 항목/판정 체계 설계만(Phase 7) | **신규**, §8 |
| Source Validator | 미분리 | **신규 module**, §5 |
| Dataset Isolation | `core/dataset_registry.py` 기존 구현 | 재사용 |
| Archive.org 수집 | `collector.py` 완전 구현 | 재사용(선택적 전단계) |

## 4. Identity & Authority Strategy — Option C 확정

```
Author(author_id) → Work(work_id) → Edition(edition_id) → Source File(source_id)
```

ID 포맷: `NAE_CORPUS_INGESTION_STANDARD_v1.md` Phase 3 그대로
(`{surname}_{givenname}`, `{author_id}-{title_slug}`,
`{work_id}-{edition_slug}`). 충돌 시 숫자 suffix + notes 기록(자동 침묵
덮어쓰기 금지). Batch 번호는 identity로 사용하지 않는다(ADR-020 §3 원칙
계승).

### Authority Seed = Option C (최종 확정)

```
Legacy 3,319 Authority
        │
        ▼
Read-only Legacy Authority Snapshot   (NAE/authority/legacy_snapshot/)
        │
        │  READ ONLY — 신규 ingestion의 write target 아님
        ▼
New Authority Registry                (NAE/authority/{authors,works}.yaml)
        │
        ├── Author
        ├── Work
        ├── Edition
        └── Source File
```

규칙:
- 기존 3,319 TSU에서 신규 Authority registry를 **역산하지 않는다**(Option
  A 기각 — 동명이인/오타가 verified TSU에 소급 반영될 위험).
- Legacy snapshot은 **reference/audit 전용**, 코드 경로상 어떤 쓰기
  작업도 이 디렉토리를 대상으로 하지 않는다(리뷰/디버깅 시 사람이 읽는
  용도).
- 신규 registry는 **빈 상태로 시작**(Option B 요소를 채택하되, 운영
  병목은 legacy snapshot을 참고자료로 열람 가능하게 해서 완화 — Option B
  단독의 결점 회피).
- Author/Work 병합은 **항상 사람 확인**, 자동 병합 금지(동명이인 위험).

### Legacy Authority Snapshot 생성 방법 (Phase A 착수 전 확정)

```python
# 개념 스펙 — Phase A 구현 시 정확한 스크립트로 구체화
1. NAE/corpus/tsu/{Hiscox_Standard_Manual,Dagg_Church_Order}/tsu.json을
   READ-ONLY로 로드
2. review_status와 무관하게(verified/generated/rejected 전부) author_id/
   work_id/edition_id/source_id 조합을 집계
3. NAE/authority/legacy_snapshot/{authors,works}.yaml 로 1회성 write
   (생성 스크립트 자체는 이후 재실행해도 같은 입력이면 같은 출력 —
   deterministic, 그러나 "생성"은 1회만 수행하고 이후 수정하지 않음)
4. 생성 완료 후 파일 권한을 §6과 동일한 read-only 취급으로 전환
5. 생성 로그를 Evidence로 남긴다: 입력 파일 해시, 출력 파일 해시,
   레코드 수, Production TSU 파일 무변경 확인(전/후 해시 비교)
```

이 과정 자체가 Production TSU/Qdrant/기존 Authority에 어떤 쓰기도
가하지 않는다 — 순수 파생 생성물이다.

## 5. Source Validator — 신규 module, TSU Validator와 경계 분리

C1 권고에 따라 upstream 전용 Source Validator를 **신규 module로 분리**한다
(§12.3의 이전 결정 "기존 `source_validator.py` 확장"을 이번 개정에서
재검토한 결과, C1이 지적한 대로 upstream 검사 범위(Raw/Metadata/
Provenance/Integrity)가 기존 `scripts/source_validator.py`의 책임(등록된
manifest entry의 필드 존재/유일성 검사)과 성격이 달라 **분리가 더
명확함** — 아래 §16 결정사항 기록 참고, 최종 결정은 신규 module).

```
Source Validator (신규, NAE/pipeline/registration/source_validator.py)
    ↓
Raw / Metadata / Provenance / Integrity 검사
    ↓
Extraction
    ↓
TSU Validator (기존, 무수정)
    ↓
TSU schema / structural validation
```

- 기존 `scripts/source_validator.py`(manifest 필드 검사)는 **무수정** —
  이 신규 module과 나란히 존재하되 호출 관계 없음(각자 다른 시점 검증).
- 신규 module의 검사 항목: raw 파일 존재/체크섬 일치, 필수 identity
  필드 존재, provenance(archive_source 등) 존재 여부, 파일 무결성(0바이트/
  손상 여부).

## 6. Raw Preservation Enforcement (실측 조사 결과 반영)

### 기존 갭
"RAW immutable"은 `NAE_DATA_ARCHITECTURE.md`의 **정책**일 뿐, 이를 어기는
것을 막는 코드가 저장소에 없었다(Discovery 확인 완료, 이전 세션).

### 조사한 enforcement 방법과 각각의 한계

| 방법 | 실효성 | 한계 |
|---|---|---|
| `chmod 0o444`(read-only 권한) | 낮음 — 실수 방지용 | 파일 소유자/root가 언제든 `chmod`로 복원 가능. **immutability를 증명하지 않는다** — 감사 시 "권한이 444였다"는 "내용이 안 바뀌었다"의 증거가 아니다. |
| macOS `chflags uchg`(불변 플래그) | 낮음~중간 | root로 해제 가능, 파일시스템 종속(APFS 외 이식성 낮음), Python 표준 라이브러리로 다루기 어려움(별도 `chflags` 서브프로세스 필요) — Phase A 범위에서 채택하지 않음(과도한 복잡도 대비 낮은 실익) |
| Git-annex/DVC 같은 content-addressable storage | 높음 | 신규 인프라 의존성 추가, 기존 `NAE/corpus/raw/` 관례와 단절, Phase A 범위를 크게 벗어남 — **채택하지 않음**, 후속 검토 후보로만 기록 |
| **체크섬 기반 접근 시점 재검증(채택)** | **실제로 검증 가능** | 권한/플래그와 무관하게 "내용이 등록 시점과 같은가"를 매 접근마다 수학적으로 증명 — 유일하게 감사 가능한 방법 |

### 채택 설계: Content Verification, Not Permission Enforcement

**핵심 원칙**: "OS 권한이 immutability를 보장한다"고 주장하지 않는다.
대신 **매 접근 시점에 체크섬을 재계산해 등록 시점 값과 비교**하는 것을
유일한 실질적 무결성 근거로 삼는다.

```
1. Registration 완료 시 SHA256 계산 → manifest entry `raw_checksum` 필드
   + append-only ledger(NAE/pipeline/registration/state/
   raw_checksum_ledger.jsonl, 매 계산 결과를 append만 — 덮어쓰기 금지)에
   기록
2. Extraction/재실행/재검증 등 원본 파일에 접근하는 모든 지점에서 SHA256을
   재계산하고 ledger의 최초 기록과 비교
3. 불일치 → 즉시 FAIL, `RAW_CHECKSUM_MISMATCH` 상태로 전이(§10),
   quarantine/exception 경로로 이관(§11) — 자동 복구/재다운로드 없음
4. `chmod 0o444`는 **보조 수단으로만** 유지(사고 방지 수준, 문서에 한계
   명시) — 실질 보장은 항상 체크섬 재검증이 담당
5. ledger가 append-only이므로, 파일 내용이 조용히 바뀌어도 최초 기록과의
   비교에서 반드시 드러난다 — ledger 자체의 변조는 Git 이력(ledger도
   git-tracked)으로 별도 감지 가능
```

이 설계의 한계도 명시한다: 만약 원본 파일과 ledger가 **동시에** 함께
조작된다면 이론상 감지 불가 — 이는 완전한 cryptographic tamper-proofing이
아니라 **실수/사고성 변경에 대한 감사 가능한 방어**임을 인정한다(threat
model: 실수로 인한 덮어쓰기·손상, 악의적 변조에 대한 완전한 방어는 범위
밖).

## 7. Extraction Adapter

기존 `NAE/pipeline/canonical/extract.py`(hOCR 우선 → OCR TXT → PDF
fallback)를 **코드 무수정**으로 호출한다. 이 모듈은 이미 "원본을 읽기만
하고 결과는 별도 경로(`NAE/corpus/canonical/`)에 쓰는" 원칙을 따르고
있음을 확인함(Discovery 완료, 수정 불필요) — §6의 raw immutability
원칙과 이미 정합.

## 8. Quality Gate — Conservative / Warning-First (최종 확정)

```
RAW → Extraction → Quality Gate → { PASS | WARNING | FAIL }
```

### FAIL (치명적 integrity 오류만, 초기 구현 범위 고정)

```
- Raw file missing
- Raw checksum mismatch
- Extraction output missing
- Zero-page extraction
- Unreadable/corrupt source
- Required identity unavailable (author_id/work_id/edition_id/source_id 중 하나라도 없음)
- Required metadata missing (Phase 3 필수 필드)
```

FAIL 자료는 Production TSU로 전달하지 않고 quarantine/exception으로
이관한다(§11).

### WARNING (초기에는 비차단, 사람 확인 후 진행 가능)

```
- Low OCR confidence
- Partial OCR degradation
- Abnormal character ratio
- Possible page-count discrepancy
- Encoding anomalies
- 기타 non-fatal extraction quality concerns
```

**중요**: 초기 OCR confidence/문자 오류율 등의 구체적 수치 임계값은 이번
FINAL-DRAFT에서도 확정하지 않는다 — 첫 dry-run(§13 후보)의 실측 데이터를
확보한 뒤 결정한다. 임계값 없이도 FAIL 목록(치명적 오류)만으로 Quality
Gate 자체는 동작 가능하도록 설계했다 — WARNING 항목은 "탐지는 하되
차단하지 않음"이 초기 동작.

## 9. Duplicate Detection — 2계층

Collector catalog 수준의 dedup(기존 `NAE/collectors/archive_org/filters.py`
등)에 의존하지 않는다.

```
Level 1 — Source identity / catalog duplicate
  동일 archive_identifier 또는 동일 source_id 재등록 시도 → 신규 source_id
  미발급, 기존 entry에 local_path/archive alias만 추가

Level 2 — Raw content checksum duplicate
  §6의 raw_checksum_ledger 전체(모든 기존 source, 파일명/식별자 무관)를
  대상으로 신규 파일의 SHA256을 대조 → 다른 파일명/다른 identifier로
  유입된 동일 content도 탐지
```

Duplicate로 판정되어도 **자동 삭제하지 않는다**(Phase 6 "삭제하지
않는다" 원칙 계승):

```
DUPLICATE → quarantine/disposition (사람이 최종 판단) → provenance 보존
```

## 10. Failure Isolation — State Machine

ADR-020 §5 `ProcessingState` 패턴을 계승하되 **완전히 별도의 파일/네임스페이스**로
분리한다(ADR-020의 downstream state machine은 무변경):

```
NAE/pipeline/registration/state.py (신규, ADR-020 state.py와 별개 모듈)

DISCOVERED → REGISTERED → RAW_PRESERVED → VALIDATED → EXTRACTED → QUALITY_PASSED
실패:
  REGISTRATION_FAILED
  RAW_CHECKSUM_MISMATCH
  EXTRACTION_FAILED
  QUALITY_GATE_FAILED
```

상태 저장소: `NAE/pipeline/registration/state/registration_state.json`
— ADR-020의 `NAE/pipeline/ingest/state/incremental_state.json`과 물리적으로
별도 파일. 한 source의 실패가 다른 source의 등록을 막지 않는다.

## 11. Exception Queue Integration

```
FAIL (§8) → NAE/pipeline/registration/state/exception_queue.json (신규)
```

- 이 신규 큐는 `NAE/review/human/exception_queue.json`(Production Human
  Review용, ADR-020/기존 Batch 프로세스가 사용)과 **물리적으로 완전히
  분리**한다 — upstream(TSU 존재 이전) 실패가 downstream(TSU 존재 이후)
  Production review 큐를 오염시키지 않도록 명확히 경계를 긋는다.
- 큐 엔트리 구조(개념): `{source_id, failure_state, reason, timestamp,
  raw_path, checksum_at_failure}`.
- 사람이 이 큐를 검토해 재시도(원본 재확보 후) 또는 영구 반려(레코드
  보존, §6 원칙대로 raw 파일 자체는 삭제하지 않음) 결정.
- ADR-020의 `ProcessingState`/`incremental_state.json` 코드는 이번 ADR
  구현에서 **임의로 변경하지 않는다**.

## 12. Dataset Isolation

신규 source 등록 시 `core/dataset_registry.py`에도 함께 등록한다
(`TrustTier`/`LicensePolicy` 부여). 기존 3,319 verified TSU가 속한
dataset과는 별도 `dataset_id`로 등록해 명시적으로 분리 — 병합은 Human
Review 완료 후 별도 절차(현재 보류 중)에서만 수행.

## 13. Dry-run Candidate Investigation (조사만, 다운로드/등록 없음)

C1 권장 검색 조건(`possible-copyright-status:"Public" AND ocr:"hocr" AND
(language:kor OR language:eng)`, 1900년 이전 한국 관련 Protestant
missionary 문서, 50페이지 이하)으로 Archive.org를 조회한 결과, 아래 3개
후보를 확인했다. **실제 다운로드/등록/ingestion은 수행하지 않았다.**

### Candidate 1
```
Title: Forward mission movement in North Korea
Author: Daniel L. Gifford (1861-1900)
Work/Edition: 단권, 1897년판 단일 인쇄로 추정(추가 판본 확인 안 됨)
Archive identifier: forwardmission00giff
Public-domain evidence: 출판연도 1897 (미국 저작권 보호 기간 상한인 1928년
  이전 출판 — 공개영역 추정 근거, possible-copyright-status 필드 자체는
  검색 결과에 비어있어 Registration 단계에서 재확인 필요)
Page count: 36 pages (imagecount)
OCR availability: 있음
OCR format: hOCR(forwardmission00giff_hocr.html, 824,806 bytes) +
  djvu.txt(36,643 bytes)
Raw download URL: https://archive.org/download/forwardmission00giff/
Identity collision check: 기존 3,319 TSU의 author_id는 {dagg_john_l,
  hiscox_edward_t} 뿐 — Gifford와 충돌 없음(확인 완료)
Expected extraction path: NAE/corpus/raw/archive_org/missions/
  Forward_Mission_Movement_North_Korea/ (제안, 최종은 Phase A 등록 시 확정)
```

### Candidate 2
```
Title: Mrs. Esther Kim Pak, Korea's first woman doctor
Author: Rosetta Sherwood Hall
Work/Edition: 단권, [19--?] 추정 발행
Archive identifier: mrsestherkimpakk00hall
Public-domain evidence: 저작 시기 20세기 초(정확한 연도 미상, Registration
  단계에서 possible-copyright-status 직접 재확인 필요)
Page count: 18 pages
OCR availability: 있음
OCR format: hOCR(mrsestherkimpakk00hall_hocr.html, 594,821 bytes) +
  djvu.txt(23,160 bytes)
Raw download URL: https://archive.org/download/mrsestherkimpakk00hall/
Identity collision check: author_id 후보 "hall_rosetta_sherwood" —
  기존 corpus와 충돌 없음(확인 완료)
Expected extraction path: NAE/corpus/raw/archive_org/missions/
  Esther_Kim_Pak_Korea_First_Woman_Doctor/ (제안)
```

### Candidate 3
```
Title: Kim Chang Sik : a Korean circuit rider
Author: (metadata에 명시적 creator 없음 — Registration 단계에서 확인 필요,
  Methodist Episcopal Church 계열 출판물로 추정)
Work/Edition: 단권, [190-?] 추정
Archive identifier: kimchangsikkorea00unse
Public-domain evidence: 20세기 초 추정(정확한 연도/저자 미상 — Quality
  Gate에서 "Required metadata missing"으로 FAIL 처리될 가능성 있음, 이
  경우가 바로 §8 FAIL 경로의 실제 검증 사례가 될 수 있어 dry-run
  후보로서 오히려 유용)
Page count: 10 images (가장 짧음)
OCR availability: 있음
OCR format: hOCR(kimchangsikkorea00unse_hocr.html, 127,203 bytes) +
  djvu.txt(5,343 bytes)
Raw download URL: https://archive.org/download/kimchangsikkorea00unse/
Identity collision check: 충돌 없음(확인 완료)
Expected extraction path: NAE/corpus/raw/archive_org/missions/
  Kim_Chang_Sik_Korean_Circuit_Rider/ (제안)
```

**추천 순위**: Candidate 1(Gifford) — 저자/연도/출처가 가장 명확해 정상
경로(PASS/WARNING) 검증에 적합. Candidate 3(Kim Chang Sik)은 저자
정보 결여로 FAIL 경로(Required metadata missing) 검증에 유용 — 두 건을
함께 사용하면 Quality Gate의 PASS/WARNING/FAIL 세 경로 중 최소 두 개를
첫 dry-run에서 실증할 수 있다. 최종 선정은 Phase A 착수 시 사용자 확인.

## 14. Dry-run Isolation Rule

```
Phase A dry-run
        ↓
Qdrant mutation = 0
        ↓
Existing 3,319 verified TSU unchanged
        ↓
TSU Builder 호출 직전에 정지 (Quality Gate 결과까지만 확인)
```

dry-run은 manifest/raw/state 파일만 생성하고, TSU 레코드 생성이나
ADR-020 incremental pipeline 호출은 별도 승인 후로 미룬다.

## 15. Phase A 구현 범위

```
포함:
  Source Registration
  Identity Resolution
  Raw Preservation
  Source Validation
  Extraction Adapter
  Quality Gate
  Registration Manifest
  Audit/Evidence

제외(Phase A에서 하지 않음):
  ❌ 기존 3,319 TSU 재처리
  ❌ 기존 3,319 embedding
  ❌ 기존 Qdrant indexing
  ❌ index_all()
  ❌ Human Review 776 promotion
  ❌ Production corpus migration
```

## 16. 신규 Package (module 분할, 조정 가능)

```
NAE/pipeline/registration/
    identity.py           — source_id/author_id/work_id/edition_id 발급, 충돌 처리
    source_validator.py   — 신규 upstream validator (§5, 기존 scripts/source_validator.py와 별개)
    raw_preservation.py   — 체크섬 기록/재검증, duplicate detection (§6, §9)
    authority.py          — Author/Work Authority 대조, legacy snapshot 참조 (§4)
    manifest_writer.py    — source_manifest.yaml entry 작성/갱신
    state.py               — 상태 머신 + exception queue (§10, §11)
    quality_gate.py        — PASS/WARNING/FAIL (§8)
    pipeline.py             — 오케스트레이션, extract.py/tsu builder 호출 지점 연결
```

실제 module 분할은 구현 착수 시 기존 repository convention을 재검토해
조정 가능 — 불필요한 module 증식은 피한다.

## 17. Test Specification (구현 전 확정, Phase A 착수 시 그대로 사용)

| 영역 | 최소 커버리지 |
|---|---|
| Identity | 정상 발급, 충돌 시 suffix 부여, 필수 필드 누락 감지 |
| Raw checksum | 최초 기록, 재검증 일치, 재검증 불일치(FAIL 전이) |
| Raw preservation | ledger append-only 동작(덮어쓰기 안 됨), read-only 권한 부여 확인 |
| Duplicate detection | Level 1(동일 identifier), Level 2(동일 content 다른 파일명) |
| Source validation | Raw/Metadata/Provenance/Integrity 각 항목 PASS/FAIL |
| Extraction adapter | 기존 extract.py 호출 결과 그대로 전달(mock 기반, 실제 파일 불필요) |
| Quality Gate | PASS/WARNING/FAIL 3판정 각각, FAIL 목록 7개 항목 개별 검증 |
| FAIL → quarantine | 상태 전이 확인, 원본 파일 미삭제 확인 |
| Exception queue | 엔트리 기록, `NAE/review/human/exception_queue.json`과 물리적 분리 확인 |
| Authority separation | legacy snapshot 읽기전용, 신규 registry에 legacy 내용 미유입 확인 |
| Manifest generation | entry 스키마 준수, 유일성 검사 |
| Idempotent re-run | 동일 source 재실행 시 중복 생성 없음 |
| Dry-run isolation | **불변식**: dry-run 실행 후 Qdrant points_count 불변, 기존 3,319 TSU ID셋 불변(§14) |
| Baseline protection | 전체 테스트 스위트 실행 전후 `NAE/corpus/tsu/`, Qdrant 상태 하시 비교 |

fake client/isolated fixture 사용(ADR-020 패턴 계승), Production 파일에
실제 접근하지 않는다.

## 18. Evidence Before Promotion Sequence

```
Implementation → Unit tests → Integration tests → Dry-run →
Evidence Package → C1 Independent Audit → User Approval → Production promotion
```

이 순서를 임의로 단축하지 않는다. 본 ADR은 현재 "Implementation" 이전
단계(설계 확정, C1 Final Review 대기)다.

## 19. 절대 금지 (본 ADR 구현 범위 전체)

- `NAE/pipeline/canonical/*`, `NAE/pipeline/tsu/*`, `NAE/pipeline/ingest/*`,
  `NAE/pipeline/index/*`, `NAE/pipeline/embed/*` 코드 수정
- 기존 3,319 verified TSU / Qdrant 3,319 vector에 대한 어떤 재처리도 수행
- OCR 엔진 자체 구현
- Human Review disposition 구조(776건, 현재 보류 중) 설계
- 자동 병합(Author/Work Authority)
- C1 Final Review 이전 구현 코드 작성(단, interface spec/test spec 문서는
  작성 가능 — 본 ADR §16/§17이 그 결과물)

## 20. Compliance

- ADR-001/013/015/016/020 미충돌 — §11(이전 개정)과 동일 판단 유지.
- Architecture Freeze Rule: 본 ADR은 Proposed/FINAL-DRAFT이며, Approved로
  승격되기 전까지 어떤 기존 Approved ADR도 변경/우회하지 않는다.

---

## 21. 결정 이력

| 일자 | 사건 | 결과 |
|---|---|---|
| 2026-08-11 | ADR-021 최초 작성 | Proposed |
| 2026-08-11 | C1 1차 독립 리뷰 | CONDITIONAL GREEN (4개 조건) |
| 2026-08-11 | 사용자 승인 | Authority=Option C / Quality Gate=WARNING우선 / dry-run=C1권장조건 / validator=신규 module(최종, §5) |
| 2026-08-11 | FINAL-DRAFT 개정(본 문서) | §4~§17 전면 구체화, dry-run 후보 3건 조사 완료 |
| 2026-08-11 | C1 Final Review 1차 제출 | GREEN, 단 Baseline Protection 수치 오류 발견(Generated 776→4,893 오기, Qdrant nae_tsu_v1 3,319→0 오기) — CUE가 직접 재측정으로 대조 후 재감사 요청 |
| 2026-08-11 | C1 재감사 제출 | 오류 원인 규명(전역 tsu.json 탐색으로 backup/migration 혼입, 잘못된 로컬 임베디드 Qdrant 경로 조회) 및 정정. 정정값(verified=3319/generated=776/rejected=22/total=4117, Qdrant nae_tsu_v1 points=3319)이 CUE 직접 재측정과 정확히 일치 — **FINAL: GREEN** |
| 2026-08-11 | Phase B/C 구현 | `NAE/pipeline/registration/` 8개 모듈(commit `b1ebc3a`), smoke test 6건 106/106 PASS |
| 2026-08-11 | Phase E/F FREEZE | CUE는 dry-run/Evidence 생성 보류, C1 독립 Phase E/F 감사 대기(`NAE_ADR021_PHASE_E_READINESS_FREEZE_001.md`) |
| 2026-08-12 | C1 Phase E 1차 dry-run | 3개 후보 전부 EXTRACTION_FAILED. CUE가 evidence 교차대조로 "OCR 레이어 부재"가 아니라 dry-run staging이 hocr.html/ocr.txt를 배치하지 않은 test fixture 문제임을 규명(사용자 확인) |
| 2026-08-12 | C1 Phase E 2차 재실행(hOCR staging 보완) | gifford(29p, PASS)·kim(6p, PASS)·hall(metadata 누락, QUALITY_GATE_FAILED — 정상 동작) — `extraction_source` 필드로 hOCR 경로 실사용 확인. 최소 1개(실제 2개) 후보에서 PASS 도달 — **GREEN 승격 조건 충족**(commit `5ed5562`) |
| 2026-08-12 | Phase D 전체 커버리지 | ADR-021 §17 14개 영역 커버 테스트 36건 추가(총 42/42 PASS), evidence generator 추가(commit `de8eeb7`). CUE가 안전성(Production 읽기전용, 쓰기는 자체 output만) 직접 검증 후 커밋 |
| 2026-08-12 | Git governance 교정 | `output/adr021_phase_ef_evidence/`가 실수로 git 추적 상태였음을 CUE가 발견, `.gitignore` 예외 규칙 제거 + `git rm --cached`로 untrack(history rewrite 없음, commit `b9d8865`). 동일 편집에서 발생한 `.gitignore` 병합 실수(`output/`+`output_sav/`→`output/output_sub/`)도 같은 커밋에서 자체 발견·수정 |
| 2026-08-12 | Phase F 1차 감사 — Evidence Freshness FAIL 발견 | CUE가 evidence 디렉토리를 감사하는 도중 다른 프로세스가 실시간으로 파일을 재작성하는 것을 직접 관측(경쟁 writer). 한 스냅샷에서 `production_integrity.json`이 `qdrant_reachable=false`이면서도 `production_mutation=false`를 주장하는 자기모순 발견 — Final Approval을 HOLD 처리 |
| 2026-08-13 | Phase F Final Evidence Freeze | 단일 writer 원칙으로 `scripts/generate_adr021_final_evidence.py` 신설(commit `6c1d9cd`) — staging에서 전량 생성 후 manifest.json을 마지막에 계산, atomic move로 발행. hall의 서술을 "register_source extraction = NOT_REACHED(Source Validation이 Extraction보다 먼저 실행되어 도달하지 않음), 별도 direct hOCR test에서만 15p 확인"으로 정정. 재실행 결과: production_integrity PASS(Qdrant reachable, points=3319, TSU SHA256 일치), regression 142/142, FAIL-path 8/8(이전 in_exception_queue 오차 수정됨), manifest↔disk 완전 일치, 3초 재해시 드리프트 0 — **Self-consistency PASS** |
| 2026-08-13 | ADR-021 Approved 승격 | Evidence Before Promotion Rule 4개 조건(구현완료/회귀PASS/C1독립리뷰/사용자승인) 전부 충족 확인 |

**FINAL STATUS: Approved. Phase A~F 전체 완료 — Legacy Authority
Snapshot(Phase A), `NAE/pipeline/registration/` 8개 모듈(Phase B/C),
전체 테스트 커버리지 42건(Phase D), hOCR 경로 실증 PASS 2건(Phase E),
Final Evidence Freeze로 governance 문제 교정 및 self-consistency 검증
완료(Phase F). Production mutation 0, 기존 3,319 verified TSU / Qdrant
3,319 vector 불변.**
