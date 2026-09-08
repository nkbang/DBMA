# Task Order — B-1: Scripture 추출기 수정 (C1)

- 발급: CUE → C1
- 일자: 2026-09-08
- 근거: `NAE_FULLER_PROCESSING_RESUMPTION_PLAN_v1.md` §10 B-1;
  `NAE_FULLER_CANONICAL_VERIFICATION_001.md` T3 (전 8권 체계적 추출 실패)
- 작업 위치: `/Users/David/DBMA` @ `dev/dbma-engine`, venv `~/envs/dbma311`
- 대상 파일: `NAE/pipeline/canonical/annotate.py` (필요 시 전용 헬퍼 모듈 신설)

---

## 0. 목적 / 비목적

**목적**: `annotate.py`의 성구 참조 추출 정확도를 올린다. F1 실측 —
`_ROMAN_MAP`이 xxviii(28)에서 잘리고, book 이름이 `[A-Z][a-z]+`(영문 1단어)만
허용, OCR 노이즈에 취약 → Vol.01 리포트 2 vs 실제 수백.

**비목적** (이 Task Order 밖):
- ❌ Fuller / Smith / Dagg / Hiscox canonical **재-정제(re-normalize)** — B-2, B-1에 BLOCKED
- ❌ `scripture_references` **출력 스키마 변경** — `[{"original":..., "canonical":...}]` 유지, `scripture_references_found`는 int 카운트 유지
- ❌ TSU builder / retrieval / embedding 코드
- ❌ Vol.02–08 TSU 생성 (B-1·P-2 완료 후 별도)

---

## 1. 수정 항목

### F-1. Roman numeral 파서
- `_ROMAN_MAP`(28개 하드코딩) → **일반 로마숫자 파서**로 교체.
  최소 1–150 (시편 150편), 3자리(cxviii=118) 처리. 상한(예: ≤ 199)을 둬서
  OCR 잡음 오탐 방지. 잘못된 시퀀스("iiii", "vx")는 None 반환.
- `canonicalize_scripture_ref()`가 chapter/verse 둘 다 로마숫자인 경우도 처리
  (현재는 chapter만).

### F-2. Book 이름 인식 확대
- **기존 book-name 테이블 재사용** — 새 테이블 신설 금지:
  - 영문: `core/query_enhancements.py` alias 로직 또는 `core/bible_index.py`
  - 한글: `core/sermon/bible_books.py::BIBLE_BOOKS` (66권 KR명 + book_id).
    ⚠️ `core/query_enhancements.py::_KOREAN_FULL_NAMES`의 알려진 오타
    ("예레미애"→애가, "스게론"→스가랴)는 **재현하지 말 것**.
- 추가 인식: 전대문자(`ROM`), 통상 약어(`Rom`, `1 Cor`, `Rev`), 한글 서명
  (`롬`, `요`, `고전`, `계`).
- 한글 성구 표기: `요 3:16`, `요한복음 3장 16절`, `롬 8:1-2` 형태.

### F-3. 한글 canonical 형식 — **C1이 결정 제시** (구현 전 CUE 승인)
- 옵션 A: 영문 canonical로 통일 (`요 3:16` → `John 3:16`) — 기존
  `John 3:16` 출력과 일관, 색인 단순.
- 옵션 B: 한글 유지 (`요 3:16` → `요한복음 3:16`).
- **CUE 권고 = A** (기존 출력·`book_id` 공간과 일관). 이견 있으면 근거와 함께 제시.

### F-4. OCR 노이즈 내성 (보수적으로)
- book과 chapter/verse 사이의 흔한 잡음 1–3자 허용 (`Rom. ii. + 2` 류).
- 단, 오탐 급증 방지 — 노이즈 허용 범위를 좁게, 테스트로 경계 고정.

---

## 2. TDD / 회귀

### 신규 테스트 (`tests/test_nae_canonical_annotate.py` 확장 또는 신규 파일)
- roman > 28: `Ps. xl. 6` → `Psalms 40:6`, `Rom. cxviii...`(비정상)은 None
- 한글: `롬 8:1` → canonical(F-3 결정), `요한복음 3장 16절` → canonical
- OCR 노이즈: `Rom. ii. + 2` → `Romans 2:2`; 과도한 잡음은 미매칭
- 음성 케이스: `Vol. iii. 5`(책 참조 아님), `p. 12`(페이지)는 성구로 잡지 않음

### 회귀 (전량 PASS 필수)
```
~/envs/dbma311/bin/python -m pytest -q \
  tests/test_nae_canonical_annotate.py \
  tests/test_nae_canonical_normalize.py \
  tests/test_nae_canonical_pipeline.py \
  tests/test_nae_canonical_structure.py \
  tests/test_nae_canonical_reflow.py \
  tests/test_scripture_reference_stabilization.py \
  tests/test_nae_tsu_citation_scripture.py \
  tests/test_scripture_evidence_resolver.py \
  tests/test_book_alias_resolution.py \
  tests/test_build_tsu_dataset_verse_mapping.py
```
기존 케이스의 기대값이 바뀌어야 한다면(개선으로 인해) **그 목록과 근거를
리포트에 명시** — 무단 기대값 수정 금지.

### 측정 (read-only, 재-정제 아님)
- `NAE/corpus/canonical/Fuller_Complete_Works_Vol01..08/canonical.txt`에
  **수정된 `find_scripture_references_extended()` 를 직접 적용**해 before/after
  참조 수 표 작성 (8권). 파일은 건드리지 않는다.

---

## 3. 금지 / STOP

- ❌ `scripture_references` 출력 스키마 변경, 신규 metadata 필드
- ❌ canonical 파일·`normalize_report.json` 수정, 재-정제 실행
- ❌ 새 book-name 테이블 신설 (기존 재사용)
- ❌ TSU/embedding/Qdrant/retrieval 코드
- STOP: 회귀 테스트에서 기대값이 바뀌는데 근거 불명 / 오탐이 급증(측정에서
  before 대비 비상식적 증가) / F-3 결정을 CUE 승인 없이 구현

---

## 4. 완료 조건

- [ ] F-1~F-4 구현, 출력 스키마 불변
- [ ] 신규 테스트 추가, §2 회귀 명령 전량 PASS (변경된 기대값은 목록·근거 명시)
- [ ] F-3 한글 canonical 형식 = CUE 승인된 방식
- [ ] 8권 before/after 측정표 (read-only)
- [ ] `git status --porcelain` = `annotate.py` (+ 헬퍼/테스트) 만. canonical/tsu 무변경
- [ ] 보고 첫 줄 `git rev-parse HEAD` / `remote -v` / `--show-toplevel`

## 5. 산출물

- 수정 `NAE/pipeline/canonical/annotate.py` (+ 필요 시 헬퍼 모듈)
- 확장/신규 테스트
- `docs/NAE_FULLER_B1_SCRIPTURE_EXTRACTOR_REPORT_C1_001.md`
  (git status / F-1~F-4 diff 요약 / F-3 결정 / pytest 결과 / 8권 before-after / Next)

## 6. 범위 밖 (CUE / HQ)

- B-2 re-normalize (8권) = B-1 커밋 후 별도 Task Order
- Vol.02–08 TSU 생성 = B-2 + P-2 Amendment 후
- F-3 형식 최종 승인 = CUE (필요 시 HQ)
