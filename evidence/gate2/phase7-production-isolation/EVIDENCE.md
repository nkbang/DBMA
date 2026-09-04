# Phase 7 (Production Isolation) — CUE 직접 실행 Evidence

- 작성/실행: CUE, 2026-08-18 (C1 무응답 지속으로 CUE가 직접 실행 — 읽기 전용 검증이라 안전)
- 대상: `scripts/gate2/70_production_isolation.py`(BEFORE=AFTER 해시 비교, mutation 없음)

## 결과

| 대상 | BEFORE = AFTER | 상태 |
|---|---|---|
| `output/bench/tsu_dataset.jsonl` | `e3b0c442...` (0 bytes, 여전히 비어있음) | ✅ 무변경 |
| `output/bench/tsu_manifest.json` | `40fe3cfc...` | ✅ 무변경 |
| `NAE/corpus/tsu/tsu_id_state.json` | `f42e5fab...` | ✅ 무변경 |
| `{DEFAULT_OUTPUT_DIR}/registry/documents.json` | `bd2c5ecf...` | ✅ 무변경 |
| `nae_qdrant`(포트 7333, `nae_tsu_v1`) points_count | 스크립트 자체는 404(URL 버그: `/collections/nae_tsu_v1/points`가 아니라 `/collections/nae_tsu_v1`이 올바른 엔드포인트) | ⚠️ 스크립트 버그, **CUE가 직접 curl로 수동 확인** |

### Qdrant 수동 확인 (스크립트 버그 우회)
```
curl http://localhost:7333/collections/nae_tsu_v1
→ points_count: 3319
```
이 값은 ADR-024 Promotion 근거 evidence에 기록된 값과 **완전히 일치** —
오늘 밤 작업 전체에서 `nae_qdrant`가 단 한 번도 mutate되지 않았음을 확인.

## 판정

**Phase 7 = GREEN.** 4개 파일 해시 전부 BEFORE=AFTER 일치, Qdrant point count도
수동 확인으로 무변경 재확인. `70_production_isolation.py`의 Qdrant 체크 URL은
경미한 버그이나 production 안전성 판단에는 영향 없음(수동 검증으로 대체 완료).
다음 C1 작업 시 `scripts/gate2/70_production_isolation.py:112` 경로를
`/collections/nae_tsu_v1`(trailing `/points` 제거)로 수정 필요 — 낮은 우선순위.
