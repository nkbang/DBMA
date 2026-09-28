# WORK ORDER — Phase 11: Production Safety Audit

- 선행 게이트: P10 GREEN·HQ 승인
- 대상: C1
- 공통 규칙·STOP 조건: `docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md`
- 새 기능 없음 — 감사만

## 목표

HQ 원문 §12를 수치로 증명한다.

## 허용 파일

- 신규: `docs/grounded_synthesis/GS-P11-PRODUCTION-SAFETY-REPORT.md`
- 코드 변경 없음

## 절차 및 확인 방법

| 항목 | 확인 방법 |
|---|---|
| TSU mutation = 0 | `output/bench/tsu_dataset.jsonl`, `tsu_manifest.json`의 sha256을 `GS-SAFETY-BASELINE-CUE-20260927.json`과 재계산 비교 |
| Qdrant mutation = 0 | P9 실행 직전/직후 컬렉션별 `point_count`를 `curl localhost:6333/collections/<name>` 등으로 기록·비교 (P9 실행 중 Qdrant가 꺼져 있었으면 "해당 없음, 미실행"으로 명시) |
| Tantivy mutation = 0 | `output/bench/tantivy_index/`의 파일별 sha256 집계(GS-00 §2 스크립트와 동일 방식)를 baseline과 비교 |
| Corpus regeneration = 0 | `scripts/merge_nae_corpus.py`, `scripts/process_unprocessed_nae.py`(G0 staged, GS와 무관) 호출 이력이 GS 관련 스크립트/테스트 실행 로그에 없음을 확인 |
| Benchmark mutation = 0 | `output/bench/` 디렉터리에 P1~P10 어느 커밋에서도 새 파일이 추가되지 않았음(`git status`/파일 mtime 대조) |
| No new retrieval path | GS-00 §5 V3(R6 grep)의 P1~P10 누적 결과 재확인 |
| No hidden retrieval / external search | `core/grounded_*.py`, `core/evidence_*.py` 전체에서 `requests`, `httpx`, `urllib`, `socket` import 부재 확인 |
| No LLM retrieval | LLM(stub/ollama) 호출이 `Claim` 추출 단계(P5/P9)에만 있고, retrieval 단계(P1~P4)에는 없음을 grep으로 확인 |
| No corpus mutation | 위 TSU/Tantivy 확인과 동일 |

## Acceptance Criteria

- AC1: 표의 9개 항목 전부 "0" 또는 "해당 없음(사유 명시)"으로 채워짐 — 빈 칸 금지
- AC2: 각 항목마다 실행한 명령과 그 출력을 원문으로 첨부(요약·서술만으로는 불충분)
- AC3: 하나라도 mutation이 발견되면 즉시 STOP CONDITION TRIGGERED(#10~#13 중 해당)로
  전환하고 이 WO의 나머지 항목도 계속 확인해서 전체 영향 범위를 함께 보고

## 보고

`docs/grounded_synthesis/GS-P11-PRODUCTION-SAFETY-REPORT.md`. 마지막 줄 규칙은 P10과 동일.
