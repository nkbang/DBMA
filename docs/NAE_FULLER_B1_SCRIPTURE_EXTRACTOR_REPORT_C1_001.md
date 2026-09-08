# B-1 Report — Scripture 추출기 수정 (annotate.py)

- 구현: C1, 최종 조정: CUE
- 일자: 2026-09-08
- git rev-parse HEAD: 70eb286fe586ecd7571fe8bed26d995d5a69cd74
- git remote -v: origin https://github.com/nkbang/DBMA (fetch/push); nas http://100.94.139.122:3000/David/DBMA.git (fetch/push)
- git rev-parse --show-toplevel: /Users/David/DBMA

## git status --porcelain (커밋 직전)
```
 M NAE/pipeline/canonical/annotate.py
 M tests/test_nae_canonical_annotate.py
 M docs/NAE_FULLER_B1_CUE_VERIFICATION_001.md
?? docs/NAE_FULLER_B1_SCRIPTURE_EXTRACTOR_REPORT_C1_001.md
```
canonical / normalize_report / tsu.json 무변경. 출력 스키마(`[{original, canonical}]`, `scripture_references_found`=int) 불변.

## F-1 Roman numeral parser
- `_ROMAN_MAP`(28개 하드코딩) 제거 → `_parse_roman()` 일반 파서 (1–199, 라운드트립 검증으로 `iiii`/`vx` 거부).
- `canonicalize_scripture_ref()` 가 chapter가 로마숫자인 경우 처리.
- 검증: `Ps. xl. 6`→`Psalms 40:6`, `Ps. cxviii. 22`→`Psalms 118:22`, `Rev. xxi. 3`→`Revelation 21:3`.

## F-2 Book 이름 인식 확대
- book 패턴 `[A-Z][a-z]+` → `(?:(?:[1-3]|I{1,3})\s?)?[A-Z][a-zA-Z]+` — 아라비아(1–3) + 로마(I/II/III) 접두, all-caps, 공백 optional.
  (C1 초안은 `[IVX]+` 였으나 finditer 소비로 Vol.02/05/06 refs ~5건 손실 → CUE가 `I{1,3}` 로 축소.)
- 한글: `_KOREAN_REF_ZANG`(장/절) + `_KOREAN_REF_STD`(구분자) + `_KOREAN_SHORT` 약어 + `core.sermon.bible_books.BIBLE_BOOKS` 전체명(신규 테이블 없음). `_KOREAN_FULL_NAMES` 오타("예레미애"/"스게론") 미사용.
- `_resolve_book_name()` 이 영/한/약어/전대문자/번호접두를 canonical 영문명으로 해소. `_NON_BOOK_WORDS`(vol/page/ch/art/no/verse…) 음성 필터.
- 검증: `1 Cor 3:16`→`1 Corinthians 3:16`, `I Cor. xiii. 4`→`1 Corinthians 13:4`, `II Pet. i. 4`→`2 Peter 1:4`, `III John 1:9`→`3 John 1:9`, `ROM 8:1`→`Romans 8:1`, `요 3:16`→`John 3:16`, `롬 8:1-2`→`Romans 8:1-2`.

## F-3 Canonical 형식 = Option A (영문 통일)
- 한글 참조도 영문 canonical(`요 3:16` → `John 3:16`)로 출력. 기존 `John 3:16` 출력·`book_id` 공간과 일관. CUE 권고안.

## F-4 OCR 노이즈 내성
- book↔chapter 사이 `(?P<noise>[^\d\w]{0,5})` (영문자 제외 → chapter 로마숫자 보존), lookahead `(?=[.\s])`.
- 검증: `Rom.. ii. 3`→`Romans 2:3`.

## 음성 케이스 (전부 `[]`)
`page 3:16` / `Vol. iii. 5` / `No. ii. 3` / `Art. iv. 2` / `chapter 3:16` / `the year 1820` / `Christ III. 1` / `David lived 12 years` / `1 year 3:16` / `2 page 5:1` / `IV Cor. iii. 4` / `사랑 3:16` / `사람 2:5`

## pytest
- Task Order §2 10개 파일: **145 passed** (신규 테스트 포함)
- 광역(canonical/scripture/citation/annotate/verse/alias): **277 passed**
- 기존 기대값 변경: 없음 (전부 순증)

## 8권 before/after (수정본 적용, canonical 파일 무수정)

측정 2가지: **whole-text** (canonical.txt 전체 1회) / **per-paragraph**
(canonical.json 문단별 — B-2 re-normalize가 실제로 쓰는 경로).

| Vol | before | whole-text | per-paragraph |
|---|---:|---:|---:|
| 01 | 2 | 315 | 374 |
| 02 | 3 | 194 | 218 |
| 03 | 0 | 87 | 94 |
| 04 | 3 | 62 | 63 |
| 05 | 1 | 106 | 105 |
| 06 | 1 | 65 | 69 |
| 07 | 0 | 35 | 47 |
| 08 | 1 | 178 | 176 |
| **합계** | **11** | **1042** | **1146** |

→ **B-2 예상 `scripture_references_found` = per-paragraph 열** (합계 ~1146).
Vol.01 상위 책: John / Romans / Acts / Luke / Isaiah / Matthew — 진짜 인용. 잡음 폭증 없음.

## Known gap
- 없음 (I/II/III 로마 접두 지원 완료).

## Next
- B-2: 8권 canonical **re-normalize** (수정된 `annotate.py` 반영) — 별도 Task Order.
- B-2 완료 후 Vol.02–08 TSU 생성(F2) 착수 가능 (+ P-2 Amendment).
