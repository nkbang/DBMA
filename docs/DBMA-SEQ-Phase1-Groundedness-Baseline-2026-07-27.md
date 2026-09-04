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

## 확장 — SEQ004~007 사람 채점 대조 (2026-07-29)

`docs/GOLDEN-SET-SCORING-SHEET-gold4-7.md`에서 ADR-010(RAG)/ADR-012
(설교) 골든셋을 3→7건으로 동시 확장하며 SEQ004~007도 David가 직접
채점했다(`scripts/run_golden_set_expansion.py`로 judge 채점만 먼저
산출, human_groundedness는 별도 채점).

```
             judge  사람  일치
SEQ004 시편 23편 목자   4.0   3     △ (judge가 +1 관대)
SEQ005 엡2장 은혜 구원  5.0   5     완전 일치
SEQ006 갈5장 성령의열매 1.0   0     △ (judge가 +1 관대)
SEQ007 마5장 팔복       2.0   2     완전 일치
```

SEQ001~003(전부 5.0)과 달리 이번엔 **judge가 0~5 전 구간에서 실제로
갈라져서 채점** — "전부 만점"이었던 이전 우려(§한계)가 이번 확장으로
일부 해소됐다. 사람과의 편차는 최대 1점(judge가 항상 사람보다 높거나
같음, 낮은 적은 없음) — RAG 축(gold-4~7, `tests/fixtures/rag_eval_
golden_set.json`)은 4건 전부 완전 일치였던 것과 비교하면, 설교 축
judge가 RAG 축보다 살짝 더 관대한 경향이 이번에도 재확인됐다(§해석의
"judge가 관대한 성향" 가설과 일치).

SEQ006이 특히 근거 있다 — 검색된 청크 5개가 갈라디아서 5장과 완전히
무관(참고문헌 목록·6장 논쟁)함에도 judge는 "학자 이름이 언급되니 약한
연결"로 1.0을 줬는데, 사람은 "그 연결 자체가 억지"라며 0을 줬다 —
judge가 인용 형식(`[자료N]`)의 존재 자체를 근거로 오인하는 경향이
있을 수 있음을 시사한다.

## Next Steps (ADR-012 원문과 연결)

- [x] `sermon_judge.py`를 실제 경로로 처음 실행 — 죽은 코드 상태 해소
- [x] 골든셋 라벨링 담당·일정 결정 — David 직접 채점, 2026-07-29 SEQ004~007
      완료(위 "확장" 절 참고)
- [x] 판별력 확인 — SEQ004~007로 0~5 전 구간 판정 확인, "전부 만점"
      우려 해소. 잔여 이슈: judge가 사람보다 최대 1점 관대한 경향은
      여전히 남아있어 절대 점수 그대로 신뢰하기보다 상대 비교(델타
      측정) 용도로 우선 사용 권장.
- [ ] Few-shot 예시 뱅크 큐레이션 기준 정의(ADR-012 Next Steps §4)
