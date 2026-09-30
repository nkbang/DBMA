# FU-004 (b-1) Vol.08 재검수 큐

- 일자: 2026-09-29 · 생성: `scripts/nae_fuller_vol08_rereview_queue.py` (읽기 전용, 큐 파일만 생성, 재현 가능)
- 근거: 독립 표본 2건(파일럿 17.5%, CUE 표본 27.5%)이 Amendment C의 Q1 오류 2%와 충돌 → `NAE_EUAT_001_FU004_VOL08_SAMPLE_CHECK.md`

## 대상 (verified 5,045 → 재검수 5,005)
파일럿·재표본에서 이미 사람이 판정한 40건(승인 33 / 거부 7)은 제외.

| 우선순위 | 기준 | 건수 |
|---|---|---|
| P0 | CUE 표본에서 R 판정 | 11 |
| P1 | CJK 잔존·스크립트 오염·CUE 표본 C | 81 |
| P2 | triage 플래그 (파일럿 거부율 높은 순: truncated 43% > very_short 33% > quote 31% > rhetorical 29% > conditional 20%) | 1,240 |
| P3 | 신호 없음 (파일럿 무플래그 거부율 19%) | 3,673 |

26배치(200건씩). 배치 001 = P0 11 + P1 81 + P2 108. 배치 002–007 = P2, 008 이후 P3.
사전 추정 거부 기대치는 약 1,155건(P0 1.0, P1 0.9, P2/P3는 파일럿 거부율)이며 표본 오차가 크다.

## 검수 순서 제안 (결정은 사용자)
1. 배치 001(200건)을 먼저 — 결함 밀도가 가장 높아 Amendment C 정정 필요성의 판단 근거가 된다.
2. 배치 002–007(P2 1,240건) 후 P3는 표본 재점검으로 중단 여부 판단: P3 앞 배치에서 거부율이 충분히 낮으면(예: 5% 미만) 나머지는 표본 검수로 대체하는 안을 Amendment로 상정.
3. 검수 산출물(decisions)을 tsu.json `review_status`에 반영하는 단계는 별도(현재 미구현 — rejected 전환은 `tsu.json` 변경이므로 사전 확인 후 진행).

## 사용
```
python scripts/nae_fuller_vol08_rereview_queue.py            # 큐 생성
```
검수 도구(`scripts/nae_fuller_review_recorder.py`)는 배치 ID를 `fuller_v01_batch_NNNN`으로 가정해 v08 배치를 직접 읽지 못한다 — 기록기 배치 ID 확장이 필요하다(미구현).
