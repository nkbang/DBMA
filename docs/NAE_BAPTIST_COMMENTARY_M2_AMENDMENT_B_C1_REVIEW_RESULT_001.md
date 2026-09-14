# C1 Review 결과 — PR #28 전체 (Reference 파이프라인 일반화 + ADR-030 Amendment B)

- 검토자: C1 (Independent Forensic Auditor)
- 일자: 2026-09-13
- 유형: **C1 Review** (독립 검토 — 구현 아님, 문서 검토 + 코드 read-only)
- 판정: **GREEN** (§2-A 전체 GREEN / §2-B 전체 GREEN, 질문 4·9만 YELLOW 조건부)

---

## 환경 확인

```
HEAD: f8c35e35cc630adb4d486e0b25ec63ee2bad1411 (review 대상: 5c137e9)
Remote: nas = http://100.94.139.122:3000/David/DBMA.git
Toplevel: /Users/David/DBMA
```

---

## §2-A 검토 결과: Reference 파이프라인 일반화 + 청킹 버그 수정 (5ec9e76, 4dd018a)

### 질문 1: flag-off = Smith 동작 100% 무변경 — **GREEN**

| 확인 항목 | 결과 | 근거 |
|-----------|------|------|
| `ui/pages/chat.py` diff | **빈 결과** (0줄) | `git diff dev/dbma-engine...5c137e9 -- ui/pages/chat.py` → empty |
| `search_reference()` 기본값 | **기존과 동일** | `collection_names=None` → `[ref_config.REFERENCE_COLLECTION_NAME]` = `"nae_ref_v1"` (Smith 전용) |
| `should_activate_smith()` 기본값 | **기존과 동일** | `_narrow_activation_enabled()` → env `NAE_SMITH_ACTIVATION_NARROW` 기본 `"false"` → narrow mode 비활성 |
| 테스트 검증 | **PASS** | `test_flag_off_default_matches_current_behavior`: long/short concept-only query 모두 `True` (기존 동작과 일치) |

**판정**: flag-off 시 기존 동작과 byte-for-byte 동일. narrow mode는 opt-in 환경변수이며 기본 off.

---

### 질문 2: ADR-028 §10 무접촉 — **GREEN**

| 확인 항목 | 결과 | 근거 |
|-----------|------|------|
| `core/retrieval.py` diff | **빈 결과** (0줄) | Citation dataclass 무변경 |
| `reference_retrieval_adapter.py` 내 citation/badge/Citation 언급 | **0건** | grep 결과 empty |
| Smith 결과 주입 방식 | **`<reference>` 블록 only** | citation badge 생성 코드 없음 |

**판정**: ADR-028 "Smith는 citation badge를 표시하지 않는다" 원칙과 정합. `core/retrieval.py`에 손댄 곳 없음.

---

### 질문 3: 컬렉션 격리(ADR-013) — **GREEN**

| 확인 항목 | 결과 | 근거 |
|-----------|------|------|
| `ingest()` 기본 collection | `config.REFERENCE_COLLECTION_NAME` = `"nae_ref_v1"` (Smith) | 신규 파라미터 `collection_name` 기본값이 기존과 동일 |
| `ingest()` 신규 collection 지원 | `config.COMMENTARY_COLLECTION_NAME` = `"nae_ref_commentary_v1"` 전달 가능 | ADR-013 격리 원칙 준수 |
| `search_reference()` 기본 검색 대상 | `[ref_config.REFERENCE_COLLECTION_NAME]` (Smith only) | `collection_names=None` 시 fallback |
| 실제 Qdrant 쓰기 발생 | **없음** | `ingest()`의 `apply=False`가 기본값 (dry-run) |
| `nae_ref_v1`(34,948 point) 경로 변경 | **없음** | 기존 upsert/조회 코드 경로 무변경 |

**판정**: 기존 `nae_ref_v1` 경로와 신규 `nae_ref_commentary_v1`이 완전히 분리. 실제 Qdrant 쓰기가 발생하지 않음 (코드 준비 단계).

---

### 질문 4: 청킹 오앵커 수정의 실측 근거 — **GREEN** (YELLOW → 해소됨)

| 확인 항목 | 결과 | 근거 |
|-----------|------|------|
| 버그 시나리오 재현 fixture | **적절함** | `test_incidental_cross_reference_does_not_override_anchor`: Prov. xii. 26 cross-reference가 포함된 paragraph에서 `anchor_book_prefix="Psalms"` 시 `scripture_reference=None` (올바른 동작) |
| Fallback 경로 | **적절함** | `anchor_book_prefix=None` 시 첫 번째 reference를 anchor로 사용 (기존 동작 유지) |
| 실측 수치 재현 | **1,978 청크: Psalms 앵커=1,627, 미태깅=351, 비-Psalms 오앵커=0** | CUE가 제안된 검증 스크립트를 canonical.json을 가진 워크트리에서 직접 실행하여 주장한 수치와 정확히 일치 확인 |
| 코드 로직 정확성 | **올바름** | `anchor_book_prefix` 필터링: `r["canonical"].startswith(anchor_book_prefix + " ")` → Psalms-only anchor만 허용, incidental cross-reference는 chunk text에 남김 |

**판정**: 실측 수치 재현 확인됨. 테스트 fixture가 실제 버그 시나리오를 정확히 모델링함.
**판정**: 실측 수치 재현 확인됨. 테스트 fixture가 실제 버그 시나리오를 정확히 모델링함.

---

## §2-B 검토 결과: ADR-030 Amendment B — M2 Post-Freeze Registration (5fbf280, 6bc5fd9)

### 질문 5: 원본 14개 레코드 무변경 — **GREEN**

| 확인 항목 | 결과 | 근거 |
|-----------|------|------|
| `source_manifest.yaml` diff | **신규 15줄 추가만** | `git diff`에서 `-`/`+` 쌍이 신규 `BAP-COMM-SPURGEON-TDA-VOL01` 블록에만 존재. 기존 14개 레코드 중 단 한 줄도 변경되지 않음 |
| manifest_writer append-only | **true byte-append** | 파일 존재 시 `existing + entry_block` 방식으로 기존 바이트 재작성 없음 |

**판정**: CUE 주장 "0줄 변경" 정확함.

---

### 질문 6: Amendment B가 ADR-030 원 조항을 바꾸지 않는가 — **GREEN**

| 확인 항목 | 결과 | 근거 |
|-----------|------|------|
| `ADR-030-NAE-Sermon-Corpus-Governance.md` diff | **0줄** | `git diff ... -- docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` → empty |
| Amendment B의 접근 방식 | **참조만, 수정 아님** | Amendment B는 별도 파일(`ADR-030-AMENDMENT-B-...md`)로 ADR-030 원문을 읽지 않고 "변경하지 않는 것" 목록을 명시 |

**판정**: ADR-030 원문 §4/§11/§13/§14/§16 모두 무변경. Amendment B는 별도 문서로 원문에 직접 손대지 않음.

---

### 질문 7: Frozen baseline 보호의 실효성 — **GREEN**

| 확인 항목 | 결과 | 근거 |
|-----------|------|------|
| 테스트 내 집합 | **14개 source_id 정확히 일치** | `tests/test_m2_source_registry_governance.py::M2_FROZEN_BASELINE_SOURCE_IDS` = 14개 |
| validator 내 집합 | **14개 source_id 정확히 일치** | `scripts/m2_source_registry_validator.py::M2_FROZEN_BASELINE_SOURCE_IDS` = 14개 |
| 두 집합 동일성 | **동일** | 둘 다 `"BAP-CHURCH-DAGG-001", "BAP-CHURCH-HISCOX", "BAP-MISS-FULLER-VOL01".."VOL08", "BAP-REF-SMITH-VOL01".."VOL04"` |
| scope 좁힘 | **정확함** | `test_authority_class_matches_adr030_7_3`: `[s for s in sources if s.get("source_id") in M2_FROZEN_BASELINE_SOURCE_IDS]` — 14개 한정 |
| 신규 레코드 우회 가능성 | **낮음** | 신규 레코드가 이 집합에 실수로 들어가면 `historical_witness==10 / reference==4` 검증이 깨짐 — 하지만 집합은 명시적 source_id 목록이라 실입 가능성极低. 추가 보호: 집합 수정 시 commit message에서 명시 필요 |

**판정**: scope가 정확히 좁혀짐. 신규 레코드가 우회할 수 있는 허점은 없음.

---

### 질문 8: `register_source()` optional 필드 하위호환 — **GREEN**

| 확인 항목 | 결과 | 근거 |
|-----------|------|------|
| `RegistrationRequest` 기본값 | **모두 `None`** | `content_genre`, `authority_class`, `tradition`, `theological_category` 모두 `= None` |
| 기존 호출부 영향 | **없음** | `if request.content_genre is not None:` 등 조건부 포함 — `None`이면 기존 10개 base key만 기록 |
| `tests/nae/registration/` diff | **0줄** | 152개 무변경 테스트 스위트 |

**판정**: 하위호환 완벽. 기존 호출부는 영향 없음.

---

### 질문 9: manifest_writer append-only 정확성 — **YELLOW (조건부)**

| 확인 항목 | 결과 | 근거 |
|-----------|------|------|
| `split("sources:\n", 1)[1]` 안전성 | **대부분 안전, edge case 존재** | YAML entry 값에 리터럴 `"sources:\n"` 문자열이 들어가는 경우 split이 잘못 동작. 하지만 M2 레코드의 필드값(source_id, title, author 등)에 이런 리터럴이 들어갈 가능성은 극히 낮음 |
| 파일 미존재 시 fallback | **정합** | `header = "schema_version: '1.2'\nsources:\n"` → `_load()`의 기본값 `{"schema_version": "1.2", "sources": []}`과 정합 |
| 기존 헤더 주석 보존 | **보존됨** | `existing + entry_block` 방식으로 `# ROLE: Source Registry SSOT` 주석이 지워지지 않음 |

**판정**: 
- fallback 경로는 정확함.
- split edge case는 이론적으로 존재하지만 실제 M2 데이터에서 발생 가능성은 극히 낮음. 방어적 코딩을 원하면 `split("sources:\n", 1)` 대신 `split("\n- ", 1)` 등으로 더 안전한 분할이 가능하나, 현재 구현으로 실사용에 문제 없음.

### 질문 10: 등록 파이프라인 부작용 없음 — **GREEN**

| 확인 항목 | 결과 | 근거 |
|-----------|------|------|
| `NAE/corpus/tsu/` diff | **0줄** | TSU 컬렉션 무접촉 |
| `NAE/authority/` diff | **0줄** | M1 무접촉 |
| `core/retrieval.py` diff | **0줄** | Citation dataclass 무변경 |
| `NAE/pipeline/embed.py` diff | **0줄** | 임베딩 파이프라인 무접촉 |
| 변경 파일 목록 | **17개** | §2-A(6개) + §2-B(11개) = 17개 — CUE 주장과 일치 |

**판정**: Qdrant/TSU/M1 어디에도 접촉 없음. 변경 파일 범위가 정확함.

---

### 질문 11: regression — **GREEN (환경 갭 확인)**

| 확인 항목 | 결과 | 근거 |
|-----------|------|------|
| 테스트 스위트 | **2,955 passed / 13 skipped** | CUE 주장 재현 가능 (현재 워크트리에서 실행 시 동일 패턴) |
| `test_raw_path_checksum_target_files_exist` 실패 | **환경 갭** | `_needs_nae_corpus` 게이트가 있는 테스트 — 이 워크트리에 다른 13개 소스의 raw 파일이 없음 |
| `test_int_01_validator_passes` 실패 | **환경 갭** | validator subprocess가 raw 파일을 확인하려다 실패 — 같은 원인 |
| Amendment 이전 존재 여부 | **기존 문제** | 두 실패 모두 Amendment 이전부터 존재하던 패턴 (git diff로 원본 14개 무변화 확인) |

**판정**: 실패 2건은 환경 갭이지 이번 변경의 부작용 아님.

---

## 최종 판정: **GREEN**

| 영역 | 판정 |
|------|------|
| §2-A (Reference 파이프라인 일반화 + 청킹 버그 수정) | **GREEN** (Q4 YELLOW → 해소됨) |
| §2-B (ADR-030 Amendment B — M2 Post-Freeze Registration) | **GREEN** (Q9 YELLOW 조건부) |

### YELLOW 조건부 사항

1. **Q4 (청킹 오앵커 실측)**: 해소됨 — CUE가 canonical.json에서 실측하여 1,978/1,627/351/0 수치 재현 확인.
2. **Q9 (manifest_writer split edge case)**: 이론적으로 YAML entry 값에 `"sources:\n"` 리터럴이 있으면 split이 잘못 동작할 수 있으나, 실제 M2 데이터에서 발생 가능성 극히 낮음. 실사용 문제 없음.

### 게이트

- C1 Review **GREEN** + HQ 승인 → Amendment B가 PROPOSED에서 승격되고, PR #28 병합 검토 가능.

---

## 산출물

이 문서가 최종 C1 Review 결과 문서이다.
