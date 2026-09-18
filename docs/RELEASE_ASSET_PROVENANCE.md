# 배포 자산 저작권 전수 확인 — S2-1 / B-4

- 작성자: CUE · 일자: 2026-09-15
- 근거: `docs/NAE_FREE_DISTRIBUTION_PLAN_v1.md` §2, `docs/DBMA_RELEASE_GAP_CLOSURE_PIPELINE_v1.md` S2-1(B-4)
- 확인 대상: `data/beta_corpus/`(156M), `data/bible/`(4.9M) — 원 계획 문서가
  "출처 미검증"으로 표시했던 두 디렉터리 전량(파일 16개, 전수 확인 완료)

## 결론 — **`data/beta_corpus/` 전량 배포 불가 확정**

`data/beta_corpus/`의 12개 파일(commentaries 4 + bible_study 8) 전부
도서 스캔본으로 확정됐다(commentaries는 저자·발행사 표기로 즉시 확인,
bible_study는 2026-09-15 사용자 확인). 무료 배포라도 복제·배포는 저작권
침해다(`NAE_FREE_DISTRIBUTION_PLAN_v1.md` §2.1). Phase A(법적 정리)가
끝나기 전 어떤 패키징 스크립트도 `data/beta_corpus/`를 포함해서는 안 되며,
사실상 **이 디렉터리 전체를 배포판 범위에서 영구 제외**하는 것으로
정리한다.

## 전수 확인 결과 (16개 파일)

### 1. `data/beta_corpus/commentaries/` — 4개 파일, **배포 절대 불가**

| 파일 | 판정 | 근거 |
|---|---|---|
| `2 Chronicles, Volume 15 (Word Biblical Commentary) (Raymond B. Dillard).pdf` | ❌ 배포 불가 | Word Biblical Commentary 시리즈 — Zondervan/Thomas Nelson 발행 현재 시판 학술 주석 |
| `2 Kings The Anchor Bible Commentary (Mordechai Cogan and Hayim Tadmor).pdf` | ❌ 배포 불가 | Anchor Bible 시리즈 — Yale University Press 발행 현재 시판 학술 주석 |
| `2 Kings The Power and the Fury (Dale Ralph Davis).pdf` | ❌ 배포 불가 | Christian Focus/Christian Focus 발행 현재 시판 주석 |
| `2 Kings, Volume 13 (Word Biblical Commentary, David Allen Hubbard 등).pdf` | ❌ 배포 불가 | Word Biblical Commentary 시리즈 — 동일 |

**개인 소장 스캔본으로 추정되며, CLAUDE.md "금지 사항 — 상용 전자책을 기본
코퍼스에 적재 금지"에 정확히 해당한다.** 개인 연구용 보관과 무료 배포용
동봉은 전혀 다른 문제다.

### 2. `data/beta_corpus/bible_study/` — 8개 파일, **배포 불가 확정 (사용자 확인, 2026-09-15)**

| 파일 | 페이지 | 판정 | 근거 |
|---|---:|---|---|
| `3. 마가복음.pdf` | 341 | ❌ 배포 불가 | 도서 스캔본 — 사용자 확인 |
| `5. 요한복음1.pdf` | 251 | ❌ 배포 불가 | 상동 |
| `6. 요한복음2.pdf` | 263 | ❌ 배포 불가 | 상동 |
| `9. 로마서1.pdf` | 261 | ❌ 배포 불가 | 상동 |
| `11. 고린도전서.pdf` | 331 | ❌ 배포 불가 | 상동 |
| `12. 고린도후서.pdf` | 224 | ❌ 배포 불가 | 상동 |
| `7. 사도행전1.pdf` | 305 | ❌ 배포 불가 | 상동 |
| `8. 사도행전2.pdf` | 391 | ❌ 배포 불가 | 상동 |

CUE가 OCR 스캔 흔적(`Adobe Acrobat Pro ClearScan`)으로 세운 가설("출판된
책을 스캔한 것으로 보인다")이 사용자 확인으로 확정됐다 — 도서 스캔본,
개인 저작 아님. `commentaries/`와 동일하게 배포 절대 불가로 판정한다.

### 3. `data/bible/knrv.json` — **배포 불가 (HQ 결정 D1 선결 필요)**

파일명(`knrv`)과 실제 본문("태초에 하나님이 천지를 창조하시니라" 등)을
대조하면 **개역개정(대한성서공회 발행, 1998)** 전문이다.
`core/bible_text.py:14`의 코드 주석도 동일하게 명시한다("개역개정
knrv.json"). 대한성서공회 저작권 대상이며, `NAE_FREE_DISTRIBUTION_PLAN_v1.md`
§8-1이 이미 "허락 문의 / 공개 번역본 / 사용자 직접 투입" 중 택1이
필요하다고 명시한 바로 그 자료다. **HQ 결정(D1) 없이는 동봉 불가.**

**추가 조사 결과(2026-09-15, S2-2) — D1 "공개 번역본" 선택지가 실현
가능함을 확인:** 대한성서공회 자체 저작권 FAQ
([bskorea.or.kr](https://www.bskorea.or.kr/bbs/board.php?bo_table=copyright_faq&wr_id=5))에
따르면 **『성경전서 개역한글판』(1961)은 저작재산권 보호기간이 지나
저작권료 없이 사용 가능**하다 — 단 성명표시권(원저작자 표시)과
동일성유지권(무단 변경·절삭 금지)은 지켜야 한다. 반면 개역개정(1998)을
포함해 이후 번역본(공동번역 1977, 표준새번역 1993, 새번역 2001)은
[별도 FAQ](https://www.bskorea.or.kr/bbs/board.php?bo_table=copyright_faq&wr_id=3)에서
여전히 저작권 보유로 명시된다 — `knrv.json`(개역개정)의 배포 불가 판정은
그대로 유지된다.

**실행 항목(별도 작업, 이 PR 범위 밖):** 개역한글판(1961) 전문(약 3만
1천 절)을 신뢰할 수 있는 출처에서 확보해 `docs/NAE_BIBLE_TEXT_JSON_SPEC.md`
스키마로 변환하는 작업이 필요하다 — 동일성유지권을 지키려면 원문을
그대로 옮겨야 하므로 LLM 재구성이 아니라 검증 가능한 출처에서 직접
가져와야 한다. 후보: 한국어 위키문헌(퍼블릭도메인 텍스트 저장소)의
개역한글판 항목. 착수 전 출처 신뢰도를 별도로 확인할 것.

### 4. `data/bible/reference.json` — **안전, 배포 가능**

파일 자체가 `"_note": "PLACEHOLDER. 실제 번역본이 아닙니다."`로 명시돼
있다. 실제 성경 본문이 아니라 스키마 예시이므로 저작권 문제가 없다.

## S2-1 완료 판정 (R4)

| 판정 | 파일 수 | 용량 |
|---|---:|---:|
| ❌ 배포 절대 불가 | 13 (`commentaries/` 4 + `bible_study/` 8 + `knrv.json` 1) | ~161.5M |
| ✅ 배포 가능 | 1 (`reference.json`) | 39K |

**R4(자산 100% 출처 판정) 완료 — 판정에 미확정 항목 없음.** `data/beta_corpus/`
전량(16개 중 12개)과 `data/bible/knrv.json`이 배포 불가로 확정됐다.
패키징 스크립트(`build_mac_package.sh`, `setup_beta_tester.command`)가
이를 포함하지 않는지는 이미 확인했다(아래).

## 즉시 확인 완료

`scripts/build_mac_package.sh`, `scripts/setup_beta_tester.command`,
`scripts/reset_for_release.py` 3개 전부 `grep`으로 확인 — `beta_corpus`,
`knrv`, `data/bible` 참조가 **하나도 없다.** 현재 패키징 경로는 이 위험
자산들을 우발적으로 포함하지 않는다. 단, S5(패키징) 작업 시 새 스크립트가
`data/` 전체를 통째로 복사하는 방식으로 짜이지 않도록 주의해야 한다.

## 권고 조치

1. ~~패키징 스크립트 참조 확인~~ — 완료, 위 "즉시 확인 완료" 참고.
2. ~~`bible_study/` 8건 출처 확인~~ — 완료, 도서 스캔본으로 확정(위).
3. **성경 본문(D1)**: `NAE_FREE_DISTRIBUTION_PLAN_v1.md` §8-1 결정을
   기다린다. 결정 전까지 온보딩 화면은 "성경 본문을 직접 추가하세요"
   안내로 대체(§5.1 공개 번역본 경로 확정 전 임시 조치).
4. **배포판 최소 서재**: NAE 퍼블릭 도메인 트랙(스펄전 4종 등, 이미 확인된
   퍼블릭 도메인)만 동봉 대상으로 삼는다 — `data/beta_corpus/`는 배포판이
   아니라 CUE/C1 로컬 개발·테스트용 자산으로 범위를 분리한다(전량 배포
   제외 확정).

이 파일들을 삭제하거나 이동하지 않았다 — 개인 연구용 보관 여부는 사용자
판단이며, 이 보고서의 역할은 "무엇을 배포판에 넣으면 안 되는지" 판정까지다.
