# C1 Night Shift Order 003 — Registration → TSU → Embedding → Qdrant 연결부

| | |
|---|---|
| Issued by | CUE, on Rev. Bang's approval (2026-08-15) |
| Mission | 등록된 10개 source 중 **아직 처리 안 된 것**에 대해 TSU→Embedding→Qdrant 실행 |
| Priority | P0 |
| Mode | Autonomous / No Questions / Night Shift 계속 |
| Continues | `C1-NIGHT-SHIFT-ORDER-002`(Registration 10건 완료, 커밋 `f57407d`) |

Order 002의 Registration 10건은 완료로 인정됐다. 이 미션은 **기존 컴포넌트를
확인하고 최대한 재사용**해서 TSU 연결부를 실행한다. **새 아키텍처/새 ADR을
임의로 만들지 마라.**

---

## 🛑 착수 전 필독 — CUE가 이미 확인한 사실 (재조사 금지, 그대로 받아써라)

**10건 중 2건(Dagg, Hiscox)은 이미 2026-08-09에 TSU 생성·embedding·Qdrant
indexing이 끝나 있다.** CUE가 직접 확인:

- `NAE/corpus/tsu/Dagg_Church_Order/tsu.json`(3,377 raw record), `index_report.json`
  (`generated_at: 2026-08-09`, `indexed: 5`) — 이미 존재
- `NAE/corpus/tsu/Hiscox_Standard_Manual/`도 동일(`indexed: 5`, 2026-08-09)
- **Qdrant 실측**: `nae_tsu_v1`에서 `source_id: BAP-CHURCH-DAGG-001`로 조회 →
  **실제 10 point 존재**, `work_id: WORK-DAGG-CHURCH-ORDER-001` 확인
- **중요한 불일치**: 어젯밤 Registration이 새로 계산한 `work_id`는
  `dagg_john_l-church_order`(소문자 snake_case)인데, 기존 Qdrant에 이미
  indexing된 레코드의 `work_id`는 `WORK-DAGG-CHURCH-ORDER-001`(대문자 형식)이다
  — **서로 다른 identity 스킴**이다.

**Fuller Vol01-08(8건)은 TSU가 없다** — `NAE/corpus/tsu/Fuller_Complete_Works_Vol01~08`
디렉터리 자체가 존재하지 않는다(CUE가 `find`로 확인). 이 8건이 실제로
"아직 처리 안 된" 대상이다. `NAE/corpus/canonical/Fuller_Complete_Works_Vol01~08/`에는
이미 `canonical.json`/`canonical.txt`가 존재한다(2026-08-07 생성, Dagg의 것과
동일한 구조) — 즉 추출은 이미 되어 있고 TSU 생성부터 시작하면 된다.

### 이것이 바꾸는 것

- **Phase 1~3의 파일럿 1건은 Dagg나 Hiscox가 아니라 `Fuller_Complete_Works_Vol01`로
  하라.** Dagg/Hiscox를 다시 처리하면 이미 존재하는 Qdrant 레코드와 identity
  스킴이 다른 **중복 임베딩**이 생긴다 — 사용자가 명시한 "중복 embedding 금지"
  위반이다.
- **Phase 4의 "10건 확대"는 실제로는 Fuller Vol01-08 8건이다.** Dagg/Hiscox는
  건드리지 마라 — identity 스킴 불일치는 이 미션의 범위가 아니다(별도 정리
  필요, 아래 §종료조건 참고).

---

## 기존 컴포넌트 확인 결과 (CUE가 코드로 확인 — 그대로 재사용해라)

```
NAE/pipeline/tsu/runner.py --identifier <id>
    → gate 우회, builder.build_tsu_for_identifier(identifier, ...) 직접 호출
    → NAE/corpus/canonical/<id>/canonical.json 을 입력으로 사용
    → NAE/corpus/tsu/<id>/tsu.json + tsu_report.json 생성

scripts/nae_incremental_ingest.py --identifier <id> --apply
    → NAE/pipeline/ingest/pipeline.py (ADR-020, Approved) 호출
    → embedding.py: content_hash 캐시로 SKIP/EMBED 판정 (중복 방지 내장)
    → indexing.py: Qdrant upsert-only, 기존 vector 보존
    → 기본값은 --dry-run, --apply를 줘야 실제 mutation
```

이 두 CLI는 **이미 완성되어 있다.** 새로 만들 코드는 없어야 한다 — 이 둘을
순서대로 호출하고 결과를 evidence로 남기는 것이 이번 미션의 전부다.

---

## Phase 1 — TSU 생성 (Fuller Vol01 1건)

```bash
python -m NAE.pipeline.tsu.runner --identifier Fuller_Complete_Works_Vol01
```

성공 조건: `NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu.json`이 실제
생성되고, record 안의 `source_id`가 registration에서 쓴
`BAP-MISS-FULLER-VOL01`과 일치하는지 확인(Dagg 사례처럼 canonical.json 안에
이미 source_id가 박혀있을 수 있다 — 확인만 해라, 다르면 STOP하고 보고).

## Phase 2 — Embedding/Indexing 연결 확인 (dry-run 먼저)

```bash
python scripts/nae_incremental_ingest.py --identifier Fuller_Complete_Works_Vol01
```

(기본이 `--dry-run`이다) `NEW/CHANGED/UNCHANGED/SKIP/EMBED/INDEX` 카운트를
evidence로 남긴다. Qdrant에 아직 이 identifier가 없다는 걸 dry-run 결과로
확인한 뒤에만 Phase 3로 간다.

## Phase 3 — 1건 E2E 실제 실행

```bash
python scripts/nae_incremental_ingest.py --identifier Fuller_Complete_Works_Vol01 --apply
```

성공 조건: Qdrant `nae_tsu_v1`에 `source_id: BAP-MISS-FULLER-VOL01`로 실제
point가 생겼는지 확인(스크립트 결과 서술이 아니라 Qdrant를 직접
`scroll`/`count`로 재확인). **실행 전후 총 points 수 변화를 정확히 기록해라**
(사용자 지시: "기존 3,319 baseline을 기준으로 mutation을 정확히 기록").

## Phase 4 — 나머지 확대 (Fuller Vol02-08, 7건만)

Phase 1-3가 GREEN이면 Vol02~Vol08을 순차로 Phase 1→2→3와 동일하게
반복한다. **Dagg, Hiscox는 포함하지 않는다.** 1건 실패해도 나머지는 계속
진행(서로 독립적인 원문).

---

## 필수 보호조건 (사용자 원문 그대로, 재확인)

```
✅ DBMA core/retrieval.py 변경 금지
✅ DBMA/NAE corpus isolation 유지
✅ 기존 Qdrant collection contract 준수 (nae_tsu_v1, upsert-only)
✅ 기존 3,319 baseline 기준으로 mutation 정확히 기록 (실행 전/후 points 수)
✅ 중복 embedding 금지 → 그래서 Dagg/Hiscox 제외, embedding.py의
   content_hash 캐시 SKIP 로직 신뢰
✅ idempotency 유지 (embedding.py/indexing.py가 이미 보장 — 재구현 금지)
✅ 실패 시 fail-closed
✅ 실제 실행하지 않은 결과를 PASS로 보고하지 말 것
```

## 절대 하지 말 것

```
❌ Dagg_Church_Order, Hiscox_Standard_Manual을 다시 TSU 생성/embedding 시도
❌ builder.py, embedding.py, indexing.py, pipeline.py(ingest/registration
   양쪽 다) 코드 수정 — 이미 완성된 컴포넌트, 호출만 해라
❌ resources/theological_sources/ 아래 어떤 파일도 건드리기
❌ Crosswalk Gate/Manifest 시스템을 우회하려고 새 코드 작성 — 이번엔
   --identifier override 경로(이미 존재)만 쓴다
```

## 종료 조건 / STOP 조건

- Phase 1에서 `canonical.json`의 `source_id`가 registration의 `source_id`와
  다르면 즉시 멈추고 evidence만 남겨라(identity 재조정은 별도 미션).
- Vol02-08 중 하나가 Dagg/Hiscox처럼 **이미 TSU가 존재하는 것으로 드러나면**
  그 건은 건너뛰고 계속(나머지는 진행), STOP.md에 기록.
- 8건이 모두 끝나면 미션 완료 — 억지로 다음 batch를 만들지 마라. Dagg/Hiscox의
  identity 스킴 불일치는 **이 미션에서 고치지 않는다** — 별도 보고만 남겨라.

## Evidence

`.automation/evidence/night-shift/tsu-processing-connection/`에 Phase별
디렉터리로 남긴다. Qdrant points 수는 매 Phase 전/후 CUE가 직접 재현할 수
있도록 실제 커맨드 결과(스크린샷 아님, 텍스트)로 남긴다.
