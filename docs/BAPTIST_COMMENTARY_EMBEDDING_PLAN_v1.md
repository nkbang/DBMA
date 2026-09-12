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

## 5. 원본 확보 요청 — 사용자 승인 필요 (자동 다운로드 금지)

아래 파일을 CCEL(Christian Classics Ethereal Library) 또는 archive.org에서 받아야 한다. **다운로드는 사용자의 명시적 "예" 승인 후 별도로 진행한다.**

| 항목 | 값 |
|---|---|
| 제목 | The Treasury of David, Volume 1 (Psalms I–XXVI) |
| 저자 | Charles Haddon Spurgeon |
| 추정 크기 | PDF/EPUB 기준 약 5–10MB (원서 약 500쪽) |
| 후보 출처 1 | `https://ccel.org/ccel/spurgeon/treasury1` (CCEL — 학술 공개 텍스트, HTML/PDF/EPUB 제공) |
| 후보 출처 2 | `https://archive.org` 검색: "Treasury of David volume 1 Spurgeon" (여러 스캔본 존재, 스캔 품질 확인 필요) |
| 권장 파일명 | `Spurgeon_TreasuryOfDavid_Vol1.epub` (또는 확보 형식에 맞춰 `.pdf`) |
| 저장 위치 | `NAE/corpus/raw/Spurgeon_TreasuryOfDavid_Vol1/` (프로젝트 관례 — RAW 원본 보관 경로, `scripts/check_raw_only_originals.py` 대상) |

승인 후 진행 순서: 다운로드 → RAW 체크섬 등록(`NAE/pipeline/registration/`) → `NAE.pipeline.canonical` 추출/정제(canonical.json 생성, `scripture_references` 자동 주석 포함) → `python scripts/nae_commentary_ingest.py --identifier Spurgeon_TreasuryOfDavid_Vol1 --dry-run`으로 청킹 검증 → 육안 검토 → `--apply`.

**승인 못 받을 경우**: 위 절차는 미착수 상태로 유지된다. 이번 세션에서 완료한 코드/테스트/문서(§2, §3, 본 문서)는 원본과 무관하게 그대로 유효하며, 원본 확보 후 바로 `--dry-run`부터 재개 가능하다.

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
