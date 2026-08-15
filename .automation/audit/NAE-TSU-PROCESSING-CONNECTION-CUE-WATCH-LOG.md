# CUE Watch Log — NAE TSU Processing Connection (Night Shift Order 003)

CUE는 C1(Cline)을 프로그래밍적으로 트리거하거나 상태를 실시간으로 읽을 수
없다. 이 로그는 CUE가 filesystem/git/Qdrant를 직접 재실행/재조회해 검증한
기록이다. C1의 서술만으로 PASS를 인정하지 않는다.

## 2026-08-15 07:58 UTC — kickoff, 착수 전 조사 결과

Order 발행 전 CUE가 직접 확인한 사실(재조사 불필요, Order 003에 그대로 반영됨):

- `NAE/pipeline/tsu/runner.py --identifier <id>`: 기존 override 경로, Gate
  우회, `builder.build_tsu_for_identifier()` 직접 호출. 신규 코드 아님.
- `scripts/nae_incremental_ingest.py --identifier <id> [--apply]`: ADR-020
  Approved 구현. 기본 dry-run, embedding.py의 content_hash 캐시가 중복 방지
  내장.
- **Dagg/Hiscox는 이미 2026-08-09 TSU+embedding+Qdrant indexing 완료**:
  - `NAE/corpus/tsu/Dagg_Church_Order/index_report.json`:
    `generated_at: 2026-08-09T18:32:43Z, indexed: 5`
  - Qdrant 실측(`scroll` + filter `source_id=BAP-CHURCH-DAGG-001`): **10
    point 존재**, `work_id: WORK-DAGG-CHURCH-ORDER-001`
  - 어젯밤 Registration이 계산한 신규 `work_id`: `dagg_john_l-church_order`
    — **identity 스킴 불일치 확인**
  - Hiscox도 동일 패턴(`index_report.json`, `indexed: 5`, 2026-08-09)
- **Fuller Vol01-08은 TSU 미존재**(`find`로 확인, 디렉터리 자체가 없음).
  `NAE/corpus/canonical/Fuller_Complete_Works_Vol01~08/`에는 이미
  canonical.json/txt 존재(2026-08-07 생성) — 추출은 끝나 있음.
- Qdrant baseline(재확인): `nae_tsu_v1` = 3,319 points.

Order 003을 이 사실에 맞춰 재구성: 파일럿을 Dagg(사용자 원 지시 예시와 다름)
대신 **Fuller_Complete_Works_Vol01**로 지정, Dagg/Hiscox는 이번 미션에서
제외(identity 불일치는 별도 정리 필요 — 이 미션 범위 아님). 릴레이 7로 전달.

Baseline:
- `.automation/evidence/night-shift/tsu-processing-connection/` — 미생성
- `NAE/corpus/tsu/Fuller_Complete_Works_Vol01~08/` — 전부 미존재
- Qdrant `nae_tsu_v1` — 3,319 points
- `git diff core/retrieval.py NAE/pipeline/tsu/*.py NAE/pipeline/ingest/*.py` — 비어 있음

이후 각 check-in은 이 파일 하단에 append.
