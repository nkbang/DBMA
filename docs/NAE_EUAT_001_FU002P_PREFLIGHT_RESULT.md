# FU-002-P 사전점검 결과

기준일 2026-09-29. 근거: [NAE_EUAT_001_FOLLOWUP_TASK_ORDERS.md](NAE_EUAT_001_FOLLOWUP_TASK_ORDERS.md) FU-002-P. 점검은 읽기 전용이었다. 상태 파일 해시·포인트 수·저장소는 점검 전후 동일하다.

## 결론

기술적 위험은 낮다. 다만 **Approved ADR-030이 `nae_tsu_v1` = 3,319를 "CLEAN baseline (변경 금지)"으로 명시**하여, 기준선 내부 포인트를 수정하는 CHANGED 17건 재임베딩은 충돌 소지가 있었다. 사용자 결정(2026-09-29): **선택지 B — 신규 572건만 적용(추가만), CHANGED 17건은 보류.**

## 1. 보호 파일 점검: 통과

- 메인 체크아웃(`feat/peb-v0.1` @ `c2cdf147`)의 미커밋 17개에 보호 파일(`embed/client.py`, `tsu/builder.py`, `tsu/runner.py`)은 없다. `NAE/` 추적 파일은 HEAD와 동일하다.
- 인제스트 경로(`ingest`, `embed`, `index`, `scripts/nae_incremental_ingest.py`)는 `core.*`와 `config.yaml`을 import하지 않는다.
- 주의: `config.yaml`의 `nae_pd.enabled`는 HEAD가 `false`, 작업 트리(스테이징)가 `true`다. 실행 중인 앱은 이 미커밋 값에 의존한다. 스테이징된 `scripts/merge_nae_corpus.py`, `process_unprocessed_nae.py`, `test_default_corpus_query.py`는 인제스트 경로 밖이며 읽거나 실행하지 않았다.

## 2. 재현성 점검: 통과

| 항목 | 결과 |
|---|---|
| dry-run 재실행 | Dagg NEW 321 / CHANGED 14, Hiscox NEW 251 / CHANGED 3 (이전과 동일) |
| `incremental_state.json` 해시 | 전후 동일 (`00ba092a75c77b2b76dd21f8b3b94e46`) |
| Qdrant `nae_tsu_v1` | 3,319, green |
| `tests/test_nae_incremental_ingestion.py` | 25 passed (tmp 경로 + 가짜 클라이언트) |
| 중복·빈 claim | 0건 |
| 디스크 | 2.0 TB 여유, 임베딩 캐시 1.2 GB |

- 임베딩 실패는 치명적이지 않다: `embed_text`가 `None`을 반환하고 해당 레코드만 `EMBEDDING_FAILED`로 기록된다. 임베딩 자체에는 3초 제한이 없다.

## 3. ADR-030 충돌 검토

- ADR-030 헤더 "CLEAN baseline (변경 금지): `nae_tsu_v1` = 3,319", §8 원칙 3 "CLEAN 영역 동결", §14 Production Safety.
- FU-002-A 전체 적용(선택지 A)은 기준선 안의 17포인트를 수정하므로 "변경 금지"에 직접 해당한다.
- 반대 근거: ADR §6.2의 임베딩 게이트는 `review_status == verified`이고, 신규 572건은 이미 admission된 소스 내 verified 레코드이며 9/15~9/16 승인은 인간 리뷰(reviewer: David) 기록이 있다. 채택 문구도 "이 ADR을 이유로 재처리하지 않는다"로 되어 있어 사후 추가의 금지 여부가 모호하다.

| 선택 | 내용 | 결과 |
|---|---|---|
| A | 572건 + CHANGED 17건 적용, ADR-030 Amendment로 기준선 정정 | 미채택 |
| **B** | **신규 572건만 적용(추가만), CHANGED 17건 보류** | **채택** |
| C | 전체 보류 | 미채택 |

## 4. 후속 판단이 남은 항목

- CHANGED 17건(기준선 내 오염 claim)은 보류 상태다. 처리하려면 ADR-030 Amendment 또는 기준선 갱신 결정이 필요하다.
- 승인 후 claim 수정 17건의 재승인 여부(교정은 원문 `source_text`와 대조했다고 기록되어 있으나 수정자는 미기록).
- 기준선 문서화: 신규 572건 적용 후 `nae_tsu_v1`은 3,891이 되어 ADR-030의 "3,319" 서술과 달라진다. 정정 기록 방식은 사용자 결정 사항이다.

## 5. 실행 계획 (선택지 B)

1. 백업: `incremental_state.json` 사본, 기존 3,319포인트의 (id, payload, vector) 해시 스냅샷, 신규 대상 572 tsu_id 목록(롤백 기준).
2. 공식 경로 `NAE.pipeline.ingest.pipeline.apply()`에 **CHANGED 17건을 제외한** verified 레코드를 전달한다(스크립트·코드는 수정하지 않음).
3. Dagg → Hiscox 순으로 실행하고 각 단계 후 검증(포인트 수, 기존 3,319 불변, 상태 파일).
4. 롤백: 신규 tsu_id에 해당하는 포인트 삭제 + 상태 파일 복원.
