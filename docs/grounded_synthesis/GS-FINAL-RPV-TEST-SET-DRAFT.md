# GS-FINAL-RPV Test Set — DRAFT (HQ 최종 승인 전, preflight 대기)

- 상태: **조건부 승인** (HQ, 2026-09-28) — RPV-01~07 PASS 기준을 "grounded 고정"에서
  "corpus snapshot 기준 기대 결과와 일치"로 재정의하기 위해 preflight 결과 대기 중
- 이 문서는 C1 preflight Work Order가 참조할 **질문 텍스트 정본**이다.
  WO 자체에는 질문 텍스트가 누락되어 있었으므로 이 파일로 보강한다.
- 실행 금지: 이 문서는 정의 단계 산출물이며, 실제 Real Pastoral Query Execution은
  preflight 결과 + HQ 최종 승인 후에만 시작한다.

## Preflight 실행 전 공통 확인 사항

- 실행 위치: `/Users/David/DBMA` (main, 병합 커밋 `c8f7e41a` 포함 여부 확인 후)
- G0 비-GS 변경(`config.yaml`, `core/candidate_generator.py`,
  `core/hybrid_candidate_pipeline.py`, `scripts/merge_nae_corpus.py`,
  `scripts/process_unprocessed_nae.py`, `scripts/test_default_corpus_query.py`)은
  RPV 실행 환경에서 제외한다.
- `tsu_manifest.json`의 sha256과 실행 시각을 먼저 기록한다.

## RPV 질문 목록 (13개)

| RPV-ID | 범주 | 질문 텍스트 | 비고 |
|---|---|---|---|
| RPV-01a | Biblical Text | 로마서 8장 28절의 헬라어 원문에서 "모든 것이 합력하여 선을 이룬다"는 표현의 문법 구조는 어떻게 되어 있습니까? | Default corpus |
| RPV-01b | Biblical Text | 요한일서와 요한복음에서 "사랑"(ἀγάπη)이 사용되는 용례 차이가 있습니까? | Default corpus |
| RPV-02 | Exegetical/Interpretive | 야고보서 2장의 "행함이 없는 믿음은 죽은 것"이라는 구절을 로마서의 이신칭의 교리와 어떻게 조화시킬 수 있습니까? | Default corpus |
| RPV-03a | Theological | 개혁주의 관점에서 예정론과 인간의 자유의지는 어떻게 양립합니까? | Default corpus |
| RPV-03b | Theological | 침례교 신앙고백(1689 LBC 등)에서 성찬에 대한 입장은 무엇입니까? | Default corpus (SLBC1689) |
| RPV-04 | Historical/Background | 1세기 로마 제국의 노예 제도가 빌레몬서의 배경을 이해하는 데 어떤 영향을 줍니까? | Default corpus |
| RPV-05a | Multi-source | 산상수훈의 팔복(마태복음 5장)에 대해 여러 주석가들의 해석을 비교해 주십시오. | Default corpus, 다출처 기대 |
| RPV-05b | Multi-source | 칭의(justification) 교리에 대해 Fuller와 다른 저자들의 견해 차이가 있습니까? | Default corpus (Fuller 등) |
| RPV-06a | Personal + Default Corpus | [fixture 설교노트: 요한복음 15장 포도나무 비유] 관련해 참고할 만한 추가 자료가 있습니까? | **fixture 업로드 후 실행 — 아래 §fixture 참고** |
| RPV-06b | Personal + Default Corpus | [fixture 개인자료: 성령의 은사] 제 개인 서재 자료를 우선으로, 부족하면 기본 코퍼스에서 보충해서 정리해 주십시오. | **fixture 업로드 후 실행** |
| RPV-07 | Sermon Research | 이번 주 설교 본문이 누가복음 15장(잃어버린 아들 비유)입니다. 설교 개요를 짜는 데 참고할 신학적/역사적 포인트를 정리해 주십시오. | Personal+Default |
| RPV-08a | Insufficient Evidence | "김민수 목사"라는 신학자가 주장했다는 "제3의 은혜론"의 핵심 내용은 무엇입니까? | 가공 인물, 근거 없음 기대 |
| RPV-08b | Insufficient Evidence | (실행 직전 manifest hash 기준으로 확정 — 아직 미확정, §fixture 참고) | 통제 질의 |

## RPV-06a/06b fixture 사양 (preflight에서 함께 처리)

- 테스트 계정: **HQ/CUE가 별도 지정 필요** (아직 미확정 — C1은 preflight 단계에서
  임의 계정을 쓰지 말고, 지정받을 때까지 이 두 항목만 보류 가능)
- fixture 문서 A (RPV-06a용): 제목 "요한복음 15장 포도나무 비유 설교노트"(가제),
  내용은 C1이 preflight 중 임의 고정하되 문서 전문을 raw output에 포함
- fixture 문서 B (RPV-06b용): 제목 "성령의 은사 개인 연구노트"(가제), 동일 절차
- preflight 산출물: 실제 업로드 후 시스템이 생성한 evidence_id를 그대로 기록
  (추정 금지)

## RPV-08b 통제 질의 확정 절차

1. `tsu_manifest.json` sha256 + 시각 기록
2. 후보 질의 1~2개를 시험 실행해 RankedCandidate 0건인 것을 확인
3. 0건 확인된 질의를 RPV-08b 최종 텍스트로 이 문서에 업데이트

## Preflight 보고 형식 (C1 → CUE)

RPV-ID별로:
```
RPV-ID:
실행 명령:
raw 출력 (RankedCandidate 개수/ID 또는 fixture evidence_id):
기대 결과 판정: grounded 가능 / insufficient_evidence가 정상
```
