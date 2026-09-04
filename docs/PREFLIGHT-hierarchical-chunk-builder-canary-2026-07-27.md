# Canary — Hierarchical Chunk Builder 프로덕션 전환 실측 (2026-07-27)

상태: **실측 완료, 전환 보류 확정**. ADR-008의 D-5 게이트(§1~§5)는
2026-07-22 시점 Beta corpus 집계로 이미 통과 판정을 받았으나, "게이트
통과 = 실행 승인 아님"(ADR-007 원칙) 원칙에 따라 실제 전환 전
canary(개별 문서 단위 재검증)를 별도로 실행했다.

## 방법

`scripts/shadow_d5_metrics.py::analyze_document()`(기존 진단 스크립트,
신규 로직 없음)로 `output/beta_validation_v5/` 문서 중 작은 것부터
순차 샘플링 — Ollama 임베딩 호출(`EmbeddingSimilarityBoundaryFeature`)
비용 때문에 corpus 전체가 아니라 표본으로 진행
([[feedback_verification_cost_discipline]] 원칙).

Profile A 2건, Profile B 3건 측정. Profile B가 핵심 관심 대상인
이유: ADR-008 §1에서 Profile B의 Axis 2(Semantic Flush Ratio)만
"프로덕션 전환 불충분" 판정을 받았던 이력이 있음(당시 16.4%→개선
후 33.7%, corpus 집계 기준).

## 결과

| 문서 | Profile | Axis 1 (Recovery, ≥95%) | Axis 2 (Semantic Flush, B는 ≥25%) | Axis 3 (Outlier, A:0%/B:≤10%) |
|---|---|---|---|---|
| 12. 고린도후서 | A | 97.7% ✅ | 32.8% (기준 없음) | 0.0% ✅ |
| 5. 요한복음1 | A | 96.2% ✅ | 22.7% (기준 없음) | 0.0% ✅ |
| 2 Kings: The Power and the Fury | B | 100.0% ✅ | **23.0% ❌** | 0.0% ✅ |
| 2 Kings: The Anchor Bible Commentary | B | 96.2% ✅ | **23.5% ❌** | 0.0% ✅ |
| 2 Chronicles, Vol. 15 (WBC) | B | 100.0% ✅ | 25.3% ✅(턱걸이) | 0.0% ✅ |
| **Profile B 평균** | | **98.7%** | **23.9% ❌** | **0.0%** |

## 판정

**§5 롤백 트리거 발동**: `Axis 2(Profile B) < 25%` — 평균 23.9%,
3건 중 2건 개별적으로도 미달. Axis 1/Axis 3는 Profile A/B 모두
안전하게 통과 — 문제는 Axis 2(의미 기반 플러시 비율)로 국한된다.

Profile A는 이 결정 범위 밖(ADR-008 §5: "Profile A의 Axis 2는
§1과 동일하게 유지, 롤백 트리거에서 제외")이라 참고용으로만
기록했고 판정에는 영향 없음.

## 결정: 프로덕션 전환 보류

3개 표본(corpus 전체 대비 소규모)이지만 방향이 일관돼(2/3 개별
실패, 평균도 미달) 우연으로 보기 어렵다. 2026-07-22 이후 "HQ 승인
대기"로 미결정 상태였던 항목을 이번 실측으로 **"전환 보류"로 확정**
한다 — `core/hierarchical_chunk_builder.py`는 계속 dormant 상태
유지, `core/processing.py`는 `core/chunking_optimizer.py`
(`optimize_chunks`)를 그대로 사용한다.

## Next Steps

- [x] Profile A/B 표본 실측
- [x] 롤백 트리거 기준 판정
- [x] 전환 보류 확정, STATE.md 갱신
- [ ] (후속, 낮은 우선순위) Profile B의 Axis 2가 왜 25% 근처에서
      불안정한지 원인 조사 — 개선되면 재평가 가능
- [ ] (후속) corpus 전체 재측정으로 표본 크기 확대(비용 크므로 필요성
      재확인 후 진행)
