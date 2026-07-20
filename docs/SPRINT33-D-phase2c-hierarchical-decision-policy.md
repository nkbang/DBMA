# SPRINT33-D Phase 2-C — Hierarchical Decision Policy Draft

상태: Investigation + Design only. Code change: none. Commit: none.

## 목적

현재 builder decision flow를 시각화하고, semantic boundary / safety
cap / hard fallback의 우선순위를 정의하며, production chunker와의
경계를 재확인하고, ADR-007 amendment 필요 여부를 판단한다.

---

## 1. 현재 Builder Decision Flow (Phase 1 구현 그대로)

```text
for each candidate (paragraph, in document order):

    ┌─────────────────────────────────────────────────────┐
    │ score_boundary(candidate)  — heading/paragraph/tiny/  │
    │ sentence/scripture 5-feature 합산, threshold=50        │
    └───────────────────────┬───────────────────────────────┘
                             │
              buf가 비어있지 않고
              is_boundary=True 이고
              buf_len >= min_chunk_size(80) ?
                     │                    │
                    Yes                   No
                     │                    │
              ┌──────▼──────┐             │
              │ flush(buf)  │             │
              │ = semantic  │             │
              │   split     │             │
              └──────┬──────┘             │
                     │                    │
                     └────────┬───────────┘
                               │
                    candidate를 buf에 추가
                    buf_len += len(candidate) + 2
                               │
                    buf_len > safety_cap(chunk_size*1.5) ?
                     │                    │
                    Yes                   No
                     │                    │
              ┌──────▼──────┐             │
              │ flush(buf)  │             │
              │ = safety-cap│      (다음 candidate로 계속)
              │   split     │
              └─────────────┘

문서 끝: 남은 buf를 flush(EOF split)
```

**현재 존재하는 계층은 2단계뿐이다**: semantic split과 safety-cap
split. Phase 2-A §3에서 논의된 "hard fallback"(단어 경계만 지키는
강제 절단, `_slice_preserving_words` 성격)은 **아직 구현되어 있지
않다** — 이번 Phase 2-C는 이 3단계를 어떻게 배치할지 설계만 한다.

---

## 2. 우선순위 정의 (설계, 미구현)

### 문제의 재구성 (Phase 2-B 발견 반영)

Phase 2-B가 밝힌 대로, "safety cap"은 사실 두 가지 서로 다른 상황에서
발동한다:

```text
상황 1(원인 B, 보편적): semantic 신호가 그냥 부족해서 buf가 자연스럽게
  1800자까지 자란 경우 — 이때 safety cap은 "정상적인 2차 방어선"으로
  작동한다. 이 buf 안의 candidate들은 각각 정상 크기(<1800)다.

상황 2(원인 A, Profile B 전용): buf에 넣은 candidate 자체가 이미
  >1800자라서, 그 candidate 하나만으로 safety cap을 즉시 초과하는
  경우 — 이때 safety cap이 flush해도 그 결과물(단일 candidate 그대로)
  은 여전히 크기 목표를 만족하지 못한다. **hard fallback이 필요한
  지점은 정확히 여기뿐이다.**
```

### 제안 우선순위 (3단계)

```text
1순위 — Semantic Split
  조건: buf_len >= min_chunk_size AND is_boundary(candidate)=True
  역할: 항상 최우선. 의미 경계가 있으면 그것을 따른다.

2순위 — Safety-cap Split (상황 1)
  조건: semantic 신호 없이 buf_len > safety_cap, 그러나 이 buf를
        구성하는 개별 candidate는 모두 <= safety_cap
  역할: semantic 신호 부재 시의 정상적인 길이 기반 대체(fallback).
        현재 Phase 1 구현 그대로 유지.

3순위 — Hard Fallback Split (상황 2, 신규 설계, 미구현)
  조건: 단일 candidate 자체가 이미 > safety_cap
  역할: 문장 경계도 없는(Phase 2-A 실측: 100% 분할 불가) 콘텐츠에
        대한 최후 수단. word-safe 강제 절단만 수행 — semantic 정보를
        전혀 참고하지 않는 순수 길이 기반 분할이며, 오직 Profile B의
        후주(색인/카탈로그/참고문헌) 콘텐츠에만 실질적으로 적용된다
        (Phase 2-A: Profile A는 이 상황 자체가 발생하지 않음, 0건).

이 3단계가 서로 배타적으로 정의되어 있어("상황 1"과 "상황 2"는
candidate 자체의 길이로 명확히 구분됨) 우선순위 충돌이 발생하지
않는다 — 2순위와 3순위는 사실 "같은 safety-cap 발동"의 두 하위
케이스이지, 서로 경쟁하는 규칙이 아니다.
```

---

## 3. Production Chunker와의 경계 재확인

```text
core/hierarchical_chunk_builder.py (SPRINT33-D)
  = shadow-only 계층. 여전히 어디서도 import되지 않음.
core/chunking_optimizer.py (production)
  = 무수정, 무접촉 상태 유지.

Hard Fallback(3순위, 설계만 완료)을 실제로 구현하더라도:
  - chunking_optimizer.py의 _slice_preserving_words()를 직접 import
    하지 않는다(Phase 2-A §1에서 확인한 새 의존 방향 문제) — 대신
    core/hierarchical_chunk_builder.py 내부에 동등한 순수 함수를 독립
    구현하거나, core/text_normalizer.py에 위치한 기존 word-boundary
    유틸(있다면)을 재사용하는 방향을 다음 Preflight에서 검토.
  - 여전히 shadow 산출물일 뿐, production pipeline에 연결하지 않는다.

이 경계는 SPRINT33-D 전체(Phase 1~2)에서 한 번도 흔들리지 않았으며,
Phase 2-C도 이 경계를 그대로 유지한다.
```

---

## 4. ADR-007 Amendment 필요 여부 — 필요함(판단)

```text
ADR-007(§1 minimum improvement threshold, §2 orphaned acceptance range)은
SPRINT33-D 완료 후 재산정하기로 이미 이연되어 있었으나, 그 이연의
전제("시제품 결과를 보고 수치를 정한다")가 Phase 1~2-B를 거치며 다음과
같이 더 구체화되었다:

  1. §2(orphaned acceptance range)는 corpus 전체 단일값이 아니라
     genre profile별로 나뉘어야 한다(Phase 2-B §3/§5).
  2. "chunk-size constraint"라는 단일 축이 실제로는 3개의 독립 축
     (recovery / semantic flush ratio / unsplittable outlier ratio)
     으로 세분화되어야 한다(Phase 2-B §4) — ADR-007 원문은 이 세분화를
     예견하지 못했다.
  3. Hard Fallback이라는 3번째 decision layer가 설계상 필요함이
     확인되었다(본 문서 §2) — ADR-007은 원래 "semantic-first,
     length-fallback" 2단계만 전제했다.

→ 이 세 가지는 ADR-007이 이미 세운 원칙(계층 분리, genre 분리 철학)을
  뒤집는 것이 아니라 "구체화·정밀화"하는 성격이므로, 새 ADR을 만들
  필요는 없고 ADR-007에 Amendment로 추가하는 것이 적절하다고 판단한다
  (기존 ADR-001~006 관례상 Amendment는 원 ADR의 Consequences/Decision
  섹션에 각주 형태로 추가되어 왔다 — 이번 세션에서 실제 선례 파일을
  확인하지는 못했으나, ADR-005/006 문서 구조상 유사한 갱신 방식이
  합리적).
```

---

## 완료 조건

```text
✅ 현재(Phase 1) decision flow 시각화 — 2단계(semantic/safety-cap)임을
   명확히 표현
✅ 3단계 우선순위 설계(semantic → safety-cap → hard fallback) — 2/3순위가
   상호 배타적 하위 케이스임을 확인해 우선순위 충돌 없음을 보임
✅ Production 경계 재확인 — hard fallback 구현 시에도
   chunking_optimizer.py 직접 의존 없이 독립 구현 권고
✅ ADR-007 amendment 필요 판단 — 필요(3개 구체적 사유), 신규 ADR
   불필요(기존 원칙의 정밀화 성격)
코드 변경 없음, commit 없음.
```
