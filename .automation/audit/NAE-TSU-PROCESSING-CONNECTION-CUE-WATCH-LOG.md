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

## 2026-08-15 15:42 UTC(추정, 세션 재개 후) — C1 보고 독립 검증 + 중대 구조적 발견

### C1 보고 검증

PID 88689가 C1이 launchd로 띄운 프로세스임을 확인(C1 보고서와 대조 일치).
`tsu_report.json` 재조회 결과 CUE가 아까 직접 읽었던 값과 일치(300/5,452,
claims 207, elapsed 3248.91s) — 서로 다른 체크포인트 시점(C1은 100건째,
CUE는 300건째) 관측이라 속도 차이(12.65s vs 10.83s/candidate)는 정상 변동,
불일치 아님. Evidence 파일(`MISSION-003-STATUS.md`,
`phase-1-tsu-generation/README.md`) 실재 확인.

**실측 기반 전체 완료 예상**: 볼륨당 16~21시간, 8볼륨 전부면 130~170시간+.

### 🔴 구조적 발견 — Phase 2/3는 TSU 생성이 끝나도 자동으로 진행되지 않는다

`scripts/nae_incremental_ingest.py:33`:
```python
return [r for r in data if r.get("review_status") == "verified"]
```

`NAE/pipeline/tsu/review_promotion.py` 모듈 docstring이 명시: `review_status
== "verified"`는 **"사람이 신학적 검토를 완료했다"**는 뜻이며, 이 모듈은
"the only path by which a TSU record's review_status may become verified"다.
새로 생성되는 TSU는 전부 `review_status: "generated"`로 시작한다(builder.py
자체 docstring).

즉 Phase 1이 20시간 뒤 완료돼도, Phase 2(embedding dry-run)는 **검토·승격된
레코드가 0건이라 아무것도 하지 않을 것**이다. Dagg/Hiscox의 기존
`index_report.json`이 `records_total_raw: 3377/740` 중 `gate_pass: 5,
indexed: 5`였던 이유가 바로 이것 — 원래도 사람이 수천 개 후보 중 5개만
검토·승격한 결과였다.

**결론**: 이건 버그나 설계 공백이 아니라 **의도된 human-in-the-loop 품질
게이트**다. C1/CUE가 임의로 우회·자동화하면 안 된다(Order 003의 "새 아키텍처
임의 구현 금지"와 review_promotion.py의 설계 의도 둘 다 위반). Phase 1
완료 후 Phase 2로 넘어가려면 **사람의 검토·승격 결정이 별도로 필요**하다는
사실을 Rev. Bang에게 미리 보고함.

Rev. Bang 결정: 현재 프로세스(PID 88689) 그대로 계속 진행. Phase 1 완료 후
review/promotion 필요성은 그때 다시 보고.

## 2026-08-15 16:05 CDT — CUE Directive 채택: NAE TSU Extraction Continuation

Rev. Bang 지시로 아래를 운영 원칙으로 고정한다(요약, 전문은 대화 기록 참고):

- Vol01 production run(PID 88689, `llama-server --parallel 1`) 무변경 유지.
  Ollama 재시작·모델 unload/load·`OLLAMA_NUM_PARALLEL` 변경·프로세스 중단
  전부 금지.
- C1에게 새 성능 실험 하달 안 함(병렬화 실험 취소).
- CUE는 1시간 간격으로 다음만 확인: processed/total, throughput,
  process alive, error/failure count, evidence/state integrity. 정상이면
  개입하지 않는다.
- 개입 조건(이것만): 프로세스 종료, 반복 오류, state/evidence corruption,
  데이터 손상 가능성, production boundary violation. 단일 candidate 실패는
  개입 사유 아님. **"느리다"는 이유만으로 중단·재설계 금지.**
- Vol01 완료 시 CUE가 즉시 확인: candidate count, TSU output count,
  실패/누락 count, evidence completeness, quality gate 결과, git diff.
  그 후 Vol02가 자동 큐(`run_tsu_queue.sh`)에서 이어서 시작 — Rev. Bang
  승인 대기 없이 진행.
- 모델 최적화 검토는 볼륨 간 경계(Vol01→Vol02 등)에서만, 별도 소규모
  benchmark로. Vol01을 위해 지금 재시작하지 않는다.
- 운영 원칙: "정상적으로 느리게 진행되는 작업은 방해하지 않는다." 현재
  0/400 failure, throughput 실측 진행 중 — 이 상태로는 무개입.
- 아침까지 Rev. Bang 추가 입력 대기 없이: C1 생산 계속, CUE 감시·장애
  대응·다음 batch 완료 감사만 수행.

이 시점부터 위 원칙이 기본 운영 모드다. 이후 이탈 시에만 이 로그에 기록.
