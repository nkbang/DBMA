# 침례교 주석(Commentary) Reference 트랙 임베딩 계획 v1

- 작성일: 2026-09-12
- 작성자: CUE
- 승인: HQ (본 작업 지시 자체가 승인) — 원본 다운로드 단계만 별도 승인 대기
- 트랙: **Reference**(TSU 아님) — ADR-013 collection 격리, ADR-028 Smith Reference Layer 패턴 재사용
- 선례: Smith Bible Dictionary (`nae_ref_v1`, 34,948 chunks, F3 인간검수 없이 처리, [메모리: Reference Dictionary TSU Mismatch])
- 관련: `docs/architecture/ADR-013-NAE-Vector-Store.md`, `docs/architecture/ADR-028-NAE-Smith-Reference-Layer.md`

---

## 0. 이 문서가 하는 일 / 하지 않는 일

**한다:**
- 후보 5개 침례교 주석 저작을 기록하고 파일럿(Spurgeon Vol.1)을 확정한다.
- 기존 Smith reference 파이프라인을 **일반화**해 두 번째 격리 컬렉션(`nae_ref_commentary_v1`)을 지원하도록 코드를 준비한다(이번 세션에서 구현·테스트 완료).
- 시편 해설의 절 단위(chapter:verse) 청킹 규칙을 설계·구현한다(구현 완료, fixture 테스트 통과).
- Smith 활성화 과활성 문제(CON-006/PB-08)를 좁히는 옵션을 플래그 뒤에 준비한다(구현 완료, 기본값 off).
- 원본 확보에 필요한 정확한 파일 정보를 사용자에게 제시한다.

**하지 않는다:**
- 원본 텍스트를 다운로드하지 않는다 (사용자 승인 필수 — §5).
- `nae_ref_commentary_v1`에 실제 데이터를 upsert하지 않는다 (원본 없음).
- `corpus_admissions.jsonl`에 실제 항목을 추가하지 않는다 (초안만 §4).
- Smith의 기존 동작을 변경하지 않는다 (모든 신규 동작은 기본값 off 플래그 뒤에 있음, 회귀 테스트로 확인).
- Citation 모델(`core/retrieval.py::Citation`)을 변경하지 않는다 — ADR-028 §10 "Smith는 citation badge로 노출하지 않는다"는 원칙을 이 작업도 그대로 따른다.

---

## 1. 후보 저작 5개 (기록용, 실행은 Spurgeon Vol.1만)

| 저자 | 저작 | 침례교 계열 | Public Domain | 비고 |
|---|---|---|---|---|
| **C.H. Spurgeon** | The Treasury of David (전 7권) | Particular Baptist | Yes (1885년경 완간) | **파일럿 = Vol.1 (시편 1–26편)**. 시편 전체 해설, 분량 방대(전권 ~3,500쪽) |
| John Gill | An Exposition of the Old and New Testament | Particular Baptist | Yes (1746–1763) | 신구약 전체 주석, 분량 매우 방대(Spurgeon보다 큼). 향후 후보 |
| A.T. Robertson | Word Pictures in the New Testament | Southern Baptist | Yes (1930년, 저자 사후 저작권 만료국 확인 필요 — 미국은 1930 출간이라 최근까지 저작권 존재 가능성, 별도 확인 필요) | 헬라어 원어 해설 포함 — DBMA 헬라어 처리 요구사항과 정합 |
| John A. Broadus | Commentary on Matthew (American Commentary) | Southern Baptist | Yes (1886) | 마태복음 단권 주석 |
| B.H. Carroll | An Interpretation of the English Bible | Southern Baptist | Yes (1913, 저자 사후 출간 1916–1917) | 17권 시리즈, 설교체 주석 |

**파일럿 선정 근거**: Spurgeon Vol.1은 (a) 확실한 public domain, (b) 시편 26편으로 분량이 관리 가능, (c) 절 단위 구조가 명확(시편 장:절별 해설)해 신규 청킹 규칙 검증에 적합, (d) 이미 §3에서 확인한 기존 scripture-reference 감지기(`NAE/pipeline/canonical/annotate.py::find_scripture_references_extended`)와의 정합성을 테스트하기 좋다.

**A.T. Robertson 저작권 주의**: 1930년 출간 저작은 저작권 갱신 여부에 따라 현재도 저작권이 살아있을 수 있다(미국 1928년 이전 출간만 확정적 public domain — CLAUDE.md 기준과 별개로 실제 법적 판단 필요). Robertson을 추가 파일럿으로 진행하기 전 별도로 저작권 상태를 재확인해야 한다. 이번 파일럿에서는 다루지 않는다.

---

## 2. 파이프라인 재사용 지도 — 무엇을 새로 만들고 무엇을 재사용했는가

기존 확인: `NAE/pipeline/reference/`는 이미 존재하는 모듈(2026-09-07 커밋, Smith Vol1-4 처리 시 생성)이며 "신설"이 아니라 **일반화 대상**이었다. 아래는 실제로 변경한 파일과 그 방식이다.

| 파일 | 변경 전 | 변경 후 | 방식 |
|---|---|---|---|
| `NAE/pipeline/reference/config.py` | `REFERENCE_COLLECTION_NAME = "nae_ref_v1"`만 존재 | `COMMENTARY_COLLECTION_NAME = "nae_ref_commentary_v1"` + `KNOWN_REFERENCE_COLLECTIONS` 튜플 추가 | additive, 기존 상수 무변경 |
| `NAE/pipeline/reference/chunker.py` | `chunk_canonical()` (heading+prose, Smith 사전용) | `chunk_canonical_verse_anchored()` 신규 함수 추가 | additive 함수, 기존 함수 무변경. `ReferenceChunk`에 `scripture_reference: str \| None = None` 필드 추가(기본값 None → 기존 호출부 영향 없음) |
| `NAE/pipeline/reference/ingest.py` | `ingest()`가 `config.REFERENCE_COLLECTION_NAME`/`chunker.chunk_canonical`을 하드코딩 | `collection_name`/`chunker_fn`/`content_type` 키워드 인자 추가, 기본값을 기존 하드코딩 값으로 고정 | 시그니처 확장, 기본 인자로 하위호환 보장. `_ensure_ref_collection`/`_build_payload`/`_build_point`도 파라미터화 |
| `NAE/reference_retrieval_adapter.py::search_reference()` | `ref_config.REFERENCE_COLLECTION_NAME` 하드코딩 단일 컬렉션 검색 | `collection_names: list[str] \| None = None` 추가(기본 None → 기존과 동일하게 Smith 컬렉션만), 다중 컬렉션이면 점수 기준 병합 | 시그니처 확장, 기본값 유지 |
| `NAE/smith_activation.py::should_activate_smith()` | 신학 개념어 매칭 시 무조건 True | `NAE_SMITH_ACTIVATION_NARROW=true`일 때만 "짧은 질의가 아니면 개념어 단독 매칭 제외" | 플래그 게이트, 기본 false = 기존 동작 100% 동일 (회귀 테스트로 확인) |
| `scripts/nae_commentary_ingest.py` | 없음(신규) | Smith 스크립트를 복붙하지 않고 `ref_ingest.ingest()`를 `collection_name=COMMENTARY_COLLECTION_NAME`, `chunker_fn=chunk_canonical_verse_anchored`로 호출하는 얇은 CLI | 코드 재사용, 로직 중복 없음 |

**핵심 재사용**: 시편 장:절 검출은 **새 정규식을 만들지 않았다**. `NAE/pipeline/canonical/annotate.py::find_scripture_references_extended()`가 모든 문서의 canonicalization 단계에서 이미 각 문단의 `scripture_references` 필드(예: `{"original": "Ps. i. 1", "canonical": "PS 1:1"}`)를 채운다 — TSU의 `verse_mapping`이 쓰는 것과 동일한 감지기다. `chunk_canonical_verse_anchored()`는 이 필드를 소비만 한다.

---

## 3. 활성화 배선(§3) — CON-006/PB-08 인지 및 처리 방침

작업 중 `should_activate_smith()`의 신학 개념어 목록이 정의 질의가 아닌 일반 신학 대화에도 광범위하게 True를 반환하는 과활성 문제를 확인했다(다른 세션의 감사 초안 `DBMA_NAE_PROPOSAL_CONFLICT_REGISTER_v1.md` CON-006/PB-08과 동일 관측 — 해당 문서는 아직 커밋되지 않은 별도 worktree 산출물이며 본 계획서가 그 결론에 종속되지는 않으나, 독립적으로 동일 현상을 재현·확인함).

**중요한 경계 확인**: CON-006이 다루는 문제는 "Smith 결과를 정식 Citation으로 승격"(ADR-028 §10과 충돌 — Smith는 citation badge 없는 silent background layer로 못박혀 있음)이며, 이번 작업은 그 문제를 다루지 않는다. 이번에 구현한 것은 **활성화 임계값 좁히기**(citation 모델 무변경, UI 표시 무변경)로, ADR-028 §10과 충돌하지 않는다.

**구현 내용**: `NAE_SMITH_ACTIVATION_NARROW=true` 환경변수(기본 false)로 게이트. 개념어 단독 매칭(고유명사·정의패턴 없음)이 15자를 초과하는 질의에서는 비활성화 — 짧은 사전형 질의("은혜란?")는 그대로 활성화되고, 긴 서술형 신학 대화("믿음으로 산다는 것이...")에서의 배경 주입만 억제한다. `_CONCEPT_ONLY_MAX_QUERY_LEN = 15`는 경험적 기본값이며 실측 데이터 없이 정한 판단값 — 파일럿 운영 후 조정 필요.

**결정하지 않은 것**: 이 플래그를 언제 기본값 on으로 전환할지는 HQ 판단 사항이다. 이번 세션은 코드만 준비했다(기본 off, 회귀 없음 확인).

---

## 4. `corpus_admissions.jsonl` 초안 (미기록 — 승인 후 실제 등록)

```json
{"source_id": "BAP-COMM-SPURGEON-TDA-VOL01", "decided_by": "David / HQ", "date": "TBD", "track": "reference", "authority_class": "reference", "content_genre": ["commentary"], "tradition": "Particular Baptist", "rationale": "PENDING — 원본 확보 전 초안. ADMIT for reference-track embedding via nae_ref_commentary_v1 (Smith Bible Dictionary 선례 재사용, F3 인간검수 없이 처리). Public domain 추정(1885년경 완간) — 실제 확보 파일의 출판연도/출처 확인 후 rationale 갱신 필요. TSU 트랙 아님 — ADR-030 TSU-track 심사 대상 아님.", "evidence_refs": ["docs/BAPTIST_COMMENTARY_EMBEDDING_PLAN_v1.md", "NAE/authority/works.yaml"]}
```

**주의**: 위 항목은 초안이며 `NAE/governance/corpus_admissions.jsonl`에 실제로 추가하지 않았다. `date`는 원본 확보·HQ 최종 결재 시점으로 채워야 한다. 기존 원장의 다른 항목(Fuller Vol04-08 등)과 달리 `track: "reference"`를 사용 — 기존 원장에 `"track": "tsu"` 외 값이 실제로 쓰인 선례가 있는지는 확인하지 못했다(Smith 자체가 이 원장에 등록되어 있는지도 미확인 — 아래 §6 확인 필요 항목 참고).

`NAE/authority/works.yaml`은 현재 `works: []`로 비어 있다(ADR-021 §4 Option C). Smith도 아직 이 파일에 등록되지 않은 것으로 보인다 — 이 작업만의 문제가 아니라 기존 관례 확인이 필요한 사항이다.

---

## 5. 원본 확보 — 진행 기록 (2026-09-12, 사용자 승인 후 실행)

사용자가 "다운로드 진행하라"로 승인한 뒤 실제로 진행한 내용과, 그 과정에서 계획을 두 번 수정해야 했던 이유를 기록한다.

### 5.1 1차 시도 — CCEL, 실패 (사용 불가로 판명)

CCEL(`https://ccel.org/ccel/spurgeon/treasury1`)에서 PDF를 받았으나(46.6MB, 235쪽, SHA256 `e4c204bb...`), 직접 열어 확인한 결과:
- CCEL 메타데이터에 `dc:subject: ImagesOnly`로 명시돼 있었고,
- 실제로 각 페이지가 텍스트 레이어 없는 스캔 이미지였다(`fitz`로 페이지 텍스트 추출 시 거의 빈 값).
- 이 프로젝트의 `NAE/pipeline/canonical/extract.py::extract_pages()`는 **자체 OCR을 수행하지 않는다** — hOCR/djvu.xml/OCR TXT 중 하나가 이미 존재해야만 추출이 가능하고, 없으면 PDF 텍스트 레이어에 최후 수단으로 의존한다. CCEL 자료엔 그 어느 것도 없어 사실상 사용 불가.
- 파일은 `NAE/corpus/raw/ccel/reference/Spurgeon_TreasuryOfDavid_Vol1/treasury1.pdf`에 남아있다(gitignored, 무해하나 미사용).

### 5.2 2차 시도 — archive.org, 성공

기존 Smith Bible Dictionary/Fuller 전량이 archive.org 소스였다는 점(예: 모든 raw_path가 `NAE/corpus/raw/archive_org/...`)을 뒤늦게 확인하고 archive.org에서 동일 저작·동일 권(Psalms I–XXVI)의 스캔본을 검색했다:
- Identifier: `treasuryofdavid0001chsp_d1s7` (I.K. Funk & Co., 1882, "volume: 1", imagecount 510)
- 시편 범위 확인: OCR 텍스트에서 "PSALM THE FIRST"부터 "PSALM THE TWENTY-SIXTH"까지만 등장 — CCEL판과 동일하게 시편 1–26편 한정, 확인 완료.
- 받은 파일: `hocr.html`(49.1MB, archive.org 자체 OCR 산출물)과 `original.pdf`(40.3MB) → `NAE/corpus/raw/archive_org/reference/Spurgeon_TreasuryOfDavid_Vol1/`
- SHA256(hocr.html): `a1d7df0d15e03c9cccbb91db925317f1d881e33a528fd9886052b9211d17ed85`

### 5.3 Canonicalization 실행 결과

`python -m NAE.pipeline.canonical.runner --identifier Spurgeon_TreasuryOfDavid_Vol1` 실행(기존 파이프라인 그대로, 코드 변경 없음): source=hocr, 510페이지, 4,145 문단, scripture_references 535건 검출, 상태 "ok". 산출물은 `NAE/corpus/canonical/Spurgeon_TreasuryOfDavid_Vol1/`(gitignored, 로컬에만 존재).

### 5.4 청킹 dry-run에서 발견한 정확도 버그 — 수정 완료

실제 canonical.json으로 `chunk_canonical_verse_anchored()`를 검증하던 중, 문단의 **첫 번째** scripture_reference를 앵커로 삼는 최초 구현이 잘못된 결과를 냈다: Spurgeon의 해설문은 종종 논의 중인 시편 구절은 재인용하지 않고(“Verse 2.—…”만 씀) 대신 지지 근거로 다른 책을 인용한다(“…as in Prov. xii. 26…”). 그 결과 시편 4편 해설 청크가 `scripture_reference="Proverbs 12:26"`처럼 **엉뚱하게 태깅**되었다 — 다른 세션 감사 문서의 CON-003(verse_mapping 오매핑)과 정확히 같은 부류의 결함.

**수정**: `chunk_canonical_verse_anchored(..., anchor_book_prefix="Psalms")` — 앵커 후보를 "Psalms"로 시작하는 참조로만 제한(이 파일럿은 시편 전용 주석이므로 다른 책 인용은 정의상 지지 근거이지 본문 대상이 아님). `anchor_book_prefix=None`이면 기존(첫 참조) 동작으로 폴백 — 여러 책을 다루는 주석에 대비.

**수정 후 실측**(실제 1,978개 청크): Psalms 앵커 1,627개(82%), 미태깅(anchor=None) 351개(18%, "Verse N.—"만 있고 장 번호를 안 반복하는 절), **잘못된(non-Psalms) 앵커 0개**. 정밀도 우선 원칙에 따라 "모른다(None)"가 "틀리게 안다"보다 낫다고 판단 — 18% 커버리지 갭은 남겨두고 문서화한다. 개선 여지(heading의 "PSALM {roman}"과 본문의 "Verse {N}"을 결합해 자체 합성)는 새 정규식 도입이 필요해 이번 파일럿 범위 밖으로 남긴다.

회귀 테스트 3건 추가(`test_incidental_cross_reference_does_not_override_anchor` 등), 전체 19개 통과.

### 5.5 발견한 거버넌스 충돌 — 구현 중단, 사용자 확인 필요 (CUE Operating Policy Architecture Freeze Rule)

RAW 체크섬 등록을 위해 `NAE.pipeline.registration.cli_driver`(ADR-021)를 `--production`으로 실행해 `BAP-COMM-SPURGEON-TDA-VOL01`을 등록했다(QUALITY_PASSED, page_count=500). 그 직후 `tests/test_m2_source_registry_governance.py` 전체를 돌려보니 7건이 깨졌다:

- `source_manifest.yaml`("M2")은 **ADR-030 v2.1 §7.3의 승인된 고정 스냅샷**이다 — 테스트가 `len(sources) == 14`, `authority_class` 구성이 정확히 `historical_witness×10 + reference×4`(2종류만), `tradition` 채워진 레코드 정확히 10개, `theological_category` 채워진 레코드 정확히 5개임을 **하드코딩된 값**으로 검증한다. [메모리: ADR-030 A-2a-PREP → M-5 CLOSED]에 이미 "HQ FINAL=ACCEPTED/FROZEN BASELINE"으로 기록돼 있었다 — 이번 작업 시작 전에 먼저 확인했어야 할 사항이었다.
- 신규 소스를 15번째로 추가하면 `reference` 카운트가 4→5로 바뀌어 `test_authority_class_matches_adr030_7_3`이 깨진다. 이는 Fuller Vol01-08 추가 때처럼 "카운트를 같이 올리면 되는" 사안이 아니라, ADR-030이 명시적으로 종료 선언한 baseline의 구성 자체를 바꾸는 일이다.
- 부가로 `NAE.pipeline.registration.manifest_writer.write_entry()`가 YAML을 다시 덤프하면서 파일 상단의 `# ROLE: Source Registry SSOT (ADR-030 §8)...` 헤더 주석을 지워버리는 것도 확인했다(별도 버그, 이 도구로 M2를 다시 쓸 때마다 재발함).

**조치**: `source_manifest.yaml` / `raw_checksum_ledger.jsonl` / `registration_state.json`에 대한 쓰기를 **즉시 git checkout으로 되돌렸다** — 세 파일 모두 git 추적 대상이라 되돌림이 정확함을 diff로 확인. 회귀 테스트 스위트가 원상태로 복귀함을 확인(2,955 passed — 남은 2건은 이번에 raw 파일을 받아 `NAE/corpus/raw/`가 생기면서 활성화된, 이 워크트리에 다른 12개 소스의 raw 파일이 애초에 없다는 **환경 완전성 갭**이며 내 되돌림과 무관).

**막힌 지점**: RAW 원본 확보(§5.1-5.3, 완료)와 canonicalize(완료, §5.3)까지는 코드/문서 산출물이지만, **"체크섬 등록"은 ADR-030이 동결한 M2 파일에 새 레코드를 추가하는 일이라 사용자 승인 없이 진행할 수 없다.** 두 가지 선택지:

- **옵션 A**: ADR-030 Amendment(또는 신규 ADR)로 M2에 Reference-track 신규 소스를 추가하는 절차를 공식화하고, `test_m2_source_registry_governance.py`의 하드코딩된 카운트(14→15, reference 4→5 등)를 그 Amendment의 일부로 함께 갱신. `manifest_writer.write_entry()`의 헤더 주석 소실 버그도 같이 고침.
- **옵션 B**: 이 침례교 주석 트랙을 M2(ADR-030 governance)와 **별도의 원장**으로 관리 — 예컨대 `NAE/authority/works.yaml`(현재 비어있음, ADR-021 §4 Option C) 쪽에 등록하고 M2는 건드리지 않음. Reference 트랙은 애초에 TSU 트랙 심사 대상이 아니므로(§0) M2가 실제로 이 트랙까지 관장해야 하는지 자체가 불명확 — Smith 4권이 이미 M2에 들어가 있는 것과의 일관성 문제는 남는다.

RAW 원본(§5.1 CCEL PDF, §5.2 archive.org hocr.html/original.pdf)과 canonical.json은 모두 로컬에 안전하게 보존돼 있고 gitignored라 아무것도 커밋되지 않았다 — 위 결정이 나면 등록 단계부터 바로 재개 가능하다.

### 5.6 해소 — 옵션 A 채택, 등록 완료 (2026-09-13)

사용자가 옵션 A(ADR-030 Amendment)를 선택했다. `docs/architecture/ADR-030-AMENDMENT-B-Reference-Track-Post-Freeze-Registration.md`(PROPOSED) 작성 후:

- `register_source()`/`RegistrationRequest`에 ADR-030 §8.4 additive 필드(content_genre 등) 통과 경로 추가.
- `manifest_writer.write_entry()`를 **진짜 append-only**로 재작성 — 1차 수정(헤더만 보존 후 전체 재덤프)이 실제로는 기존 14개 레코드의 서식을 값 변경 없이 바이트 단위로 바꾸는 걸 diff로 발견하고 되돌린 뒤, 파일이 존재하면 새 엔트리 YAML 블록만 기존 텍스트 뒤에 붙이는 방식으로 재작업. 최종 diff = 신규 레코드 15줄 추가만, 원본 14개 0줄 변경 확인.
- `tests/test_m2_source_registry_governance.py`/`scripts/m2_source_registry_validator.py`에 `M2_FROZEN_BASELINE_SOURCE_IDS`(원본 14개 source_id) 도입 — 정확한 카운트 검증을 이 집합으로 scope, 전체 개수는 "≥14 + 원본 14 포함"으로 완화.
- `BAP-COMM-SPURGEON-TDA-VOL01` 등록 완료(QUALITY_PASSED, content_genre=[commentary], authority_class=reference). `tradition`/`theological_category`는 최소 범위 유지를 위해 이번엔 비움.
- 전체 스위트 2,955 passed / 13 skipped — 실패 2건은 이 워크트리에 다른 13개 소스의 raw 파일이 원래 없는 환경 갭(Amendment 이전에도 동일하게 존재, 무관).

**남은 것**: Amendment B는 아직 PROPOSED — Evidence Before Promotion Rule의 C1 독립 검토·HQ 최종 승인 두 조건이 열려 있다(§4). RAW 체크섬 등록까지는 완료됐으므로, 다음은 canonicalize(이미 §5.3에서 완료)를 거친 실제 임베딩(`scripts/nae_commentary_ingest.py --apply`)으로 넘어갈 수 있으나, 그 전에 C1 Review 요청 여부를 사용자에게 확인한다.

---

## 6. 확인이 더 필요한 사항 (결정하지 않고 기록만)

- `NAE/authority/works.yaml`에 Smith Bible Dictionary가 실제로 등록되어 있는지 미확인 — 등록 안 됐다면 이번 파일럿도 동일 관례(미등록)를 따를지, 이번 기회에 둘 다 등록할지는 HQ 판단.
- `corpus_admissions.jsonl`에 `"track": "reference"` 값을 쓴 선례가 있는지 미확인(기존 항목은 전부 `"track": "tsu"`) — 새 track 값 추가가 스키마/검증 로직(`tests/test_validator_v22.py` 등)에 영향을 주는지 별도 확인 필요.
- ADR-028은 "Smith Reference Layer"로 명명되어 Smith 전용 문서다. 이번 커밋으로 그 파이프라인이 사실상 "일반 Reference Layer"로 넓어졌다 — ADR-028 Amendment(범위를 Reference Layer 전반으로 재정의) 또는 신규 ADR(예: ADR-034, 032/033은 이미 사용 중) 작성이 필요한지는 변경 범위가 작아(collection/chunker 파라미터화, 기존 기본값 무변경) 이번 커밋만으로는 Architecture Layer 추가에 해당하지 않는다고 판단했으나, HQ/C1 재검토를 권한다.
- PR #17(문단 앵커드 근거)·PR #25(근거부족 유출차단) 로직은 `ui/pages/chat.py`의 `generate_answer()`(§chat.py:409-474 부근) 레벨에서 전체 응답 생성 경로에 적용되므로, `_inject_smith_context()`가 반환하는 `smith_results`도 `if not response.top_k_results and not smith_results:` 체크(chat.py:462)에 이미 포함된다 — reference 주입 경로에 자동 적용됨을 코드 확인으로 검증 완료(추가 배선 불필요).

---

## 7. Build Report 요약

```
STATUS: 코드 준비 완료 / 실행(임베딩) 미착수 — 원본 미확보
Changed Files:
  NAE/pipeline/reference/config.py       (+COMMENTARY_COLLECTION_NAME, +KNOWN_REFERENCE_COLLECTIONS)
  NAE/pipeline/reference/chunker.py      (+chunk_canonical_verse_anchored, +ReferenceChunk.scripture_reference)
  NAE/pipeline/reference/ingest.py       (ingest() +collection_name/+chunker_fn/+content_type, 기본값 무변경)
  NAE/reference_retrieval_adapter.py     (search_reference() +collection_names, 기본값 무변경)
  NAE/smith_activation.py                (+NAE_SMITH_ACTIVATION_NARROW 플래그, 기본 off)
  scripts/nae_commentary_ingest.py       (신규 CLI, ingest.ingest() 재사용)
  tests/test_reference_pipeline_generalization.py (신규, 17개 테스트)
  docs/BAPTIST_COMMENTARY_EMBEDDING_PLAN_v1.md (본 문서)
Tests: 17/17 passed (신규) — chunker verse-anchoring, ingest 기본값 회귀, search_reference 시그니처 회귀, activation narrow flag on/off
Regression: tests/ -k "reference or smith or chunk" → 179/179 passed (기존 테스트 전부 통과, Qdrant/Ollama 라이브 연결 불필요한 것만 대상 — 실제 임베딩/검색 E2E는 원본 확보 후 별도)
Architecture Rule: ADR-013(collection 격리) 준수 — 별도 컬렉션. ADR-028 §10(Smith citation 미노출) 무변경 — Citation 모델 손대지 않음
ADR Conflict: 없음(신규 코드 경로는 전부 기본값 off/기존 값 유지) — ADR-028 범위 확장 여부는 §6에 미결 사항으로 기록, Amendment 필요성은 HQ/C1 판단 대기
C1 Review: 권장하나 미요청 — 변경 범위가 flag-off 기본값 무변경 + 신규 격리 컬렉션(프로덕션 미접촉)이라 "사소한 버그 수정" 범주에 가까우나, ADR-028 범위 해석 문제가 있어 사용자 판단 요청
Git(Commit/Push): 완료 조건 충족 — CUE Operating Policy에 따라 자동 commit/push 수행 (origin, 현재 작업 브랜치, force 아님)
Next: (1) 원본 확보 승인 여부 회신 (2) §6 미결 사항 중 works.yaml/corpus_admissions track 스키마 확인 (3) 승인 시 다운로드→canonicalize→dry-run→apply
```

**ADR-028 범위 관련 참고**: §6의 "ADR-028이 사실상 Reference Layer 전반으로 넓어졌다"는 관찰은 확인된 충돌(conflict)이 아니라 향후 Amendment 필요 여부에 대한 판단 요청이다 — 이번 커밋의 모든 신규 동작은 기본값 off/기존 값 유지이므로 Architecture Freeze Rule이 요구하는 "구현 중단" 사유에 해당하지 않는다고 판단해 진행했다.

---

## 8. Build Report — 원본 확보/Canonicalize 라운드 (2026-09-12, §5)

```
STATUS: 원본 확보(archive.org)·canonicalize·청킹 검증 완료 / RAW 체크섬 등록은 ADR-030 충돌로 중단(구현 미완료, 사용자 확인 대기)
Changed Files (커밋 대상):
  NAE/pipeline/reference/chunker.py            (chunk_canonical_verse_anchored에 anchor_book_prefix 파라미터 추가 — 오앵커 버그 수정, §5.4)
  tests/test_reference_pipeline_generalization.py (버그 재현 회귀 테스트 2건 추가, fixture를 실제 canonical 포맷("Psalms N:M")에 맞춰 수정)
  docs/BAPTIST_COMMENTARY_EMBEDDING_PLAN_v1.md (본 섹션)
Local-only 산출물 (gitignored, 커밋 안 됨):
  NAE/corpus/raw/ccel/reference/Spurgeon_TreasuryOfDavid_Vol1/treasury1.pdf        (1차 시도, 텍스트 레이어 없어 미사용)
  NAE/corpus/raw/archive_org/reference/Spurgeon_TreasuryOfDavid_Vol1/{hocr.html,original.pdf} (2차 시도, 사용)
  NAE/corpus/canonical/Spurgeon_TreasuryOfDavid_Vol1/{canonical.json,canonical.txt,normalize_report.json}
되돌린 것 (git checkout으로 원복, 커밋 안 됨):
  NAE/pipeline/registration/state/{source_manifest.yaml,raw_checksum_ledger.jsonl,registration_state.json}
  — ADR-021 cli_driver --production 실행으로 BAP-COMM-SPURGEON-TDA-VOL01을 등록했으나, ADR-030 §7.3 고정 스냅샷(M2)의
    하드코딩된 카운트 검증 7건이 깨져 즉시 되돌림 (§5.5)
Tests: 신규 회귀 2건 포함 19/19 passed. 전체 스위트 2,955 passed / 13 skipped — 실패 2건은 이번 raw 다운로드로
  NAE/corpus/raw/가 생기며 활성화된 환경 완전성 게이트(다른 12개 소스의 raw 파일이 이 워크트리에 원래 없음, 내 변경과 무관)
Architecture Rule: ADR-021(registration pipeline) 자체는 정상 동작 확인(QUALITY_PASSED). 문제는 ADR-021의 산출물이
  ADR-030이 동결한 M2 파일과 충돌한다는 점 — 두 ADR 간 상호작용이 사전에 문서화돼 있지 않았음.
ADR Conflict: 있음 (Architecture Freeze Rule 적용 대상) — ADR-030 v2.1 §7.3 FROZEN BASELINE(14 sources,
  authority_class 정확히 historical_witness×10+reference×4)에 15번째 레코드를 추가하는 것은 그 스냅샷의 구성을 변경함.
  §5.5에 옵션 A(Amendment)/옵션 B(별도 원장) 기록 — 구현 중단, 사용자 결정 대기.
C1 Review: 미요청 — Architecture Freeze Rule 위반 여부 자체가 사용자 확인 대기 상태라 그 전에는 요청 시점이 아님.
Git(Commit/Push): 코드 수정분(chunker 버그 수정 + 테스트)만 커밋/푸시 대상. 거버넌스 충돌 부분은 커밋하지 않음(이미 되돌림).
Next: 사용자가 옵션 A/B 중 결정 → (A) ADR-030 Amendment 작성 후 등록 재실행 / (B) works.yaml 등 별도 원장 설계 후 재실행.
  둘 중 하나가 정해지면 RAW·canonical 산출물은 이미 준비돼 있어 등록부터 바로 재개 가능.
```
