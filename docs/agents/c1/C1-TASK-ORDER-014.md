// deno-fmt-ignore-file
# C1 Task Order 014 — 설교 에디터 맞춤법 검사 기능 구현

발급: CUE (2026-07-24)
발급 사유: CUE 세션 주간 토큰 한도 98% 도달 — 남은 구현 작업을 C1으로
이관한다.
대상: C1 (Cline 작업창 #1) — **반드시 새 Task/새 세션으로 시작**
성격: **구현 Task.** 아래 §2의 설계를 그대로 코드로 옮긴다. 설계를
다시 바꾸지 않는다 — 이미 CUE-사용자 간 합의된 방향이다. 단, §2.1의
의존성(hunspell 한국어 사전) 설치 가능 여부는 C1이 직접 확인 후
§5의 폴백 절차를 따를 것.

---

## Addendum (2026-07-24, CUE) — TLI 비전 문서 반영

Human HQ가 `docs/architecture/DBMA-TLI-Architecture-Vision-v1.md`
(장기 비전 문서, TLI = Theology Language Intelligence)를 제시했다.
CUE 검토 결과 방향은 승인하되, **이번 Task Order의 구현 범위는
그 문서의 §19 범위 그대로 유지하고 다음 형태로만 좁혀 반영한다**:

- §2.1의 `core/spellcheck.py` 단일 모듈 대신, **`core/tli/` 패키지에
  파일 2개만** 만든다:
  - `core/tli/spell_engine.py` — 추상 인터페이스(예:
    `class SpellEngine(Protocol): def check(self, text: str) -> list[dict]`)
  - `core/tli/hunspell_adapter.py` — `check_korean_spelling()`의
    실제 구현(§2.1 로직 그대로, hunspell 우선 → §5 폴백 순서 동일)이
    `SpellEngine`을 구현.
- `ui/pages/sermon_draft.py`는 `hunspell_adapter`를 직접 import하지
  않고, `spell_engine.py`가 노출하는 인터페이스(또는 그 인터페이스를
  구현한 인스턴스를 반환하는 간단한 factory 함수 하나)를 통해서만
  호출한다 — "UI → Hunspell 직접 연결 금지" 원칙(비전 문서 §5) 반영.
- **Dictionary Engine / Style Engine / Citation Engine / Named Entity
  Engine 파일은 이번에 생성하지 않는다** — 빈 스텁도 금지. 비전
  문서 §4의 다이어그램은 장기 목표이지 이번 라운드 산출물이 아니다.
  필요해지면 그때 가서 새 Task Order로 하나씩 만든다.
- `resources/hunspell/custom_theology.dic`(§2.2)는 비전 문서의
  `resources/dictionary/theology/` 구조를 미리 다 만들 필요 없이,
  이번 Task 범위에 필요한 최소 파일 하나만 있으면 된다.
- 그 외 §1~§7(배경/설계/테스트/금지사항/폴백/완료절차/원칙)은 전부
  원문 그대로 유효하다 — 변경 없음.

즉: "TLI라는 이름의 인터페이스 계층 뒤에 hunspell을 숨긴다"는 모양만
반영하고, 그 계층 안에 아직 안 쓰는 다른 Engine들을 미리 만들지는
않는다.

파일명 매핑(§3/§6 원문의 `tests/test_spellcheck.py` → 대체):
`tests/test_tli_hunspell_adapter.py` 하나로 §3의 (a)~(d) 케이스를
전부 커버하면 된다 — 인터페이스 파일(`spell_engine.py`)은 추상
정의뿐이라 별도 테스트 불필요.

---

## 1. 배경

사용자가 "설교문이 투입되면 한글 맞춤법을 확인하는 것이 좋겠다"고
제안했고, CUE가 검토한 결과:

- **적용 대상은 파이프라인 전체가 아니다.** 사용자 확인: "설교로
  분류된 것 중 **사용자가 작성한 것만**, 그리고 DBMA에서 설교작성으로
  설교자가 작성할 때는 맞춤법이 **설교 에디터에서** 걸려져야 한다."
  → 즉 RAW 폴더로 투입되는 기존 설교 모음 파일(타인 원고, 외부 출처)에는
  적용하지 않는다. 적용 대상은 오직 `ui/pages/sermon_draft.py`(이미
  존재하는 AI 보조 설교 작성 에디터)에서 **사용자가 직접 입력/수정한
  텍스트**뿐이다.
- **엔진**: hunspell(오프라인, 로컬 한국어 사전) — 이유:
  - `py-hanspell`(네이버 비공식 API 래퍼)은 외부 네트워크 호출이
    필요하고 비공식 API라 언제 끊길지 모름 — DBMA는 로컬/오프라인
    우선 기조(Mac 로컬 환경, `CLAUDE.md` "목표 환경" 참고)와 안 맞고,
    설교 원고를 외부로 보내는 것도 바람직하지 않음(개인정보/저작물).
  - hunspell은 표준 사전 기반이라 신학 용어·성경 인명("갈라디아",
    "칭의" 등)을 오탐(가짜 오류)으로 잡을 수 있음 — 이건 **사용자
    정의 사전(custom dictionary)**으로 해결한다(§2.3).

## 2. 설계 (그대로 구현)

### 2.1 신규 모듈: `core/spellcheck.py`

```python
def check_korean_spelling(text: str) -> list[dict]:
    """hunspell(ko_KR)로 text를 검사해 오류 후보 목록을 반환한다.
    각 항목: {"word": str, "suggestions": list[str], "offset": int}
    hunspell/사전 로드 실패 시 빈 리스트 반환 + logger.warning
    (크래시 금지 — 맞춤법 검사는 부가 기능이지 필수 경로가 아니다)."""
```

- Python 바인딩: `hunspell`(PyPI, libhunspell C 바인딩) 우선 시도.
  macOS에서 `brew install hunspell`로 C 라이브러리가 먼저 있어야
  pip install이 빌드된다 — **설치 안 되면 §5 폴백으로 전환**.
- 한국어 사전(`ko_KR.aff`/`ko_KR.dic`): LibreOffice 한국어 맞춤법
  확장(`ko-dict` — Apache 2.0/LGPL, 오픈소스) 파일을 내려받아
  `resources/hunspell/ko_KR.{aff,dic}`에 둔다(신규 디렉터리, 프로젝트
  루트 기준 — `.gitignore`에 큰 사전 파일 추가 여부는 파일 크기 보고
  CUE와 상의, 커밋 전 반드시 CUE 승인받을 것 — Cline 최적 프롬프트
  원칙: "추측하지 말고 질문").

### 2.2 사용자 정의 사전 (신학 용어 오탐 방지)

- `resources/hunspell/custom_theology.dic` — 신규 빈 파일로 시작
  (초기엔 비어있거나 최소 시드만).
- `check_korean_spelling()`은 기본 사전 검사 후, custom_theology.dic에
  있는 단어는 오류 목록에서 제외한다.
- 시드 값(최소): 자주 쓰이는 성경책 이름 중 표준국어사전에 없을 만한
  것들 — `core/config.py`나 기존 성경책 리스트(book_coverage 관련
  코드에 이미 66권 목록이 있을 것, 재사용할 것 — 새로 만들지 말고
  `grep -rn "book_id\|BOOK_NAMES\|성경책"  core/` 로 먼저 찾아볼 것)

### 2.3 UI 연동: `ui/pages/sermon_draft.py`

- 적용 지점 2곳(파일 상단 grep 결과 기준, 실제 줄 번호는 C1이 직접
  `grep -n` 확인 후 문서화):
  1. `_render_outline_step()`의 서론/대지/결론 `st.text_area` — "💾
     수정 반영" 버튼을 누를 때 검사.
  2. `_render_expansion_step()`의 대지 확장 텍스트 — 사용자가 확장된
     내용을 수정하고 다음 단계로 넘어갈 때 검사.
- 검사 결과가 있으면 **막지 않는다** — `st.warning()`으로 "맞춤법
  확인이 필요할 수 있는 단어: X, Y, Z (오탐이면 무시해도 됩니다)"
  형태로만 보여준다(참고 §2.4의 이유).
- 각 경고 항목 옆에 "이 단어는 정상" 버튼을 둬서 클릭하면
  `custom_theology.dic`에 추가한다(→ 다음 검사부터 제외).

### 2.4 왜 "경고만" 하고 막지 않는가 (설계 근거, 바꾸지 말 것)

설교문은 구어체·인용구·성경 고유명사가 많아 표준 사전 기준으로는
오탐이 잦다. 승인/저장을 막으면 정상적인 설교문도 계속 걸려 사용성이
나빠진다 — DBMA 프로젝트 원칙("결과 정밀도와 안정성을 우선") 중
안정성 쪽을 "차단하지 않는 경고"로 해석한 것. 이 판단을 C1이 임의로
"차단"으로 바꾸지 말 것 — 바꾸고 싶으면 구현 전에 질문할 것.

## 3. 테스트

- `tests/test_spellcheck.py` 신규
- 최소 케이스:
  (a) 정상적인 한국어 문장 → 오류 없음
  (b) 명백한 오타(예: "됬다" 등) → 오류 목록에 포함
  (c) custom_theology.dic에 등록된 단어는 오류에서 제외됨
  (d) hunspell/사전 로드 실패 시 빈 리스트 반환(크래시 안 함) —
      `unittest.mock`으로 로드 실패를 흉내낼 것
- hunspell 자체가 로컬에 설치 안 돼 있어 실제 검사 테스트가 어려우면,
  §5 폴백 경로로 작성하고 그 경로 기준으로 테스트할 것

## 4. 하지 말 것

- RAW 폴더로 투입되는 기존 설교 모음 파일(`core/processing.py`
  파이프라인, `ui/pages/sermon_review.py`)에는 맞춤법 검사를 걸지
  않는다 — 이번 Task의 범위 밖(사용자가 명시적으로 "사용자가 작성한
  것만"이라고 범위를 좁혔음).
- 승인/저장을 막는 방식으로 만들지 않는다(§2.4).
- `core/document_identity.py::guess_doc_type()`, `core/processing.py`
  수정 금지 — 이번 Task와 무관.

## 5. 의존성 설치 실패 시 폴백

`pip install hunspell`이 로컬 환경(가상환경 `~/envs/dbma311`, macOS)에서
C 라이브러리 미비로 실패할 가능성이 있다. 이 경우:

1. `brew install hunspell`을 먼저 시도(사용자에게 실행 승인 요청 —
   C1이 임의로 시스템 패키지를 설치하지 말 것, 반드시 확인 후 진행).
2. 그래도 안 되면, 순수 Python 구현체인 `spylls`(PyPI, hunspell
   포맷 사전을 순수 파이썬으로 읽는 라이브러리, C 바인딩 불필요)로
   대체 — `core/spellcheck.py`의 내부 구현만 바뀌고 외부
   인터페이스(`check_korean_spelling()`)는 동일하게 유지한다.
3. 둘 다 안 되면 구현을 중단하고 CUE에게 보고 — 임의로 다른 엔진으로
   바꾸지 말 것(엔진 선택은 이미 사용자·CUE 합의 사항).

## 6. 완료 후

- 변경/신규 파일 목록과 `pytest tests/test_spellcheck.py -q` 실행
  결과를 짧은 md로 남겨라(`docs/agents/c1/` 아래, 파일명 자유).
- 전체 회귀(`pytest tests/ -q`)도 실행해 기존 테스트가 깨지지 않았는지
  확인하고 결과를 같이 남길 것.
- CUE 검토 요청 — CUE가 실제 코드 diff와 테스트 결과를 재검증한 뒤
  커밋한다(C1이 직접 커밋하지 않음).

## 7. 원칙 재확인

- "이미 존재합니다"라고 주장하기 전에 실제 파일을 열어 확인
  (Diagnosis rule).
- 파일 경로·함수명·개수를 문서화할 때는 반드시 실제 grep/read 결과에
  근거할 것 — 존재를 확인 안 한 파일/함수를 산출물 문서에 적지 말 것.
- 새 세션으로 시작 — 이 Task Order가 유일한 근거.
- 시스템 패키지 설치(brew 등)나 사전 파일 다운로드처럼 되돌리기
  까다로운 작업은 실행 전 사용자에게 확인받을 것.
