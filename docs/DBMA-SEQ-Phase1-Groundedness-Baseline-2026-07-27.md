# DBMA-SEQ Phase 1 — 설교 개요 Groundedness 베이스라인 (2026-07-27)

상태: **첫 실측 완료**. `core/evaluation/sermon_judge.py`(2026-07-24
커밋 `4f4363d`로 구현·테스트 완료)가 구현 이후 한 번도 실제 호출된
적 없이 mock 테스트만 통과한 상태였음을 발견 — `scripts/
run_sermon_eval.py`를 신설해 실제 프로덕션 경로(`ui/pages/
sermon_draft.py`와 동일한 `QueryProcessor.process()` →
`SermonDraftService.generate_outline()` → `judge_sermon_groundedness()`)
로 처음 실행했다.

## 방법

`docs/architecture/ADR-010-DBMA-REQ-RAG-Evaluation-Quality.md`
§Decision-미확정-1에서 실제로 채점에 쓰였던 본문/주제 3건(요한복음
15장 포도나무 비유 / 로마서 8장 성령 안에서의 삶 / 히브리서
대제사장이신 그리스도)을 그대로 재사용 — 새 예시를 지어내지 않음.
k=20(`ui/pages/sermon_draft.py`의 `_CANDIDATE_K`와 동일).

## 결과

```
SEQ001 요한복음 15장 포도나무 비유    — groundedness 5.0/5
SEQ002 로마서 8장 성령 안에서의 삶    — groundedness 5.0/5
SEQ003 히브리서 대제사장이신 그리스도 — groundedness 5.0/5
평균: 5.00/5
```

첫 실행(`baseline_001`)에서 SEQ001 판정 도중 judge 모델
(`dbma-planner-r1-q6:70b`, 42GB)이 `timed out waiting for
llama-server to start`로 실패해 groundedness=0.0(품질 문제 아닌
인프라 이슈)이 섞였다 — 재실행(`baseline_002`)에서는 3건 전부
정상 완료.

## 해석

RAG 채팅 답변(`docs/PREFLIGHT-tsu-verse-mapping-book-chapter-
mismatch.md`의 원인이 됐던 groundedness=0.0 사례)과 정반대 결과다.
`SermonDraftService.generate_outline()`의 프롬프트가 `[자료N]`
인용 형식을 명시적으로 강제하는 구조라, 실제 생성 텍스트에도
`[자료1]`, `[자료2]` 등 인용이 일관되게 나타났고 judge가 이를
근거 충족으로 판정했다.

**한계**: 3건 전부 만점이라 판별력이 낮다 — judge가 관대한 성향인지
(ADR-010 §Decision-미확정-1에서 이미 확인된 RAG judge의 관대함 —
평균 절대 오차 0.83/5, gold-1 사례 +1.6 편차), 실제로 설교 개요
생성 품질이 그만큼 좋은지 골든셋(사람 채점) 대조 없이는 판단할 수
없다.

## Next Steps (ADR-012 원문과 연결)

- [x] `sermon_judge.py`를 실제 경로로 처음 실행 — 죽은 코드 상태 해소
- [ ] 골든셋 라벨링 담당·일정 결정(ADR-012 Next Steps §2, ADR-010
      §1과 동일 절차 — 아직 미결정)
- [ ] Few-shot 예시 뱅크 큐레이션 기준 정의(ADR-012 Next Steps §4)
- [ ] 판별력 확인을 위해 의도적으로 품질 낮은 케이스(예: 무관한
      본문/주제)도 표본에 포함해 재측정 — 전부 만점만 나오면 judge
      민감도 자체를 의심해야 함
