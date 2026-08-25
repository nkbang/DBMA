---
title: "Smith's Bible Dictionary (Hackett & Abbot American Edition) — Raw Source Registration"
category: report
created: 2026-08-25
---

# Smith's Bible Dictionary — Raw Source Registration

## 목표

퍼블릭 도메인 성서사전(목회자용, 깊이 있는 판본)을 ADR-021 Source
Registration 파이프라인을 통해 NAE 코퍼스에 추가.

## 선택 근거

**Smith's Bible Dictionary, Hackett & Abbot American Edition (1868–1892,
4 vols)**. William Smith 원편집, Horatio B. Hackett·Ezra Abbot 증보.
공공영역 성서사전 중 가장 포괄적이며(원판보다 항목 확장), 목회자 강해
준비용으로 가장 널리 채택되는 표준판.

- 출처: [archive.org/details/BibleDictionary.williamSmithEditor.HackettAbbotFullerEtc.American](https://archive.org/details/BibleDictionary.williamSmithEditor.HackettAbbotFullerEtc.American)
- 저작권: 1868–1892 출판, 퍼블릭 도메인 확정

## 현재 상태

- [x] 4권 PDF(원본 스캔) + djvu.xml(페이지 구조 OCR) 다운로드 및 크기 검증
- [x] ADR-021 Source Registration 파이프라인 통과 (4권 전부 `QUALITY_PASSED`)
- [x] `extract.py`에 `extract_from_djvu_xml()` 추가 (하위 결함 수정)
- [x] 회귀 테스트 4건 추가, 기존 170개 테스트 전부 PASS
- [ ] TSU Builder / Extraction → Chunking → Embedding (ADR-021 범위 밖,
      후속 단계)

진행률: 등록 완료(100%) / 전체 코퍼스 편입(TSU~임베딩)은 후속 작업 대기

## 발견한 결함과 수정

이 archive.org 항목에는 hOCR 파일이 없고, `_djvu.txt`(평문 OCR)에는
페이지 구분자(`\x0c`)가 전혀 없어 ~900페이지 볼륨 전체가 "1페이지"로
붕괴되는 결함을 발견(기존 PBC1765 사례와 동일 유형, `extract.py` 기존
docstring에 문서화되어 있던 클래스의 결함). `original.pdf`도 스캔
이미지 전용(텍스트 레이어 없음)이라 PDF 폴백도 무의미했음.

**수정**: `_djvu.xml`(djvutoxml 산출물)은 hOCR과 동일하게 페이지별
`<OBJECT>` 구조를 보존한다는 점을 확인 → `NAE/pipeline/canonical/extract.py`에
`extract_from_djvu_xml()` 추가, 우선순위를 hOCR 다음·평문 OCR TXT 이전에
배치. 기존 소스(Fuller/Hiscox/Dagg)는 djvu.xml 파일이 없으므로 동작에
영향 없음(additive-only).

- 수정 전(Vol.1): 1 page, 5.8MB 단일 블록
- 수정 후(Vol.1): 921 pages, 917 non-empty — PyMuPDF의 실제 PDF 페이지
  수(921)와 일치

## 등록 식별자

| source_id | 권 | 범위 | work_id 접미사 |
|---|---|---|---|
| BAP-REF-SMITH-VOL01 | 1 | A–G | vol_1_a_g |
| BAP-REF-SMITH-VOL02 | 2 | G–M | vol_2_g_m |
| BAP-REF-SMITH-VOL03 | 3 | M–R | vol_3_m_r |
| BAP-REF-SMITH-VOL04 | 4 | R–Z | vol_4_r_z |

author_id: `smith_william` / edition_slug: `hackett_abbot_american_1868`

## 원본 위치

`NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol{1..4}/`
(각 `original.pdf` + `ocr.txt` + `djvu.xml` + `metadata.json`)

`NAE/pipeline/registration/state/source_manifest.yaml`에 4건 등록 완료
(체크섬 포함).

## 다음 조치 — TSU 인계 보류 (2026-08-25)

TSU Builder(`NAE/pipeline/tsu/builder.py`)로 인계하기 전, Vol.1(921p)만
canonical 단계(무료, LLM 미사용)로 시험 실행해 candidate 수를 확인한
결과 **37,323건**(4권 전체 약 15만 건)이 나왔다. `NAE/pipeline/index/indexer.py`를
확인하니 Qdrant 인덱싱 직전 단계가 예외 없이 `tsu.json`/`tsu_verified.json`
(claim+doctrine 스키마)만 읽도록 하드와이어드되어 있어, 일반 텍스트를
그대로 임베딩하는 경로가 코드에 없음을 확인.

TSU claim 추출은 candidate 1건당 LLM 호출 1회 — 15만 건이면 로컬 모델
기준 수십~수백 시간. 게다가 TSU 파이프라인은 Fuller/Hiscox/Dagg 같은
**논증형 신학 문서**의 "주장(claim)" 추출용으로 설계되어 있어, 사전
표제어("Aaron: Amram의 아들...")처럼 사실/어휘 항목이 대부분인 문서에는
스키마가 맞지 않는다(candidate 샘플에도 Google 스캔 상용구 같은
front-matter 노이즈가 "claim 후보"로 섞여 들어옴).

**결정(2026-08-25, 사용자 승인)**: 강행하지 않고 보류. reference(사전류)
콘텐츠 전용 임베딩 경로(TSU claim 추출 우회 — chunking → embed → Qdrant)
설계는 별도 세션 과제로 미룸. 지금 세션에서는 **원본 등록(raw
registration)까지만 완료**된 상태 — 4권 raw item + metadata.json +
source_manifest.yaml 등록은 유효하며, 향후 reference 경로가 설계되면
그대로 재사용 가능.

진행률(수정): 원본 등록 100% / reference 임베딩 경로 설계 0% (보류)
