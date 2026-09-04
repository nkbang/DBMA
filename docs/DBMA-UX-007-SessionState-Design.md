# DBMA-UX-007 §13 Session State 상세설계

**작성**: CUE (Claude Code, `dev/dbma-engine`), 2026-08-19
**근거**: [DBMA-UX-007-IMPLEMENTATION-SPEC.md](DBMA-UX-007-IMPLEMENTATION-SPEC.md)
§13(New Component Inventory)이 "신규 세션 상태 필요"라고만 표시하고
실제 스키마를 정의하지 않아, §2(이어서 읽기)/§7(설교 연구 허브)
착수 전 구체화가 필요했다. 본 문서는 §13을 대체하지 않고 **보강**한다
— 원본 스펙의 승인 범위·문구는 그대로 두고, 실제 구현 계약(키 이름,
저장 위치, 수명)만 확정한다.

**원칙**: 새 아키텍처를 만들지 않는다. 이미 이 코드베이스에 존재하는
두 개의 검증된 패턴만 재사용한다.

---

## 0. 기존 패턴 조사 결과 (구현 근거)

| 패턴 | 예시 | 수명 | 저장 위치 |
|---|---|---|---|
| **A. 순수 `st.session_state`** | `research_detail_selection`, `chat_detail_selection`, `sermon_draft_state` | 브라우저 세션 한정(새로고침·재시작 시 소멸) | 없음(메모리만) |
| **B. 디스크 미러 — 단일 파일 덮어쓰기** | `chat.py`의 `chat_messages` ↔ `_CHAT_HISTORY_FILE`(`data/chat_session_history.json`), 매 턴마다 `_save_chat_history()`로 전체 재기록 | 앱 재시작 후에도 유지 | JSON 파일 1개, 매번 통째로 덮어씀 |
| **C. 디스크 append-only 세션 로그** | `core/research_workspace.py`(ADR-004) — `create_session()`/`add_query_result()`/`list_sessions()`, `output/research/sessions.json`, 원자적 쓰기(`tmp`+`os.replace`), **참조만 저장**(tsu_id/document_id/citation_id, 본문 복제 없음) | 영구 누적 | JSON 파일 1개, append + 원자적 교체 |

§13이 요구하는 3가지 신규 상태(이어서 읽기/설교 연구 세션/전환 선택)를
이 3개 패턴에 그대로 매핑하면 새 아키텍처 없이 해결된다.

---

## 1. Tier A — 신규 코드 불필요 (기존 인프라 재사용)

### 1.1 "최근 연구" 중 검색 절반 (§2.3)

Home의 "최근 연구" 2열 그리드 중 "최근 검색어 1건"은 **이미 존재하는**
`core/research_workspace.py::list_sessions()`로 충족된다 — 가장 최근
session의 마지막 `query` 엔트리를 읽으면 된다. 신규 스키마·신규 파일
없음. `research.py`가 검색할 때마다 `add_query_result()`를 이미
호출하고 있으므로(`research.py:304`) 별도 배선도 불필요.

---

## 2. Tier B — 신규 `st.session_state` 키 (패턴 A, Core 무변경, 저위험)

기존 `*_detail_selection` / `*_state` 명명 관례를 그대로 따른다.

### 2.1 `sermon_research_selection` (전환 버퍼, §8 명시)

```python
# 검색·연구/읽기 화면에서 "설교 연구로 보내기" 클릭 시 append
st.session_state.setdefault("sermon_research_selection", [])
st.session_state["sermon_research_selection"].append({
    "tsu_id": str,
    "document_id": str,
    "excerpt": str,       # 인용 카드에 쓰인 발췌문 그대로(재검색 없이 표시)
    "source_label": str,  # 인용 카드의 "출처" 필드 그대로
    "added_at": str,       # isoformat
})
```

- `research_detail_selection` 패턴과 동일하게 소비 시점(설교 연구
  허브가 로드될 때)에 `sermon_research_state`로 흡수 후 유지(리스트는
  비우지 않음 — 여러 화면에서 계속 추가되는 누적 버퍼이므로
  `research_detail_selection`처럼 "소비 후 None"이 아니라 "설교 연구
  허브가 열릴 때마다 append된 새 항목만 흡수"하는 차이가 있음, 구현
  시 흡수된 항목은 별도 `_consumed` 플래그 또는 인덱스로 구분).

### 2.2 `sermon_research_state` (§7 허브 작업 상태)

`sermon_draft_state`와 동일한 형태(status 필드 + 타입 명시 필드)로
설계 — 새 패턴 도입 아님:

```python
st.session_state["sermon_research_state"] = {
    "status": "collecting",  # collecting | outlining | ready
    "materials": [],          # sermon_research_selection에서 흡수된 항목들
    "notes": {},               # material 식별자(tsu_id) -> 자유 텍스트, 또는 "_global"
    "outline_draft": [],       # 사용자 수동 입력 단계 리스트 (자동 생성은 Proposed, 범위 밖)
}
```

이 상태는 **브라우저 세션 한정**(패턴 A) — 앱 재시작 시 소멸. Home의
"최근 설교 연구" 카드는 v1에서 이 세션 상태가 있을 때만 표시하고,
없으면 §9 Empty State로 폴백(카드 자체 숨김)한다. 재시작 후에도
"최근 설교 연구"를 보여주려면 Tier C 확장이 필요 — **v1 범위에서는
의도적으로 제외**(아래 §4 참고).

---

## 3. Tier C — 신규 디스크 영속 모듈 (패턴 B, 신규 모듈 1개, C1 Review 필요)

### 3.1 "이어서 읽기" 마지막 위치 (§2.2)

"이어서 읽기" 카드는 앱을 재시작해도(다음날 다시 켜도) 마지막으로
읽던 자료를 보여줘야 의미가 있다 — 브라우저 세션 한정 상태로는
스펙 의도(§2 "내 연구가 어디 와 있는가")를 충족 못 한다. `chat.py`의
"단일 파일 덮어쓰기" 패턴(B)을 그대로 복제한 신규 모듈 제안:

```python
# core/reading_session.py (신규, 제안)
# chat.py의 _save_chat_history/_load_chat_history와 동일한 형태 —
# 새 저장 방식 도입이 아니라 같은 패턴을 새 파일로 복제

def save_last_read(document_id: str, title: str, source_label: str) -> None: ...
def load_last_read() -> dict | None: ...
# 저장 위치: {DEFAULT_OUTPUT_DIR}/reading/last_position.json
# 형태: {"document_id": ..., "title": ..., "source_label": ..., "read_at": iso}
# 스크롤 위치(§5 "원문 다시 보기" 시 위치 복원)는 v1에 포함하지 않음 —
# 스펙 §6에 "기존 인프라에 없으면 문서 상단 진입으로 폴백"이라고 이미
# 명시돼 있어 저장 필드에서도 제외, 문서 단위 복귀까지만 보장.
```

- **왜 새 모듈인가, `research_workspace.py`를 확장하지 않는가**:
  `research_workspace.py`는 ADR-004로 "검색 세션"만 다루도록 범위가
  명확히 정의돼 있다(append-only 쿼리 로그). "마지막으로 읽은 문서"는
  성격이 다른 개념(단일 최신값, 덮어쓰기)이라 같은 append-only 스키마에
  욱여넣으면 ADR-004 범위를 임의로 넓히는 것 — 대신 이미 존재하는
  "단일 파일 덮어쓰기" 패턴(B, chat.py)을 새 파일로 복제하는 쪽이
  기존 ADR을 건드리지 않는다.
- **CUE Operating Policy 적용**: 이건 "새 Architecture Layer 추가"에
  해당하지 않는다(기존 패턴 B의 복제일 뿐, 새 저장 방식이 아님) —
  다만 신규 영속 모듈 자체가 §7 어댑터·향후 "최근 설교 연구" 확장의
  전례가 되므로, 착수 전 **C1 Review 권장**(Validator 추가급은 아니나
  "Metadata Model 변경"에 가장 가까운 항목). 강제 게이트는 아니지만
  단독으로 판단해 바로 구현하지 않고 한 번 검토 후 진행 제안.

---

## 4. Research → Sermon Draft 어댑터 (§7 gap, 구현 시 재확인 항목)

`sermon_draft_state`(`ui/pages/sermon_draft.py:92`) 기존 필드 대조:

| `sermon_draft_state` 필드 | 어댑터가 채울 수 있는가 | 방법 |
|---|---|---|
| `scripture_and_theme` | 가능 | `sermon_research_state["materials"]`의 성경 참조 메타데이터 + `notes`를 사람이 읽을 문자열로 합성, **초안일 뿐 텍스트 영역은 그대로 편집 가능**(자동 확정 아님) |
| `style_files` | 부분 가능 | 선택된 material의 `document_id`가 `list_source_files()` 결과와 매칭되면 채움, 매칭 안 되면 빈 리스트 유지(추측 금지) |
| `candidates` / `outline` | **채우지 않음(v1)** | `RankedCandidate` 내부 구조와 결합하는 대신, 1단계 폼 제출 시 정상적인 `QueryProcessor` 재검색 경로를 그대로 타게 둔다 — 검색 결과를 직접 주입하는 최적화는 `core/generation.py` 구조를 더 조사해야 하는 별도 과제(v2 후보로 명시, 지금 시도하지 않음) |

이 표가 §7의 "구현 착수 시 재확인 항목"을 구체화한 결과다 — v1은
"텍스트 프리필까지"로 범위를 좁혀 Core(`core/generation.py`) 무변경을
유지한다.

---

## 5. 구현 순서 제안 (위험도 순, 각각 독립 Task Order 가능)

1. **Tier A** — Home "최근 검색" 카드: `research_workspace.list_sessions()` 읽기 전용 연결. 신규 코드 없음, C1 가능.
2. **Tier B** — `sermon_research_selection` + `sermon_research_state` + §7 허브 화면(수동 입력까지). Core 무변경, C1 가능.
3. **§7 어댑터(§4 표 기준, 텍스트 프리필만)** — `sermon_draft.py` 진입점 확장. Core 무변경, C1 가능.
4. **Tier C** — `core/reading_session.py` 신규 + §5 읽기 화면의 "이어서 읽기" 저장/복원. **C1 Review 권장 후 착수**.

각 단계는 041처럼 완료조건·AppTest 검증·독립 보고서 형식의 개별
Task Order로 쪼갤 것 — 이번 문서는 설계 확정까지만, 구현은 미착수.
