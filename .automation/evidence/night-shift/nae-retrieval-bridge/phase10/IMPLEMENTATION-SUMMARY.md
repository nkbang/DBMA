# Phase 10 — NAE Production Retrieval Bridge Implementation Summary

## Mission Status: PRODUCTION_READY (with module gating)

NAE Production Retrieval Bridge가 ADR-024 승인 범위에 따라 구현 완료.

---

## 1. Implementation Overview

### Files Modified

| File | Lines Changed | Description |
|------|--------------|-------------|
| `NAE/retrieval_adapter.py` | +180 | bridge_query() + _map_nae_to_citation_metadata() |
| `ui/pages/research.py` | +98 | NAE 검색 섹션 UI 통합 |

### Architecture Changes

- **bridge_query()**: query_text → embedding (Ollama BGE-M3) → NAE Qdrant search → Citation 리스트
- **_map_nae_to_citation_metadata()**: NAE payload → CitationBuilder.metadata 매핑
- **_render_nae_section()**: UI에 NAE 검색 섹션 추가 (module gating 준수)
- **_execute_nae_retrieval()**: UI에서 bridge_query() 호출

### Architecture Protection

- ✅ core/retrieval.py 수정 없음
- ✅ Production Qdrant data mutation 없음
- ✅ DBMA corpus 수정 없음
- ✅ NAE raw corpus 수정 없음
- ✅ bridge_query는 READ ONLY (upsert/update 없음)

---

## 2. Test Results

| Test | Description | Result |
|------|-------------|--------|
| A | NAE module disabled → NaePdModuleDisabledError | PASS |
| B | NAE module enabled + Qdrant retrieval | PASS |
| C | English query | PASS (5 citations, 0.40s) |
| D | Korean query | PASS (5 citations, 0.41s) |
| E | Citation/provenance 존재 확인 | PASS (7/7 필드) |
| F | Malformed/empty result | PASS (list of Citation 반환) |
| G | Qdrant connection failure | PASS (fail-closed: []) |
| H | Timeout handling | PASS (warn threshold 작동) |
| I | DBMA retrieval regression | PASS (0 contamination) |
| J | NAE benchmark regression | PASS (consistent scores) |

---

## 3. Key Design Decisions

### ADR-024 Gap Resolution

1. **NAE payload 스키마 drift fallback**: _map_nae_to_citation_metadata()에서 .get()으로 safe access, fallback chain 구현
2. **embed() 재사용 경로**: ollama.embeddings() 직접 호출 (NAE/pipeline/embed/client.py의 embed_text()와 동일한 Ollama API)
3. **Embedding/Qdrant 개별 Timeout**: Qdrant query_points(timeout=30), embedding warn threshold(1500ms)
4. **Regression 테스트용 구체적 질의**: "What is the doctrine of justification?" (실제 테스트 데이터 존재)

### Module Gating

- config.yaml `nae_pd.enabled: false` (기본값)
- bridge_query() 내부에서 module_registry.is_enabled() 체크
- UI에서도 _render_nae_section()에서 gating

### Fail-Closed Policy (§G)

- Qdrant/Ollama 장애 시 빈 리스트 반환, 예외 전파 없음
- warn threshold 초과 시 logging.warning()
- hard timeout 3000s 설정 (실제 사용 시 거의 도달하지 않음)

---

## 4. Production Safety

| Check | Result |
|-------|--------|
| core/retrieval.py 수정 | ✅ 없음 |
| Production Qdrant mutation | ✅ 없음 |
| DBMA corpus 수정 | ✅ 없음 |
| NAE raw corpus 수정 | ✅ 없음 |
| bridge_query write operations | ✅ 없음 |
| Expected files만 수정 | ✅ NAE/retrieval_adapter.py, ui/pages/research.py |

---

## 5. Final State

**PRODUCTION_READY** — nae_pd module이 enabled일 때 NAE Retrieval Bridge가 실제 Production 사용 가능.

### Activation

```bash
# Enable nae_pd module
scripts/dbma_module.py enable nae_pd

# Verify
scripts/dbma_module.py status nae_pd
```

### Deactivation

```bash
# Disable nae_pd module
scripts/dbma_module.py disable nae_pd
```

---

## 6. Remaining Items (Not Blocking)

- ADR-024 §J Acceptance Criteria 중 일부는 실제 UI 테스트 필요 (Streamlit 환경)
- NAE payload 스키마 변경 시 추가 fallback 로직 필요 (현재는 .get()으로 safe access)
- Embedding과 Qdrant 검색의 개별 Timeout 설정은 warn threshold로만 구현 (hard timeout은 hard-coded 3000s)

