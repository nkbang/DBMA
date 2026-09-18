# Invalidated Decision Records

## batch_0033 (2026-09-16 invalidated)

`batch_0033_part1..5_decisions.json` (276건: Dagg 70 + Hiscox 206)은
"표본 확인 후 나머지 일괄 승인" 방식으로 기록되어, F3 개별 Q1/Q2/Q3
검수 요건(ADR-030 Amendment A §3)을 충족하지 못함 — 사용자 확인
(2026-09-16).

- 원본 pool: `NAE/review/human/requests/batch_0033_requests.json` (449건:
  Dagg 70 + Hiscox 379)
- 이 pool 중 173건(Hiscox)은 batch_0035~0043 등 별도 파일로 정상
  개별 검수되어 문제 없음 — 이 폴더로 옮겨진 적 없음.
- 이 276건에 해당하는 TSU는 `NAE/corpus/tsu/{Dagg_Church_Order,
  Hiscox_Standard_Manual}/tsu.json`에서 `review_status: generated`로
  되돌려졌고, 이전 판정은 `review_metadata.superseded_review_metadata`에
  보존됨. 재검수 대기 상태.
- 이 파일들은 삭제하지 않고 감사 추적(audit trail) 목적으로만 보관.
