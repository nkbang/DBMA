# C1 보고 원문 — Phase 9 Report (r1, 2026-09-27)

> V0(보고 원문 보존). C1이 채팅으로 반환한 보고를 그대로 옮긴 것.

---

모든 작업 완료. 요약 보고한다.

---

## GS-P09 WORK ORDER — 완료 요약

### 생성된 파일 (3건, WO 허용 범위 내)

| 파일 | 용도 | 크기 |
|---|---|---|
| `tests/test_grounded_synthesis_integration.py` | stub LLM 결정적 통합 테스트 | 13,673 바이트 |
| `scripts/grounded_synthesis_integration_demo.py` | 실제 Ollama 모델 참조 구현 데모 | 10,245 바이트 |
| `docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md` | 실모델 실행 결과 기록 (3건) | 5,919 바이트 |

### 테스트 결과

- **P9 통합 테스트**: 7/7 PASS (stub LLM, grounded + insufficient_evidence 양쪽 경로)
- **P8 회귀 검증**: 18/18 PASS (기존 테스트 영향 없음)
- **core/retrieval.py / core/hybrid_candidate_pipeline.py**: diff 없음 (무수정 확인)

### 실모델 데모 결과 (3건)

| # | 유형 | 질의 | GroundedAnswer.status | 비고 |
|---|---|---|---|---|
| 1 | G2 (근거 부족) | "존 스미스 3세" 교회론 | `insufficient_evidence` / `no_valid_claim` | LLM이 조작된 인물 인식 → "근거 자료 없음" |
| 2 | A1 (본문주해) | 로마서 8:1-4 정죄 없음 | `insufficient_evidence` / `no_valid_claim` | retrieval 5건 반환 but claim extraction에서 evidence_ids 매칭 실패 |
| 3 | B1 (교리) | 신자 침례 근거 | `insufficient_evidence` / `no_valid_claim` | 동일 — 코퍼스 한계 + LLM 파서 한계 |

### 안전 기준선

```
tsu_dataset.jsonl:  0881618d...9c56  (전후 일치)
tsu_manifest.json:  67159d21...665e  (전후 일치)
```

**STOP 조건 트리거 아님.**

### G0 staged 변경 6건

열람만 하고 건드리지 않음. untouched 확인.

---

이 변경은 커밋하지 않았다. CUE의 읽기 전용 재검증 승인이 필요하면 `git commit -m "GS-P09: Integration test + demo script + real-model results" -- tests/test_grounded_synthesis_integration.py scripts/grounded_synthesis_integration_demo.py docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md` 로 커밋할 수 있다.

CUE READ-ONLY REVALIDATION REQUESTED
