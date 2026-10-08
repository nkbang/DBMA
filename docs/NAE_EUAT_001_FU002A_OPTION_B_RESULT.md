# FU-002-A 결과 (선택지 B): Dagg·Hiscox 신규 572건 증분 인덱싱

실행일 2026-09-29. 근거: [FU-002-P 사전점검](NAE_EUAT_001_FU002P_PREFLIGHT_RESULT.md), [후속 Task Order](NAE_EUAT_001_FOLLOWUP_TASK_ORDERS.md) FU-002. 사용자 승인(2026-09-29): 선택지 B — 신규 572건만 적용(추가만), CHANGED 17건은 보류.

## 결론

- `nae_tsu_v1` **3,319 → 3,891** (Dagg 2,958 → 3,279, Hiscox 361 → 612). 임베딩 오류 0.
- **기존 3,319포인트는 (id, payload, vector) 해시 기준 전부 불변**(변경·누락 0).
- CHANGED 17건은 의도대로 미적용(기존 오염 claim 유지).
- 완료 조건 중 "3,891 / NEW 0"은 충족. "CHANGED 0"은 선택지 B에 따라 대상이 아니다(잔존 17).

## 1. 실행 내역

공식 경로 `NAE.pipeline.ingest.pipeline.apply()`를 그대로 사용했다. 저장소 코드·스크립트는 수정하지 않았다. `scripts/nae_incremental_ingest.py`에는 CHANGED 제외 옵션이 없어, 스크래치패드(저장소 밖)의 실행기가 verified 레코드에서 CHANGED 17건을 뺀 목록을 `apply()`에 전달했다. 실행기는 실행 전 `NEW == 계획 목록`, `CHANGED == 0`을 assert했다.

| 단계 | 결과 |
|---|---|
| 백업 | `incremental_state.json` 사본(해시 `00ba092a…`), 기존 3,319포인트 해시 스냅샷, NEW/CHANGED ID 목록 (세션 스크래치패드) |
| dry-run (제외 목록) | Dagg NEW 321 / CHANGED 0, Hiscox NEW 251 / CHANGED 0 |
| Dagg apply | 321건 색인, 임베딩 오류 0 → points 3,640 |
| 중간 검증 | 기존 3,319 변경 0, 추가 321건 전부 계획 대상 |
| Hiscox apply | 251건 색인, 임베딩 오류 0 → points 3,891 |
| 최종 검증 | 기존 3,319 변경 0, 추가 572건(Dagg 321 + Hiscox 251) 전부 계획 대상, 상태 파일 3,891 전부 INDEXED |

## 2. 검증

| 항목 | 결과 |
|---|---|
| 저자별 포인트 | Dagg 3,279 / Hiscox 612 / Fuller 0 |
| 전체 verified 대상 dry-run (CLI) | NEW 0, CHANGED Dagg 14 + Hiscox 3, UNCHANGED 3,265 / 609 |
| 단위 회귀 | `test_nae_incremental_ingestion` 25 + `test_nae_bridge_full_source_text`·`test_nae_index_indexer`·`test_nae_index_qdrant_store` 11 = 36 passed |
| 미실행 | `test_nae_retrieval_bridge_integration`(라이브 Qdrant 사용) |

## 3. 검색 효과 (EUAT 질문, 라이브 인덱스)

| 질문 | 변화 |
|---|---|
| EUAT-01 (권징) | 1위가 신규 Hiscox 문단(TSU-0003533, 0.617): "Offenses calling for discipline are usually considered as of two classes; private or personal, and public or general…". "Church Discipline" 분류 TSU 38 → 85건, 최고 순위 43위 → **1위** |
| EUAT-02 (Hiscox) | 1위가 신규 Hiscox 문단(TSU-0003594, 0.667): "All evangelical churches profess to take the Holy Scriptures as their only and sufficient guide in matters of religious faith and practice…". 상위 10건 중 신규 3건 |
| EUAT-04 (1689) | 변화 미미(상위 10건 중 신규 3건). 1689 본문은 여전히 인덱스에 없음 |
| EUAT-05 | 상위 10건 중 신규 1건 |

이는 검색 어댑터(`bridge_query_paragraphs`) 기준이다. **채팅 답변 경로는 여전히 내장 TSU를 사용하지 않는다(EUAT Issue 1, FU-001 대상)**. 이번 조치는 공개 패널의 근거 품질 개선이다.

## 4. 부수 변경 및 주의

- `NAE/pipeline/ingest/state/incremental_state.json`이 추적 파일이라 메인 체크아웃(`feat/peb-v0.1`)에서 수정 상태가 됐다(미커밋 파일 17 → 18). 이 브랜치에는 다른 진행 중 작업이 섞여 있어 **커밋하지 않았다**. 커밋 여부와 방식은 별도 결정이 필요하다.
- `NAE/corpus/embeddings` 캐시에 신규 임베딩이 추가됐다.
- 되돌리려면: 신규 572개 tsu_id의 포인트 삭제 + 상태 파일 복원(백업 보관).

## 5. 남은 결정·미해결

1. **ADR-030 기준선 표기**: ADR-030은 `nae_tsu_v1` = 3,319를 "CLEAN baseline (변경 금지)"으로 서술한다. 이번 조치로 라이브 값이 3,891이 되어 문서와 어긋난다. 기준선 갱신 기록(Amendment 또는 상태 기록)의 형식은 사용자 결정 사항이다.
2. **CHANGED 17건 보류**: 기준선 내 오염 claim이 그대로다. 처리하려면 위 1번 결정과 함께 정한다.
3. **승인 후 claim 수정 17건의 재승인 여부**: 미결정.
4. **이 조치에 대한 C1 독립 검증**: 미수행(사후 검증 1회 권장).
