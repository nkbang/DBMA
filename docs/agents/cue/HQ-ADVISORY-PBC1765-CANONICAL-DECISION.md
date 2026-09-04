# HQ Advisory — PBC1765 Canonical Admission Decision

작성일: 2026-08-01
작성자: CUE (HQ 자문 역할 겸 실행, 사용자 위임에 따름)
관련: `evidence/phase5_2/pbc1765_acquire_009/hq-report.md`의 HQ Decision Request(Option A/B/C/D)

## 자문 — Identifier 불일치 판단

**결론: Option A(canonical normalization 설계로 admit) 채택 근거 충분.**

근거: CUE-RECONCILIATION-010에서 `confeo00phil_djvu.txt`(실제 다운로드된 스캔 OCR)를 직접 grep으로 재검증한 결과, 아래 7개 조건이 IA metadata 주장이 아니라 **원문 텍스트 자체**로 확인됨:
- 표제: "Baptift confeffiofi of faith"(장식체 s, "Baptist confession of faith")
- Philadelphia Association 1742년 채택 언급: "adopted by the association at Philadelphia... 1742"(원문 내 명시)
- 인쇄지/연도: "phia, printed by Ar.t. Armhrttflcr in Rac[e-street]... 1765" (Philadelphia, Ant. Armbruster, 1765 — IA metadata의 "Ant. Armbruster" 표기와 정확히 일치)
- 챕터 구조: "CHAP. I. Of the HOLY SCRIPTURES" 등 다수 확인

`plainbookofconfe00phil`(질의 식별자)과 `confeo00phil`(반환 식별자)의 불일치는 원본 등록 시 부정확하게 추정된 식별자였을 가능성이 높고, 실제 콘텐츠 검증이 이를 압도한다고 판단. IA 자체도 리다이렉트로 동일 항목임을 확인(C1 보고).

## 실행 내역

1. `NAE/corpus/raw/archive_org/books/PBC1765/`에 `original.pdf`(quarantine의 `confeo00phil.pdf` 복사), `ocr.txt`(quarantine의 `confeo00phil_djvu.txt` 복사) 배치 — 기존 `books/{AF1815,PBC1742,TH1612}` 카테고리 규약과 일치시킴(최상위 `raw/archive_org/{ID}/` 폴더는 과거 미완성 잔재로 판단, 사용하지 않음)
2. `python -m NAE.pipeline.canonical.runner --identifier PBC1765` 실행 — **이 저장소에서 canonical 파이프라인이 처음으로 `status: ok`를 낸 사례** (기존 PBC1742/AF1815/TH1612는 전부 raw 파일이 `ocr.txt`/`original.pdf` 규약과 맞지 않아 미시도 또는 실패 상태로 남아 있었음)
3. `NAE/corpus/canonical/PBC1765/{canonical.txt, canonical.json, normalize_report.json}` 생성됨

## ⚠️ 중요 — 품질 검증 결과, 하위 단계 진행 보류 권고

파이프라인의 `status: ok`는 **크래시 없이 끝났다는 뜻이지 내용 품질을 보증하지 않음**을 직접 확인:

- `canonical.json`의 앞 60개 단락 중 **39개(65%)가 OCR 노이즈**(표지/속표지 스캔 잔재로 보이는 특수문자·짧은 조각) — 구조 정리(Stage 2.2) 단계가 이를 걸러내지 못함
- 헤딩(챕터) 감지 25건 중 다수가 챕터 번호를 놓치거나(IV, V, XIII, XV, XVI, XVIII, XIX 등 확인 안 됨) 노이즈를 헤딩으로 오인식("C 5", "2CC." 등)
- `scripture_references_found: 0` — 원문에 각주 형태의 성경 참조가 육안으로 확인되는데도("a 2 Tim. 3. 19 16, 17..." 등) 정규식이 OCR 노이즈로 인해 전혀 매칭하지 못함

**권고**: 
1. `canonical_admission`은 "raw→canonical 1차 통과" 수준으로만 인정하고, **TSU 생성/embedding/Qdrant indexing으로 자동 진행하지 말 것** — 노이즈가 그대로 하위 단계에 전파되어 벤치마크·검색 품질을 오염시킬 위험
2. 후속 조치 후보(실행 안 함, HQ 판단 필요):
   - hOCR(`confeo00phil_hocr.html`, 현재 `removed_excess_artifacts/`에 보관 중)이 djvu 텍스트보다 레이아웃 인식이 나을 수 있어 재추출 소스로 검토
   - `NAE/pipeline/canonical/structure.py`의 노이즈/헤딩 감지 정규식이 이 스캔본 특유의 장식체(long-s) OCR 왜곡에 취약 — 정규식 튜닝 또는 별도 전처리 필요
   - 소규모 수동 QA(사람이 canonical.txt 일부를 원문과 대조)를 canonical 승인의 최소 조건으로 추가하는 것을 Evidence Package Standard에 반영 검토

## [2026-08-01 추가] 품질 개선 시도 — hOCR 기반 재추출

사용자 승인("승인한다")에 따라 품질 개선을 시도함.

**가설 1(신뢰도 기반 노이즈 필터링) — 기각**: hOCR의 단어별 `x_wconf` 신뢰도를 직접 확인한 결과, 명백한 본문(챕터 내용)과 명백한 노이즈(표지 잔재)의 신뢰도가 둘 다 균일하게 낮음(중앙값 2/100)을 확인 — 이 문서의 고어체 활자(장식체 s 등) 특성상 신뢰도가 노이즈 판별에 쓸모없다고 판단, 진행하지 않음.

**가설 2(페이지 구조 보존) — 채택, 부분 성공**: `djvu.txt`에 페이지 구분자(`\x0c`)가 아예 없어 전체 문서가 "1페이지"로 처리되었고, 이 때문에 머리말/꼬리말 반복 감지·페이지별 각주 추출 등 구조 정리 로직 다수가 사실상 무력화되어 있었음을 확인. `hOCR`은 실제 페이지 경계(114개)를 갖고 있어, `NAE/pipeline/canonical/extract.py`에 `extract_from_hocr()`를 신규 구현(hOCR 우선, ocr.txt/PDF는 그대로 폴백 유지)하고 `hocr.html`을 raw 디렉토리에 배치해 재실행.

**개선된 항목**:
- `page_count`: 1 → 114 (실제 페이지 구조 인식)
- `footnotes_extracted`: 0 → 38 (페이지별 각주 영역 탐지가 실제로 작동)
- HTML 엔티티(`&gt;` 등) 잔존 버그 발견·수정(`html.unescape()` 누락)
- `paragraph_count`: 최초 hOCR 시도에서 2로 붕괴하는 회귀를 발견·수정(`ocr_par` 경계를 빈 줄로 보존하지 않아 전체가 한 문단으로 뭉개짐) — 최종 1046개 문단으로 정상화

**여전히 남은 문제(추가 조치 없이 종료)**:
- 앞부분 60개 단락 중 37개(62%)가 여전히 표지/속표지 OCR 노이즈 — `SCAN_NOISE_PATTERN`이 순수 기호로만 이루어진 줄만 잡아내며, 이 노이즈처럼 짧은 단어 조각과 기호가 섞인 줄은 잡지 못함
- 챕터 헤딩 22개 중 다수 번호(IV, V, VII, VIII, XIII, XV, XVI, XVIII, XIX, XXII, XXIII, XXV, XXVII-XXIX, XXXII)가 여전히 별도 헤딩으로 인식되지 않음 — 단, 본문 내용 자체가 유실된 것은 아니고 헤딩 태깅만 누락된 것으로 보임(해당 구간 문단들을 육안 확인 결과 내용은 연속 흐름 안에 존재)
- **이 이상의 튜닝은 보류**: `SCAN_NOISE_PATTERN`/헤딩 정규식을 이 한 문서에 맞춰 더 조정하면 다른 문서(향후 SLBC1689, TH1612 등)에 과최적화되어 역효과를 낼 위험 — 여러 문서가 축적된 후 공통 패턴 기반으로 재검토 권고

## 상태 기록

| 항목 | 상태 |
|---|---|
| Identifier 판단 | Option A 채택(자문) |
| Raw 배치 | 완료 (hocr.html 추가 배치) |
| Canonical 정규화 실행 | 완료 (status: ok, hOCR 소스로 재실행) |
| Canonical 콘텐츠 품질 | **개선됨(페이지구조/각주/엔티티), 그러나 여전히 부분적** — 표지 노이즈·일부 헤딩 태깅 누락 잔존 |
| TSU 생성 / Embedding / Qdrant 인덱싱 | **미실행, 여전히 권고하지 않음** — 노이즈 잔존 상태로 하위 단계 진행 시 오염 위험 |
| 최종 "검증된 canonical 완료" 선언 | **하지 않음** — 부분 개선일 뿐, 완전 정제 아님
