# C1 Task Order 039 — NAE UX 구현 Phase 1: 용어집 전역 적용 + 인용 카드 공용 컴포넌트

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P1
**근거 문서**: [DBMA-UX-007-IMPLEMENTATION-SPEC.md](../../DBMA-UX-007-IMPLEMENTATION-SPEC.md)
(**구현 권한 — 이 문서가 기준이다**), 참고용
[mockup.html](../../design/nae-professional-redesign/mockup.html)
**작성일:** 2026-07-31
**HQ 승인**: 완료 (Gate 1~6 PASS, 2026-07-31)

---

## 0. 반드시 먼저 읽을 것

`docs/DBMA-UX-007-IMPLEMENTATION-SPEC.md`(이하 "스펙 문서") 전체, 특히:
- §0 UX Invariant — 이 Task의 존재 이유
- §11 User-facing Terminology — 이 Task의 작업 기준표
- §6 Citation / Provenance Component Specification — 이 Task의 두 번째 산출물

**`mockup.html`은 시각 참조일 뿐이다. HTML 구조를 그대로 복사하지 마라.**
스펙 문서의 컴포넌트 정의를 따르되, 기존 Streamlit 컴포넌트 패턴
(`st.markdown`+CSS, `st.button`, `st.caption` 등 기존 `ui/pages/*.py`가
이미 쓰는 방식)으로 구현한다 — 새로운 프레임워크나 렌더링 방식을
도입하지 않는다.

## 1. 이 Task의 범위 (Phase 1만)

스펙 문서 §15가 제안한 순서 중 **처음 두 항목만** 다룬다. 나머지(홈,
내 자료 이관, 읽기, 검색·연구 통합, 설교 연구 허브)는 이 Task 완료·검토
후 별도 Task Order로 순차 발급한다 — 한 번에 다 주지 않는다.

### 1-A. 기술적 leakage 제거 (스펙 §0 + §11 적용)

대상 파일과 정확한 위반:

| 파일 | 현재 | 교체 |
|---|---|---|
| `ui/pages/chat.py:513-514` | `caption_parts = [f"신뢰도(final_score): {score:.4f}"]` | 별점으로 변경. `research.py`의 기존 별점 변환 로직(`round(score*5)`, `⭐`/`☆`) 재사용 — 새로 만들지 말고 그대로 가져다 쓸 것 |
| `ui/pages/chat.py:521-522` | `caption_parts.append(f"근거 신뢰도(citation): {citation.evidence_confidence:.4f}")` | 이 줄 자체를 제거하거나, 1-B의 인용 카드 컴포넌트로 대체 |
| `README.md` 2행 | `"...RAG(Retrieval-Augmented Generation) 기반 검색·채팅..."` | "AI 기반 검색·채팅"으로 순화 (스펙 §11 "검색·연구" 용어 참고, README는 사용자 대상 설명이므로 동일 원칙 적용) |

작업 후 스펙 §11 표 전체를 기준으로 `ui/pages/*.py` 전 파일을 다시
grep 감사하라 — **단, 리터럴 문자열 grep만으로 끝내지 마라.**
`DBMA-UX-004`에서 겪은 것과 같은 실수(그리고 이번에 `chat.py`에서
실제로 놓쳤던 것)를 반복하지 않도록, f-string으로 조합되는 문자열도
직접 코드를 읽어서 확인하라.

### 1-B. 인용·출처 카드 공용 컴포넌트 (스펙 §6)

- `ui/components/` 아래 신규 함수로 구현 제안(기존 `ui/components/tables.py`,
  `ui/components/status.py`, `ui/components/detail_panel.py`와 같은 위치) —
  예: `ui/components/citation_card.py::render_citation_card(...)`
- 스펙 §6의 필드 구조(출처/본문 위치/자료 유형/관련성 별점/버튼 2개)를
  그대로 따른다. 데이터 없는 필드는 행 자체를 생략(스펙 명시 — "N/A"
  placeholder 금지)
- 이 컴포넌트로 **`chat.py`의 기존 출처 표시(`_render_source`,
  `_render_clickable_source`)를 교체**한다. 클릭 시 문서 상세로 이동하는
  기존 동작(`chat_detail_selection` 세션 상태)은 그대로 유지 — 컴포넌트
  교체이지 기능 삭제가 아니다
- `research.py`의 결과 카드는 이번 Task 범위 밖이다(이미 UX-004에서
  별점 등 정정 완료된 상태) — 손대지 마라. 이 컴포넌트를 거기 적용하는
  것은 다음 Phase(검색·연구 통합)에서 다룬다

## 2. 하지 말 것

- `core/*.py`, `pyproject.toml` 접촉 금지
- `research.py`, `library.py`, `dashboard.py`, `sermon_draft.py` 등
  이번 범위 밖 파일 수정 금지
- 사이드바 메뉴 구조 변경 금지(스펙 §1은 다음 Phase)
- mockup.html의 색상 값을 코드에 하드코딩하지 말 것 — 스펙 §14가 명시한
  대로 `ui/theme/colors.py::DBMADesignSystemColors`에 새 필드로 추가
  후 참조

## 3. 완료 조건

- [ ] `chat.py` 두 위반 지점 수정, 별점 컴포넌트 재사용 확인
- [ ] `README.md` RAG 표현 순화
- [ ] `ui/pages/*.py` 전체 재감사(코드 직접 읽기 포함) 결과표 제출 —
      추가 위반 발견 시 같이 수정하고 목록에 기록
- [ ] `ui/components/citation_card.py` 신규 구현, `chat.py`에 적용
- [ ] 기존 회귀 테스트 통과 (`pytest -k "chat"`)
- [ ] 브라우저 실제 실행으로 검증 — Chat 화면에서 실제 질문을 던져
      출처 카드가 별점으로 뜨는지, 문서 상세 이동이 정상 동작하는지
      스크린샷 또는 텍스트 추출로 증거 남길 것 (DBMA-UX-004에서 확립된
      방식 그대로 — grep만으로 끝내지 말 것)

## 4. 산출물

`docs/agents/c1/C1-TASK-ORDER-039-REPORT.md` — 수정 파일 목록, 재감사
결과표, 회귀 테스트 결과, 브라우저 검증 증거.

## 5. 다음 조치

이 Task 완료·CUE 검토 통과 후, 스펙 §15 순서대로 Phase 2(홈 화면 재구성)
Task Order를 발급한다.
