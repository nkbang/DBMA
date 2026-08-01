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

## 상태 기록

| 항목 | 상태 |
|---|---|
| Identifier 판단 | Option A 채택(자문) |
| Raw 배치 | 완료 |
| Canonical 정규화 실행 | 완료 (status: ok, 크래시 없음) |
| Canonical 콘텐츠 품질 | **낮음 — 재작업 권고** (본 문서 상단 근거) |
| TSU 생성 / Embedding / Qdrant 인덱싱 | **미실행, 권고하지 않음** |
| 최종 "검증된 canonical 완료" 선언 | **하지 않음** — 위 품질 이슈 미해결 상태
