# STEP5 Source Comparison Report

작성일: 2026-07-31
배경: STEP5-B에서 `WebFetch` 도구로 CCEL/Wikisource/Reformed Reader 등에 접근을 시도했으나, 이 도구가 내부적으로 소형 모델을 거쳐 콘텐츠를 **요약**해 반환하는 구조여서 신앙고백서 원문(18개 조항, 약 2,500단어)의 **verbatim(원문 그대로) 텍스트를 확보하지 못함**을 확인. 이에 따라 신뢰 가능한 원문 확보 방법을 재검토.

## 비교 대상

### CCEL (Christian Classics Ethereal Library)

| 항목 | 평가 |
|---|---|
| Verbatim availability | 확인 불가 — 이번 세션 도구로 CCEL 사이트 자체에 접근하지 못함(검색 결과에 CCEL 페이지가 나타나지 않음) |
| Metadata quality | 알려진 바로는 높음(서지정보 체계적) — 실측 미확인 |
| Provenance reliability | 높음(기독교 고전 전문 아카이브, 학술 인용 빈도 높음) |
| OCR risk | 낮음(텍스트 직접 입력 방식으로 알려짐) |
| 이번 세션 결론 | **접근 실패** — 유효 URL을 찾지 못함, 별도 조사 필요 |

### Internet Archive

| 항목 | 평가 |
|---|---|
| Verbatim availability | 스캔 이미지 + OCR 텍스트 병행 제공 — OCR 텍스트는 verbatim이 아닐 수 있음(오탈자 위험) |
| Metadata quality | 중간 — 스캔 판본별로 편차 큼 |
| Provenance reliability | 높음(원본 이미지 대조 가능, 이 프로젝트에서 "이미지 vs 텍스트 교차검증"에 가장 유리) |
| OCR risk | **높음** — 스캔본 OCR 특성상 조항 번호/구두점 오류 가능성 |
| 이번 세션 결론 | 미시도 (WebFetch로는 스캔 이미지 자체를 다룰 수 없음 — 별도 접근 방식 필요) |

### 기타 Public Domain Repository (이번 조사에서 검색된 것)

| 저장소 | 특징 | 평가 |
|---|---|---|
| Wikisource | 자원봉사 전사(transcription) 기반, 위키 원칙상 원문 충실도에 대한 커뮤니티 검증 존재 | WebFetch 시도 결과 **요약만 반환**, verbatim 미확보. `Special:Export`(raw wikitext export) 엔드포인트로도 시도했으나 동일하게 요약됨 — **WebFetch 도구 자체의 구조적 한계**(소형 모델이 항상 개입)로 판명 |
| Reformed Reader (reformedreader.org) | 미국 침례교 신앙고백 모음집 사이트 | WebFetch 자체가 "완전한 verbatim 재현에 한계가 있다"고 명시적으로 응답 — 신뢰도 낮음(불확실) |
| baptistdocuments.tripod.com | 개인/커뮤니티 운영 아카이브 | 미시도, 출처 신뢰성 검증 안 됨 |
| PDF 소스(storage2.snappages.site, baptiststudiesonline.com) | PDF 원문 | 미시도 — PDF는 WebFetch가 HTML 변환 후 처리하므로 verbatim 확보 가능성이 오히려 더 낮을 수 있음 |

## 핵심 발견

**문제의 본질은 저장소 선택이 아니라 도구(WebFetch)의 구조적 한계다.** WebFetch는 "URL 콘텐츠를 가져와 프롬프트로 처리 → 소형 모델이 응답 생성" 방식이므로, 어떤 저장소를 선택하든 verbatim 텍스트를 그대로 반환하지 않고 항상 요약/재서술을 거친다. 이는 STEP5_PD_VERIFICATION.md가 요구하는 "원문 변경 금지" 원칙과 근본적으로 충돌한다.

## 평가 요약

| 저장소 | Verbatim 가능성(이 세션 도구 기준) | Metadata 품질 | Provenance 신뢰성 | OCR 위험 |
|---|---|---|---|---|
| CCEL | 불명(접근 실패) | 높음(알려짐) | 높음 | 낮음(알려짐) |
| Internet Archive | 낮음(OCR 텍스트 시 위험, 이미지는 도구로 처리 불가) | 중간 | 높음 | 높음 |
| Wikisource | **이번 도구로는 불가능** (요약만 반환 확인) | 중간(커뮤니티 검증) | 중간~높음 | 낮음(전사 기반) |
| Reformed Reader | 불명(도구가 스스로 한계 인정) | 낮음(비학술 사이트) | 낮음~중간 | 낮음 |

## 결론

- 이번 세션의 `WebFetch` 도구만으로는 **어떤 저장소를 택하더라도 verbatim 원문 확보 불가**로 판단
- 대안은 STEP5_IMPORT_FORMAT_DECISION.md에서 형식 관점으로, STEP5_SOURCE_MANUAL_VERIFY.md에서 사람 개입 검증 관점으로 각각 다룸
