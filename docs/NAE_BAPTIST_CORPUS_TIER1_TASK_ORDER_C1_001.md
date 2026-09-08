# Task Order — NAE Baptist Corpus Tier 1 벡터화 준비 (C1)

- 발급: CUE → C1 (Cline 작업창 #1)
- 일자: 2026-09-07
- 상태: OPEN
- 근거 문서:
  - `docs/BAPTIST_THEOLOGY_FOUNDATIONAL_SOURCES_v1.md` (조사 결과)
  - `resources/theological_sources/baptist/source_manifest.yaml` (NAE-SOURCE-003 등록부)
  - `scripts/ingest_nae_source.py` (docstring = manifest 스키마·사용례)
  - `docs/architecture/NAE-Dual-Pipeline-Clarification.md` (RAW 배치 2경로)
  - `STEP5_HUMAN_ACQUISITION_GUIDE.md` (원문 확보 절차)
  - ADR-030 §8.3 (M2 source manifest 권위)

---

## 1. 목표

이미 등록부에 `approved_for_acquisition` 상태로 존재하나 원문이 미확보
(`local_path: null`)인 **Tier 1 침례교 1차 자료 4건**을, 프로덕션 색인
직전 단계까지 준비한다. **이번 Task Order는 dry-run까지만 — Qdrant
upsert(`--apply`)와 corpus admission은 범위 밖이다.**

### 대상 4건 (등록부 기존 항목)

| source_id | 제목 | 연도 | license |
|---|---|---|---|
| SLBC1689 | Second London Baptist Confession | 1689 | public_domain_original |
| PBC1742 | Philadelphia Baptist Confession | 1742 | public_domain_original |
| NHBC1833 | New Hampshire Confession of Faith | 1833 | public_domain_original |
| TH1612 | Helwys, *A Short Declaration of the Mystery of Iniquity* | 1612 | public_domain_original |

> Dagg / Hiscox / Fuller Vol01–08 은 이미 corpus에 존재(ADMITTED/CLEAN) →
> 이번 범위 제외. Gill / Boyce / Keach's Catechism / Carson 은 등록부에
> 없음 → CUE가 후속 ADR·등록에서 처리, 이번 범위 제외.

---

## 2. 절대 금지 (명령 없이 변경 금지 — CLAUDE.md / ADR-030)

- ❌ `--apply` 실행, Qdrant 컬렉션 생성·upsert·삭제
- ❌ `scripts/nae_reference_ingest.py --apply`
- ❌ Retrieval Engine / Embedding Engine / TSU Pipeline 코드 수정
- ❌ 기존 ADR 파일 수정, 신규 ADR 작성 (CUE 담당)
- ❌ `NAE/authority/source_manifest.yaml` 수정 (DERIVED mirror — hand-edit 금지)
- ❌ `NAE/pipeline/registration/state/` 등 M2 state 파일 수정
- ❌ 기존 RAW 파일·기존 canonical(`NAE/corpus/canonical/*`) 수정
- ❌ `core/processing.py::register_document()` 고정 스키마 수정

---

## 3. 작업 절차

### Lane A — 원문 확보 (사람 + C1 보조)

`STEP5_HUMAN_ACQUISITION_GUIDE.md` 절차를 따른다. 각 자료를 **2경로 모두**에
배치 (`NAE-Dual-Pipeline-Clarification.md`):

- (A) NAE pipeline 경로:
  `NAE/corpus/raw/archive_org/books/<SOURCE_ID>/` (PBC1765 선례 형식:
  `ocr.txt` / `original.pdf` / `hocr.html`)
- (B) tsu_builder 경로:
  `data/nae/sources/baptist/<slug>.txt` (예: `nhc_1833.txt`)

확보 출처는 등록부 notes에 기재된 것만 사용: Internet Archive, Project
Gutenberg, CCEL. 현대 학술 편집본(주석·해제 포함)은 피하고 원문 전사본
우선. 각 다운로드는 사람이 URL·판본을 확인한 뒤 진행.

### Lane B — 등록 + dry-run (C1 기계 작업)

1. RAW 배치 완료 확인 후, 각 파일 SHA-256 계산.
2. `resources/theological_sources/baptist/source_manifest.yaml` 의 해당 4개
   항목만 수정: `local_path` 채우고 `raw_checksum` 추가. **다른 항목·다른
   파일은 건드리지 않는다.**
3. `ingest_nae_source.py` 용 manifest JSON 작성:
   `data/nae/metadata/baptist_tier1_manifest.json`
   (스키마 = `scripts/ingest_nae_source.py` docstring. 필수 키:
   `source_filename`, `title`, `copyright_status`, `content_genre`.
   신앙고백서 3건은 `resource_type: confession`, Helwys는 `theology`.)
4. **dry-run 실행 & 전체 stdout 캡처**:
   ```
   python -m scripts.ingest_nae_source --manifest data/nae/metadata/baptist_tier1_manifest.json --dry-run
   ```
5. 회귀(read-only) — 작업 전/후 2회 실행, diff 비교:
   ```
   python scripts/nae_corpus_reconcile.py --json
   ```
   신규 drift가 생기면 **중단하고 보고**.
6. `git status` / `git diff --stat` 캡처.

---

## 4. 완료 조건 (Definition of Done)

- [ ] RAW 4건 × 2경로 배치 완료, 파일 크기·인코딩(UTF-8) 확인
- [ ] `source_manifest.yaml` 4개 항목 `local_path` + `raw_checksum` 반영,
      그 외 무변경 (`git diff` 로 증명)
- [ ] `baptist_tier1_manifest.json` 생성
- [ ] dry-run stdout 전문 첨부 — 4건 모두 "추출 → 청킹" 성공, skip/에러 0
- [ ] `nae_corpus_reconcile.py` 작업 전/후 결과 동일 (신규 drift 0)
- [ ] Qdrant 무접촉 (컬렉션 목록 작업 전/후 동일 — `curl` 덤프 첨부)
- [ ] Build Report 작성: `docs/NAE_BAPTIST_CORPUS_TIER1_BUILD_REPORT_001.md`

## 5. 산출물

1. RAW 파일 (2경로)
2. `resources/theological_sources/baptist/source_manifest.yaml` (patch)
3. `data/nae/metadata/baptist_tier1_manifest.json`
4. `docs/NAE_BAPTIST_CORPUS_TIER1_BUILD_REPORT_001.md`
   — 형식: `STATUS / Changed Files / dry-run 결과 / Reconcile(전·후) / Qdrant(전·후) / Git / Next`

## 6. 보고 시 반드시 원문 첨부 (C1 오보고 방지)

과거 C1이 Qdrant·corpus 상태를 검증 없이 보고한 사례 4회. 수치·완료
주장은 **명령어 stdout 원문**으로만 인정. "정상"·"완료" 단어만으로는
불가. `git rev-parse HEAD`, `git remote -v`, `git rev-parse --show-toplevel`
을 보고 첫 줄에 포함.

---

## 7. CUE 후속 (이번 Task Order 밖)

- 신규 ADR 초안: Baptist corpus 확장 — 컬렉션 설계(권장: 신규
  `nae_baptist_v1` 분리), 신앙고백서 인용 단위(권장: 문단 단위 좌표
  `<conf> §<ch>.<para>`), canonical_id 규칙(ADR-017 lowercase snake_case)
- C1 Review 요청 (Metadata Model 변경 트리거)
- 사용자 승인 후 `--apply` + admission Task Order 별도 발급
- Gill / Boyce / Keach's Catechism / Carson 등록부 신규 등재
- UI: 검색 탭 소스 필터 + 인용 좌표 표시
