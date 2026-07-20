# SPRINT33-D Phase 2-A — Long Paragraph Handling Preflight

상태: Investigation only. Code change: none. Commit: none(HQ 지시에 따라
이번 단계는 커밋하지 않고 보고만 수행).

## 목적

Hierarchical Chunk Builder(Phase 1)가 semantic boundary를 유지하면서
DBMA 기존 chunk constraint(목표 1200자, 안전망 1800자)를 만족할 수
있는지 조사.

---

## 1. 기존 primitive 재사용성 확인

```text
core/text_normalizer.py (안전하게 재사용 가능, 순환 의존성 없음):
  split_sentences_mixed()       — 문장 분할
  _merge_sentence_fragments()   — 문장 재결합(overlap_chars=0이면
                                   _sentence_overlap_tail이 항상 []
                                   반환 — overlap 미주입 확인, 코드로
                                   검증 완료)
  → core/hierarchical_chunk_builder.py(Phase 1)가 이미 core/heading_
    provider.py, core/semantic_boundary_detector.py를 text_normalizer.py
    에서 자유롭게 import하는 것과 동일한 안전한 방향.

core/chunking_optimizer.py 내부 전용(재사용 시 새로운 의존 방향 발생):
  _word_safe_tail()             — overlap prefix 합성용(Phase 6-B가
                                   root-cause로 지목한 바로 그 함수 —
                                   overlap이 이번 범위에서 제외되었으므로
                                   애초에 필요 없음)
  _slice_preserving_words()     — 단어 경계 보존 강제 슬라이스(문장
                                   단위로도 못 줄이는 경우의 최후
                                   수단, chunking_optimizer.py:321)

판단:
  - split_sentences_mixed/_merge_sentence_fragments는 그대로 재사용
    가능, dependency 방향 문제 없음(기존 패턴과 동일).
  - _word_safe_tail은 overlap 미적용 정책상 불필요 — 가져올 이유 없음.
  - _slice_preserving_words는 §2/§3에서 확인하듯 실제로 필요할 수
    있는 유일한 함수이나, chunking_optimizer.py 내부 private 함수라
    가져오면 "hierarchical_chunk_builder.py → chunking_optimizer.py"
    라는 지금까지 없었던 새로운 의존 방향이 생김(text_normalizer.py에
    동등 함수를 두는 대안도 가능 — 단 두 경우 모두 chunking_optimizer.py
    코드 변경 없이는 공식 재노출 불가, private 함수 직접 import로
    처리하거나 로컬 재구현 필요 — SPRINT32-F가 heading_provider.py에서
    한 것과 같은 패턴).
  - production chunker와 behavior 차이: _merge_sentence_fragments는
    문장을 " ".join()으로 재결합 — 원문 그대로의 substring이 아님.
    단, Phase 1 빌더는 애초에 substring 재탐색이 아니라 오프셋을
    구조적으로 전달하는 방식이라 이 문제를 이미 회피하고 있음(Phase
    6-B가 겪은 offset mismatch 문제가 재발하지 않음 — 설계상 장점
    재확인).
```

---

## 2. Long Paragraph 분포 조사

```text
Beta corpus 전체(16106개 candidate) 길이 분포:

document                    total    <1200  1200-1800  1800-2400  2400-4000  4000+
11. 고린도전서                1107     1107          0          0          0      0
12. 고린도후서                 783      783          0          0          0      0
2 Chronicles Vol.15           1864     1694        117         49          4      0
2 Kings Anchor Bible            947      628        143        108         67      1
2 Kings Power/Fury            1276     1185         53         34          4      0
2 Kings, Volume 13            3013     2739        152         61         52      9
3. 마가복음                   1525     1525          0          0          0      0
5. 요한복음1                  1114     1114          0          0          0      0
6. 요한복음2                  1166     1166          0          0          0      0
7. 사도행전1                  1061     1061          0          0          0      0
8. 사도행전2                  1268     1268          0          0          0      0
9. 로마서1                     982      982          0          0          0      0

AGGREGATE  16106  15252(94.70%)  465(2.89%)  252(1.56%)  127(0.79%)  10(0.06%)
```

**핵심 발견 1 — 장문단은 전적으로 4개 영문 WBC/주석서 문서에만 존재**:
한국어 문서 8개는 전부 1200자 초과 문단이 0건. 장문단 문제는 corpus
전체가 아니라 특정 장르(영문 학술 주석서)에 국한된 현상.

**핵심 발견 2 — 1800자 초과 389건 전량이 "문장 1개"로 판정됨**:

```text
total candidates > 1800 chars: 389
split_sentences_mixed() 결과가 1개 이하(=분할 불가): 389 / 389 = 100.0%
```

샘플 확인(길수록 더 뚜렷):

```text
길이 6511(corpus 전체 최장): "2 Kings, Volume 13"
  '375 Isaia h , th e prophe t 1 9 4 -9 5 , 2 1 0 , 2 7 0 , 2 7 1 ...'
  → 알파벳 색인(index)/찾아보기 섹션. 마침표 거의 없음, 문장 구조
    자체가 없는 참조 목록.

길이 2400-4000 구간 샘플 3건 모두 동일 패턴:
  "Garrett, Paul R. House 24 Isaiah 1–33, rev. ed.. . . . . ."
    → 시리즈 카탈로그 목록(Phase 2-A/4-C에서 이미 확인된 "TOC 유출"과
      동일 계열)
  "21). Hazael's attacks on Israel (vv 22 23.) ־Reversal..."
    → 절 단위 개요(outline) 목록
  "xlvii Main Bibliography ten. 2nd ed. ATANT 54. Zurich..."
    → 참고문헌 목록(bibliography)

→ 장문단이 "실제 semantic unit"인가, "문장 분할 대상"인가라는 질문에
  대한 답: **둘 다 아니다.** 이들은 애초에 "문단"이 아니라 색인/목록/
  참고문헌 같은 구조화된 후주(back matter)가 split_paragraphs()의
  \n\n 분리 기준을 우연히 통과하지 못해 하나의 거대한 candidate로
  뭉친 것 — 산문(prose)이 아니므로 문장 경계 자체가 존재하지 않는다.
```

---

## 3. Boundary Priority Conflict 분석

```text
현재 hierarchy: Heading → Scripture Reference → Paragraph → Sentence

장문단(semantic boundary 없음 + paragraph >1800) 상황에서의 fallback
후보 3가지에 대한 영향 분석(결정은 하지 않음, HQ 지시대로):

A. semantic boundary 보존 + sentence split
B. sentence split 우선
   → A/B 모두 §2의 실측(389/389 = 100% 분할 불가)에 따라 사실상
     동일하게 무력화됨. sentence_boundary 계층 자체가 이 콘텐츠
     유형에서 작동하지 않으므로, "split"이 선택되어도 실질적으로는
     아무것도 나뉘지 않고 원래 크기 그대로 통과한다.

C. hard size fallback
   → 유일하게 실제로 크기를 줄일 수 있는 후보. chunking_optimizer.py:
     321의 _slice_preserving_words()(단어 경계만 보존하는 강제
     분할)와 동일한 성격 — 문장/의미 경계 없이 순수 길이로 자름.
     §1에서 확인했듯 재사용하려면 새로운 의존 방향이 생기거나 로컬
     재구현이 필요.

권고(결정 아님, 참고용): 이번 corpus의 실제 데이터 특성상 A/B는
장문단 문제에 대해 사실상 아무 효과가 없으므로, C(hard size fallback)
없이는 P95/max 목표를 만족시킬 방법이 없다. 다만 §4에서 보듯 이
문제는 애초에 production에도 이미 존재하는 문제이므로, "완전히
해결"보다 "허용 범위 재정의"가 더 현실적인 방향일 수 있다.
```

---

## 4. 매우 중요한 재발견 — 이 문제는 production에도 이미 존재함

```text
Phase 1 보고에서 "chunk 크기 이상치"를 새 빌더의 한계로 보고했으나,
이번 조사에서 production chunk(기존 chunking_optimizer.py 실제 산출물,
output/beta_validation_v5/*_chunks.txt)를 직접 확인한 결과:

  "2 Kings, Volume 13" production chunks (2984개 중):
    max = 6511자           (Phase 1 shadow builder의 max와 완전히 동일값!)
    1800자 초과 = 63개
    2400자 초과 = 36개

즉 production chunking_optimizer.py도 이 정확히 같은 색인/카탈로그
콘텐츠를 분할하지 못하고 있다 — chunking_optimizer.py:303의 "len(p) >
chunk_size*1.5" 분기가 split_sentences_mixed()를 호출하지만, 그 함수가
이 콘텐츠 유형에서는 항상 "문장 1개"를 반환하므로 실질적으로 아무
효과가 없다(§2와 동일한 실패 모드).

→ Phase 1에서 "새 빌더의 결함"으로 보고한 현상은 사실 기존
  production 청커가 이미 갖고 있던 미해결 한계를 그대로 물려받은
  것이며, 새로 도입된 회귀(regression)가 아니다. 두 시스템이 동일한
  콘텐츠에서 동일하게 실패한다는 것은 오히려 새 빌더가 최소한
  기존보다 "더 나빠지지" 않았다는 근거이기도 하다.
```

---

## D-5 평가 전제 조건(초안) 재검토 — §4 근거 반영

```text
HQ 제시 초안:
  P95 chunk size <= 1800
  AND max chunk size < 2400
  AND orphaned recovery >= Phase 1 baseline

이 초안대로면 "2 Kings, Volume 13" 등 4개 영문 주석서 장르는 production
청커조차 이미 이 기준을 통과하지 못한다(max=6511, 2400자 초과 36개
확인). 즉 이 acceptance criteria를 corpus 전체에 균일 적용하면, 새
빌더의 개선 여부와 무관하게 이 4개 문서는 항상 게이트를 통과할 수
없다 — ADR-007이 이미 제안한 "genre별 gate 분리" 원칙(Signal-Profile
Calibration)이 여기서도 그대로 적용되어야 함을 시사한다.
```

---

## 완료 조건

```text
✅ 재사용 primitive 확인 — split_sentences_mixed/_merge_sentence_fragments
   안전, _word_safe_tail 불필요(overlap 범위 밖), _slice_preserving_words
   필요 시 새 의존 방향 발생 확인
✅ 장문단 분포 조사 — 4개 영문 주석서에만 존재(한국어 문서 0건),
   389/389(100%)가 문장 분할 불가능한 색인/카탈로그/참고문헌 콘텐츠
✅ Boundary priority conflict — A/B는 실효 없음, C(hard size fallback)만
   유일한 실질적 해법 확인(결정은 이연)
✅ D-5 평가 전제 조건 — 균일 적용 시 4개 장르가 애초에 통과 불가함을
   발견, genre 분리 필요성 재확인
🆕 재발견: chunk 크기 이상치는 신규 빌더의 결함이 아니라 기존
   production 청커에 이미 존재하는 한계(동일 문서에서 동일 max값
   6511 확인) — Phase 1 보고 내용에 대한 중요한 보정
코드 변경 없음. chunking_optimizer.py 등 여전히 무접촉.
```
