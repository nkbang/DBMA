---
title: SourceTierBonus 실효화 + 모델 SYSTEM 전통 일치 빌드 보고서
created: 2026-09-10
author: CUE
status: 구현 완료 · 회귀 통과 · 커밋 전 승인 대기 (Retrieval Engine + 모델 config)
audit_item: PM 정렬 감사 선결 #5·#6
base: claude/p0-3-context-bibliography (체인 #11 → #12 → #13 → #14 → 본 건)
scope: core/retrieval.py, resources/models/Modelfile.theology-bot-v2,
       docs/architecture/ADR-009-Amendment-A.md, tests/test_source_tier_bonus.py
---

# #5 SourceTierBonus 실효화 + #6 모델 SYSTEM 전통 일치

## #5 — `compute_source_tier_bonus()` 실효화

### 문제

`core/retrieval.py::compute_source_tier_bonus()`는 이름과 달리 `source_tier`를
전혀 보지 않고 `source_provenance.review_status`만 봤다 — "SourceTierBonus"
라면서 사실상 review_status bonus였다. 그리고 현행 코퍼스에는
`source_provenance` 자체가 없어 항상 0.0(가중치 0.05가 dead).

### 변경 (사용자 선택: "함수를 source_tier 반영형으로 실효화")

- `_SOURCE_TIER_RANK` 등급표 신설 — `scripts/ingest_logos_export.py`가 쓰는
  값(`scholarly_commentary`)과 설계 문서 §9의 값(`logos_primary`/
  `personal_research`)을 반영:
  - 1차 자료(성경·신조·신앙고백·Logos 원문): 1.0
  - 학술 2차(주석·조직신학·학술): 0.7
  - 개인 연구·설교 노트: 0.3
  - 표에 없는 비어있지 않은 tier: 0.5
  - tier 없음: 종전 동작(reviewed → 1.0 / else 0.0)
- review gate: `review_status in (reviewed, approved)` → 전액,
  아니면 ×0.6 (tiered-but-unreviewed는 provenance 없는 자료보단 높고
  reviewed보단 낮게)
- 결과 [0.0, 1.0] 클램프

### 현행 코퍼스 영향 — 없음

`source_provenance` 없음 → 첫 분기에서 0.0 반환. **랭킹 공식 결과 불변.**
벤치/골드 재검증 불요(입력이 바뀌지 않음). Logos-export 등 provenance를
갖춘 자료가 색인될 때부터 0.05 가중치가 등급별로 작동한다.

한 가지 잠재적 동작 변화: `scholarly_commentary` + `reviewed` 조합이
종전 1.0 → 0.7. 이 조합을 쓰는 자료가 현재 0건이고, 0.05 가중 성분이라
최종 점수 영향 최대 0.05×0.3=0.015. 어느 테스트도 이 값을 단언하지 않음.

## #6 — 모델 SYSTEM 전통 일치

### 문제

`Modelfile.theology-bot-v2`의 SYSTEM 1행이 "복음주의 및 개혁주의 관점"인데
ADR-009 확정 전통·수집 코퍼스(Fuller/Dagg/Hiscox/1689)는 개혁파 침례교다.
ADR-009 Amendment A §5는 "모델 재빌드 안 함, Modelfile 주석에 기록만"으로
이 불일치를 의도적으로 방치했다.

### 변경 (사용자 선택: "Modelfile SYSTEM 직접 수정 + Amendment A §5 갱신")

- SYSTEM 1행: `"복음주의 및 개혁주의 관점을 가진"` →
  `"개혁파 침례교(1689 런던신앙고백 계열, 신자세례·회중교회론) 전통에 서 있는"`
  (`DENOMINATION_PROFILE`과 동일 표현)
- Modelfile 헤더 주석의 "이 커밋은 기록이지 변경이 아니다" → 이력 블록으로
  갱신(#1 최초 기록 / #2 SYSTEM 전통 교체)
- ADR-009 Amendment A §5의 해당 항목을 취소선 + `[2026-09-10 개정]` 주석으로
  뒤집고, "개정 이력" 절 추가. Amendment 전체는 여전히 **Proposed**.
- `scope_modified` frontmatter에 Modelfile 추가

### 적용 조건

**저장소 파일 변경이며, 실제 모델에 반영되려면 사용자가**
`ollama create my-theology-bot-v2 -f resources/models/Modelfile.theology-bot-v2`
**를 실행해야 한다.** 그 전까지 실행 중인 모델은 종전 SYSTEM을 쓰고,
`core/generation.py::_DENOMINATION_DIRECTIVE`(PR #11에 포함)가 매 질의마다
전통을 명시한다. 앱 쪽 지시문은 재빌드 후에도 유지한다.

## 검증

```bash
~/envs/dbma311/bin/python -m pytest -q tests/
```

- 신규 `tests/test_source_tier_bonus.py`: 8건
- 전체 회귀: **2904 passed, 15 skipped** (기존 2896 + 8)

## 승인 필요

- `core/retrieval.py`는 CLAUDE.md 예외 조항의 "Retrieval Engine" — 커밋·푸시
  전 사용자 승인.
- 접근 방식(#5 함수 실효화 / #6 SYSTEM 직접 수정 + Amendment 갱신)은
  2026-09-10 AskUserQuestion으로 사용자가 선택함.
- ADR-009 Amendment A는 Proposed 유지 — C1 리뷰·사용자 승인 전까지 다른
  구현의 근거로 쓰지 않음.
