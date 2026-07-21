---
title: "ADR-009: SIL Theology Engine — Doctrine Filter Architecture & TSU Extension Shape"
category: architecture
sprint: DBMA-SIL Phase 1
based_on:
  - docs/agents/c1/DBMA-SIL-Theology-Engine-Design.md
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md
created: 2026-07-21
status: Architecture Decision (부분 확정 — 구조만 확정, 신학적 어휘/임계값은 별도 승인 대기)
scope_modified: docs/architecture/ + core/tsu_builder.py(스키마 shape만) + core/sermon/(골격만)
---

# ADR-009: SIL Theology Engine — Doctrine Filter Architecture & TSU Extension Shape

| | |
|---|---|
| Status | Partially Accepted — 구조 확정, 내용(어휘/임계값) 미확정 |
| Date | 2026-07-21 |
| Deciders | HQ(사용자) 승인 / CUE 설계·구현 |
| Supersedes | — (C1-TASK-ORDER-005 / DBMA-SIL Phase 0은 이 ADR로 대체되어 중단됨) |
| Superseded by | — |

---

## Context

사용자가 외부 자료(ChatGPT 대화록 2건 — 설교 제작 툴 아이디어,
설교엔진디자인)를 근거로 DBMA-SIL(Sermon Intelligence Layer)의 신학
엔진 설계를 요청했다. 검증 결과 DBMA에는 이미 다음이 존재함을
확인했다(`docs/agents/c1/DBMA-SIL-Theology-Engine-Design.md` §1):

- `core/generation.py::SermonDraftService` — 설교 개요/대지 확장 생성
  이미 구현·연결됨(`ui/pages/sermon_draft.py`).
- `core/tsu_builder.py:336` — TSU 레코드에 `"themes": []` 필드가 이미
  존재하나 어디서도 채워지지 않는 죽은 필드.
- `core/query_enhancements.py::EnhancedQueryParser` — 쿼리 단계에서
  이미 신학 테마(`themes`)와 의도(`intent`, `"theological"` 포함)를
  감지해 `ParsedQuery`에 담고 있음(`core/retrieval.py:78`).

사용자는 "확실한 것만 진행 승인"했다 — 이 ADR은 그 범위(아키텍처
구조)만 확정하고, 신학적 판단이 필요한 항목(교리 어휘, 신뢰도 임계값)은
별도 승인 대상으로 명시적으로 미확정 상태에 둔다.

---

## Decision — 확정되는 것 (구조)

### 1. Retrieval Engine 무변경 원칙 재확인

SIL은 `core/retrieval.py::RetrievalEngine`을 변경하거나 별도 검색
경로/가중치 체계를 추가하지 않는다(ADR-001 유지). 신학 테마 신호는
이미 존재하는 `EnhancedQueryParser`의 산출물을 `SermonDraftService`가
후처리 재정렬에만 사용한다 — 신규 retrieval 모듈 없음.

### 2. TSU 확장은 additive-only, 신규 필드 3개(구조만)

기존 `themes` 필드는 건드리지 않는다(용도 불명, 재해석하지 않음).
아래 필드를 TSU 레코드 스키마에 **구조로만** 추가한다 — 기본값은
`null`/`[]`이며, 실제 값을 채우는 어휘·로직은 이 ADR의 범위 밖이다:

```json
{
  "theological_claim": null,
  "doctrine_category": [],
  "baptist_theme": []
}
```

기존 레코드는 영향받지 않는다(additive-only, `core/tsu_builder.py`의
기존 SPRINT28-B/29-C 패턴과 동일).

### 3. 태깅 방식: 온디맨드(옵션 B) — 전체 corpus 일괄 태깅(옵션 A) 아님

`core/tsu_builder.py`의 TSU 빌드 파이프라인 자체는 이 필드를 채우지
않는다. 실제 값을 채우는 로직(있다면)은 `SermonDraftService`의 워크플로
시점에서만 온디맨드로 동작한다 — TSU 영구 저장 여부는 별도 설계.
근거: 실사용 데이터 없이 전체 corpus 재태깅 비용을 정당화할 수 없음.

### 4. Doctrine Filter 위치와 성격: 경고 전용, 후처리, 점수화 금지

`core/sermon/doctrine_filter.py`(신규 디렉터리·파일 골격만 이 ADR에서
확정)는:
- `SermonDraftService.generate_outline()` 결과에 대해 **사후**
  실행된다 — 생성 자체를 차단하지 않는다.
- 결과는 자연어 경고 문자열만 반환한다. **백분율 점수(예: "Biblical
  Fidelity 95%")는 금지** — 실제 실사용 근거 없이 정밀해 보이는
  숫자를 제시하는 것은 근거 없는 확신을 주는 안티패턴으로 판단
  (오늘 세션 전반에서 반복 확인된 실패 패턴과 동일 범주).
- 신뢰도가 낮으면 "확실하지 않음"을 그대로 노출한다 — 숨기지 않는다.
- 최종 신학적 판단 권한은 사용자(목회자)에게 있다 — 자동 차단 없음.

### 5. Multi-Agent 파이프라인 채택하지 않음

외부 자료가 제안한 Exegete/Theologian/Homiletician/Pastor 4단계
분리형 에이전트 구조는 채택하지 않는다. 기존 2단계 흐름(개요 생성 →
검토)에 검증 1단계만 추가하는 최소 구조를 원칙으로 한다.

---

## Decision — 확정되지 않는 것 (별도 승인 필요)

- **`doctrine_category`/`baptist_theme`의 실제 초기 어휘 목록** —
  신학적 판단이 필요하며 CUE/C1의 권한 밖. 사용자(목회자) 직접 결정
  대상.
- **Doctrine Filter의 신뢰도 임계값(어느 수준부터 경고를 표시할지)** —
  실사용 데이터 없이 임의 수치를 정하지 않는다.
- **`doctrine_filter.py`의 실제 LLM 프롬프트/체크 로직** — 어휘가
  없으면 정의할 수 없다. 어휘 확정 후 별도 구현 착수.
- **TSU 온디맨드 태깅 결과의 영구 저장 여부(캐시 레이어)** — 후속 설계
  대상.
- ADR 번호 확정만 이번에 다룸; 위 미확정 항목이 결정되면 이 ADR을
  Amendment로 갱신하거나 후속 ADR을 발행한다.

---

## Consequences

### 이번 ADR로 확정되는 것
- Retrieval Engine 무변경 원칙, TSU additive 스키마 shape(값 제외),
  온디맨드 태깅 방침, Doctrine Filter의 "경고 전용·점수화 금지" 원칙,
  Multi-Agent 미채택.

### 이번 ADR로 확정되지 않는 것(의도적으로 미룸)
- 교리 어휘, 신뢰도 임계값, 실제 검증 로직, TSU 태깅 결과 영속화 방식.

### 리스크
- 구조만 먼저 만들고 내용(어휘)이 늦게 확정되면, `doctrine_filter.py`가
  한동안 빈 골격(no-op)으로 남을 수 있다 — 의도된 상태.
- TSU 신규 필드가 실제로 채워지기 전까지는 어떤 코드도 이 필드를
  읽어서는 안 된다(존재하지만 항상 비어있는 상태를 전제해야 함,
  기존 `themes` 필드와 동일한 함정 방지).

---

## Next Steps

1. `core/sermon/__init__.py` 생성(빈 패키지 골격).
2. `core/tsu_builder.py`에 §Decision-2 필드 3개를 additive로 추가
   (기본값만, 채우는 로직 없음) — TDD로 기존 레코드 무영향 확인.
3. `doctrine_category`/`baptist_theme` 초기 어휘를 사용자가 확정하면
   `doctrine_filter.py` 실제 구현 착수(TDD 게이팅 방식).
4. 신뢰도 임계값은 초기 실사용(사용자 본인 설교 준비) 데이터를 모은
   뒤 재검토.
