# FU-006 결과: 미시험·미확인 항목 마감

기준일 2026-09-29. 근거: [NAE_EUAT_001_FOLLOWUP_TASK_ORDERS.md](NAE_EUAT_001_FOLLOWUP_TASK_ORDERS.md) FU-006. 조사는 읽기 전용이었다(앱 UI 시험 1회 포함, 코드·데이터·Qdrant 변경 없음).

## 요약

| 항목 | 결과 |
|---|---|
| "연구" 탭 AI 답변 | 채팅과 동일 경로·동일 결과 (EUAT-01 UI 시험) |
| CHANGED 17건 교정 시점·주체 | 2026-09-15 04:38~04:49Z, `cjk_reextract` v1.0.0 + 수작업 패스 |
| 생성 지연(90초~8분) 원인 | 두 대형 모델 상호 evict 경합 (FU-005) |
| 공개 패널 권징 근거 순위 | 순수 벡터 순위 문제, 버그 아님 |
| **정정** | TSU-0002210 "헬라어 삭제" 우려는 원문 대조로 해소 |

## 1. "연구" 탭 AI 답변

**EVIDENCE (코드)**: `ui/pages/research.py:690`은 `processor.process(query, query_id="research-ui", k=top_k)`를 호출하고 답변은 `generate_answer`를 쓴다. 채팅(`chat.py:525`)과 같은 `QueryProcessor`이고, `research.py:560`은 같은 공개 패널(`render_nae_public_section`)을 표시한다.

**EVIDENCE (UI 시험, EUAT-01)**: 답변 "이 질문은 현재 등록된 자료로는 답할 수 없습니다." 참고한 자료 10건은 Broadus, Spurgeon Vol30·Vol15, Keach 등 내 서재 자료이며 Dagg는 없다. 상위 4건의 순서와 출처가 채팅 결과와 같다.

**IMPACT**: EUAT Issue 1(TSU에 닿지 않음)은 채팅 탭만의 문제가 아니라 두 탭 공통이다.
**한계**: 연구 탭에서는 EUAT-01만 시험했다. EUAT-02~05는 코드 동일성에 근거해 같다고 판단했으며 실측하지 않았다.

## 2. CHANGED 17건 교정 시점·주체

**EVIDENCE**
- `NAE/corpus/tsu/Dagg_Church_Order/cjk_reextract_report.json`: `cjk_reextract_version 1.0.0`, `model my-theology-bot-v2:latest`, 2026-09-15T04:43Z, 후보 17건, 자동 수리 0, 잔존 16, 실패 1.
- `Hiscox_Standard_Manual` 동일 보고서: 04:38Z, 후보 3건, 자동 수리 0, 잔존 3. (후보 수 17건 + 3건은 CHANGED 17건과 일치하는 규모.)
- 두 보고서의 `manual_repair_pass`(04:49Z): "각 레코드를 `source_text`와 대조해 손으로 교정", 수작업 교정 Dagg 51건, Hiscox 18건. 실행자는 기록되어 있지 않다.
- 보고서 문구: 자동 라운드가 CJK 정규식 밖의 오염(키릴·베트남어·힌디·아랍·태국·가나)에서 정체되어 수작업으로 넘어감. 원문에 이미 있던 헬라어 음역 OCR 오류 8건은 손대지 않음.
- 도구 커밋: `a908f533`(2026-09-09, "F2 TSU claim CJK contamination — sandbox test + repair tooling"). 9/26의 v1.1.0 커밋(`83fb767b`)은 Fuller용이며 이 교정과 무관하다.

**정정**: 부록 A 이전 판에서 후보로 든 "9/26 v1.1.0 커밋"은 틀렸다. 교정은 9/15에 이뤄졌다.

## 3. TSU-0002210 헬라어 우려 해소 (정정)

- 부록 A 이전 판: "Ευχαριστία(Eucharist)" → "Eucharist"가 정상 헬라어 삭제로 보인다고 기록.
- 원문 대조: `source_text`는 "The name Eucharist is often given to it, derived from the Greek word evzaptorew…". 헬라어 문자가 없고 OCR 깨짐 표기만 있다. 삭제된 "Ευχαριστία"는 모델이 claim 생성 중 도입한 표기다.
- 결론: 원문 헬라어 손실 없음. 승인 후 claim 수정 17건의 재승인 정책만 남는다. 이에 따라 FU-002-P의 "헬라어 확인" 항목을 삭제했다.

## 4. 생성 지연 원인

FU-005 결과 참조([FU-005 결과](NAE_EUAT_001_FU005_COLD_SEARCH_FAILURE_RESULT.md)). 같은 Ollama에서 `my-theology-bot-v2`(예상 49.6 GiB)와 Cline 모델(예상 20.6 GiB, ctx 131,072)이 서로를 3~4분 주기로 evict했고(오늘 18건), `KEEP_ALIVE=5m`, `NUM_PARALLEL=1` 설정이다. 지연 측정은 동시 사용 경합에 오염됐다.

## 5. 공개 패널 권징 근거 순위 (분석만, 변경 없음)

**OBSERVED**: 권징을 직접 다룬 Dagg p.95·p.103이 EUAT-01 공개 패널 상위 10건에 없다.

**EVIDENCE**: 같은 질의 벡터로 인덱스 3,319건 전체를 순위화(읽기 전용).

| 대상 | 순위 | 점수 |
|---|---|---|
| Dagg p.95 ("…organization and discipline of churches…") | 28위 | 0.5149 |
| Dagg p.103 ("…regulate its organization and discipline…") | 170위 | 0.4596 |
| 상위 10위 컷 | 10위 | 0.5534 |

- 상위 10건은 교리 분류상 Ecclesiology 9건, Baptism 1건이다.
- 인덱스에서 "Church Discipline"으로 분류된 TSU는 38건이며 최고 순위가 43위다.
- 질의가 "교회의 질서와 권징"이라는 두 개념을 묶고 있고 "교회의 질서" 쪽 의미가 지배한다. 순수 벡터 유사도 순위이며 재정렬·어휘 결합은 없다.

**IMPACT**: 사용자가 권징만 물으면 결과가 달라질 수 있다. 버그가 아니라 질의 구성과 밀집 검색의 특성이다.
**RECOMMENDATION**: 순위 개선은 Retrieval Engine 변경이므로 본 TO 범위 밖이며 승인 대상이다. 필요하면 질의 재작성·하이브리드 결합을 별도 ADR로 검토한다.
**한계**: 질의 하나(EUAT-01)만 분석했다. 다른 질의의 순위 분포는 측정하지 않았다.
