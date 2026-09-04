# STEP5 Import Format Decision

작성일: 2026-07-31
배경: STEP5_SOURCE_COMPARISON.md에서 확인된 "WebFetch로는 어떤 저장소도 verbatim 확보 불가" 문제를 전제로, 원문을 어떤 형식으로 최종 확보·저장할지 결정.

## 검토 대상

### TXT
| 기준 | 평가 |
|---|---|
| Text fidelity | 최고 — 서식 없이 순수 텍스트만 담으므로 변환 손실 최소 |
| Structure preservation | 낮음 — 조항 번호/제목이 일반 텍스트 줄바꿈으로만 구분되므로, 사람이 직접 조항 경계를 표시(예: "Article 1." 줄 유지)해야 함 |
| TSU suitability | 높음 — `scripts/ingest_nae_source.py`(STEP4-D 구현)가 현재 `.txt`/`.md`만 지원(`_extract_text()`), 추가 파서 개발 불필요 |

### HTML
| 기준 | 평가 |
|---|---|
| Text fidelity | 중간 — 마크업 제거 과정에서 변형 위험(예: 각주 번호가 본문에 섞임) |
| Structure preservation | 높음 — `<h2>`/`<ol>` 등으로 조항 구조가 명시적으로 보존됨 |
| TSU suitability | 낮음 — 현재 `scripts/ingest_nae_source.py`는 HTML 추출기를 갖지 않음(Logos 스크립트만 `core/extractors.py::extract_text_from_html` 보유) — 지원 추가 시 코드 변경 필요 |

### PDF
| 기준 | 평가 |
|---|---|
| Text fidelity | 판본에 따라 다름 — 스캔 PDF는 OCR 필요(위험 큼), 텍스트 PDF는 fidelity 높음 |
| Structure preservation | 중간 — 페이지/폰트 정보는 남지만 논리적 조항 구조는 별도 파싱 필요 |
| TSU suitability | 중간 — `core/tsu_builder.py`가 PDF heading 처리 경로(`PdfHeadingProvider`)를 이미 갖고 있으나, `scripts/ingest_nae_source.py`는 현재 PDF 추출기를 사용하지 않음(STEP4D_IMPLEMENTATION_PLAN.md에서 "PDF는 최소 구현 범위 밖"으로 명시됨) |

## 결정

**Preferred: TXT**

근거:
1. 이번 STEP4-D에서 이미 구현·테스트·커밋된 `scripts/ingest_nae_source.py`가 TXT를 즉시 지원 — 추가 코드 변경 없이 진행 가능
2. Text fidelity가 가장 높아 "원문 변경 금지" 원칙 준수에 유리 — 변환 손실이 개입할 여지가 가장 적음
3. 조항 구조는 TXT 안에서도 사람이 원문 그대로("Article 1. Of the Scriptures." 형태)를 보존하면 충분히 유지 가능 — `core/tsu_builder.py`의 `HeadingStack`(ATX 스타일 마크다운 헤딩 감지)은 TXT에서 자동 헤딩 인식은 안 되지만, 이는 STEP4_TSU_QUALITY_CRITERIA.md의 "Confession Statement Completeness" 기준으로 별도 확인 가능한 영역이며 원문 확보 형식 결정에 필수 요소는 아님

## 보류: HTML/PDF

- HTML: 향후 구조 보존이 중요해지면(예: 대량 자료 자동 처리 필요 시) `core/extractors.py::extract_text_from_html`을 `scripts/ingest_nae_source.py`에 추가하는 확장 검토 가능 — 이번 STEP5 범위 밖
- PDF: 스캔본 확보 시 OCR 위험이 크므로, 확보 가능하다면 텍스트 기반 PDF만 우선 검토 — 이번 결정에서는 채택하지 않음

## TXT 확보 시 준수 사항 (STEP5_SOURCE_MANUAL_VERIFY.md와 연동)

- 조항 번호와 제목("Article N. Of ...")을 원문 그대로 줄 단위로 보존
- 마크다운 문법(`#`, `*` 등) 임의 추가 금지 — 원문에 없는 서식 삽입은 "원문 변경"에 해당
- UTF-8 인코딩, 줄바꿈은 원문 단락 구분을 그대로 반영
