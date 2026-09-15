# S2-3/S2-4 — 퍼블릭 도메인 63종 코퍼스 확장 Build Report

- 작성일: 2026-09-15
- 근거: `docs/DBMA_RELEASE_GAP_CLOSURE_PIPELINE_v1.md` S2-3, S2-4
- 결과: STATUS = 성공

## 1. 배경 — 예산 재산정

원 계획(§2.4)은 "패키지 ≤ 1GB" 제약 아래 63종 중 1차분만 선정하는 것을
전제로 했다. 실측 결과 63종의 원문 텍스트(`ocr.txt`) 총합이 **111MB**뿐
이라 선별 없이 **전량 포함해도 예산 안에 들어온다** — 선정 작업을
생략하고 63종 전부를 적재했다.

## 2. 적재 결과

| 항목 | 이전(4건) | 이후(67건) |
|---|---:|---:|
| 출처 문서 | 4 | **67** |
| TSU | 6,380 | **119,595** |
| `output/bench/tsu_dataset.jsonl` | 11M | 197M |
| `data/RAW` | 6.5M | 111M |

신규 63건 저자: Maclaren(17권), Spurgeon 추가분(29권: MTP 27권·NPSP
6권·Evening by Evening 등), Whitefield(4권), Broadus(2권), Dargan(2권),
Keach(1권), Hovey(1권) — 전원 1930년 이전 사망(가장 최근: Dargan
1852–1930), `docs/RELEASE_ASSET_PROVENANCE.md`와 동일 판정 기준으로
전량 퍼블릭 도메인.

## 3. 처리 경로

`ui/pages/processing.py`와 동일한 호출 경로를 헤드리스로 재현했다
(`DBMA_BASELINE_CORPUS_LOAD_REPORT_001.md`와 동일 패턴) — 새 경로를
만들지 않아 ADR-001 무위반.

```
[extract]  텍스트 추출        → 63건 성공, 0건 실패
[chunk]    청킹(1200/120)     → 113,215 chunks(신규분)
[reconcile] registry→TSU→색인 → reconciled 63, failed 0, purged 0
```

**앱 정지 확인 절차:** 실행 전 `ps aux`로 streamlit 미실행 확인 완료.
실행 도중 다른 세션이 띄운 streamlit(PID 72168, 포트 8501, 세션 추적
목록에 없는 프로세스)이 발견돼 **사용자 확인 후 종료**하고 재확인한
뒤 진행했다 — §5.2 함정을 실제로 피한 사례.

## 4. 검증

**오염 검사 (PASS)** — 배포 불가 판정된 자산(`data/beta_corpus/`
전체, Word Biblical Commentary·Anchor Bible Commentary 등)의 문자열이
`tsu_dataset.jsonl`에 0건 확인됨.

**검색 스모크 (PASS)**

| 질의 | 결과 |
|---|---|
| `preparation and delivery of sermons` | 3건 반환 |
| `exposition of scripture` | 3건 반환(Maclaren *Expositions* 매칭) |
| `설교 준비`(한국어) | 3건 반환 — 신규 코퍼스에서도 교차 언어 검색 정상 |

## 5. 배포 영향

- **R4(자산 판정)** 유지 — 신규분 전량 §2 기준 퍼블릭 도메인, 저작권
  위험 없음.
- **패키지 크기** — `output/bench/`(TSU+색인) 457M + `data/RAW` 111M ≈
  568M, 1GB 예산 내.
- **B-3(인용 메타데이터 null)** 영향 범위 확대 — `title`/`author`가
  67건 전체에서 비어 있다(4건일 때와 동일 결함, C1 RQ-1/RQ-2 회신
  대기 중).
- **B-2(doc_type 분류)** 영향 범위 확대 — 신규 63건도 `doc_type` 분류
  재검증 필요(§7 후속 조치).

## 6. 남은 절반 — 성경 본문/한국어 자료 (범위 밖)

이번 확장은 전량 영어 자료다. `docs/DBMA_S1_4_3B_QUALITY_MEASUREMENT_001.md`가
지적한 "검색 결과가 질의와 약하게만 관련될 때 근거 강제가 약하다"는
문제와 맞물려, 코퍼스가 두터워질수록 관련성 있는 검색 결과를 찾을
확률은 높아지나 언어 불일치(한국어 질의 → 영어만 나오는 코퍼스)는
그대로 남는다 — 별도 과제.

## 7. 다음 조치

- [ ] 신규 67건 `doc_type` 분류 재검증(설교/설교학/역사 등 구분)
- [ ] B-3 사이드카 메타데이터(C1 회신 대기 후 구현)
- [ ] S5 패키징 시 `output/bench/` + `data/RAW` 포함 경로 확정(현재
      스크립트는 `data/beta_corpus/`·`data/bible/knrv.json`만 제외 확인됨
      — 이번에 늘어난 `output/bench/` 크기 기준 재확인 필요)

## 8. 기록

```
STATUS:      성공
Changed:     data/RAW/ (+63), data/제련완성본/ (registry +63),
             output/bench/ (TSU 6,380→119,595, 색인 재생성)
             ※ 전부 .gitignore 범위 — 추적 변경 없음
Tests:       오염 검사 PASS, 검색 스모크 3건 PASS
Regression:  미실행 (데이터 적재, 코드 무변경)
Git:         본 문서만 커밋
Next:        §7
```
