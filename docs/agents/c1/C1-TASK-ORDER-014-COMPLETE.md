# C1-TASK-ORDER-014 — 설교문 초안 내 한글 맞춤법 검사기 (TLI 패키지 리팩터링 포함)

**Task Order:** C1-TASK-ORDER-014  
**Agent:** C1 (DBMA Core Engineer)  
**Date:** 2026-07-24  
**Status:** ✅ COMPLETE — CUE 검토·정정 완료 (2026-07-24)

**CUE 정정 사유**: C1의 원본 구현(spylls 기반)을 CUE가 검토 중 실제
문장으로 테스트한 결과, "하나님"/"우리"/"사랑" 같은 기본 단어까지
오류로 잘못 판정하는 심각한 문제를 발견했다(spylls가 이 한국어
사전의 접사 규칙을 완전히 지원하지 못함 — spylls는 순수 파이썬
재구현체라 실제 hunspell C 라이브러리 대비 기능이 일부 누락돼
있음). 사용자 승인을 받아 (1) LibreOffice 계열 오픈소스 한국어
사전(`spellcheck-ko/hunspell-dict-ko` 0.7.94, 약 14MB)을 다운로드해
`resources/hunspell/ko_KR.{aff,dic}`로 배치하고, (2) `brew install
hunspell` + pip 바인딩(Apple Silicon 전용 심볼릭 링크 우회 필요,
아래 §2.1 참고)으로 실제 hunspell C 라이브러리를 설치해 spylls를
대체했다. 아래 내용은 이 정정을 반영한 최종 상태다 — C1의 원본
아키텍처 설계(TLI 인터페이스 분리, custom_theology.dic 등)는 그대로
유효하고 변경 없음.

---

## §1. 목표

설교문 작성 워크숍(ui/pages/sermon_draft.py)에서 사용자가 개요 및 확장된 설교문을 작성·수정할 때
한글 맞춤법 오류를 실시간으로 검사하고, 오탐 시 사용자 사전에 단어를 추가할 수 있는 기능을 연동한다.

**TLI 패키지 리팩터링 (CUE Addendum):**
- `core/spellcheck.py` → `core/tli/` 패키지로 마이그레이션
- `SpellEngine` Protocol + factory 패턴으로 추상화
- UI는 factory를 통해 엔진을 사용 — hunspell_adapter 직접 import 금지

---

## §2. 설계 요약 (C1-TASK-ORDER-014.md §2)

### 2.1 의존성 (CUE 정정)
- `hunspell` (PyPI 0.5.5, PyHunSpell — 실제 hunspell C 라이브러리 바인딩)
  — spylls를 대체. Apple Silicon에서 `pip install hunspell`이 그대로
  실패한다(패키지의 setup.py가 Intel Homebrew 경로
  `/usr/local/Cellar/hunspell/1.6.2/...`를 하드코딩). 재현 절차:
  ```
  brew install hunspell
  mkdir -p /usr/local/Cellar/hunspell/1.6.2/include
  ln -sf $(brew --prefix hunspell)/include/hunspell \
      /usr/local/Cellar/hunspell/1.6.2/include/hunspell
  ln -sf $(brew --prefix hunspell)/lib/libhunspell-1.7.dylib \
      /usr/local/lib/libhunspell.dylib
  LDFLAGS="-L/usr/local/lib" pip install hunspell
  ```
- 한국어 사전 `ko_KR.aff`/`ko_KR.dic` — `spellcheck-ko/hunspell-dict-ko`
  0.7.94 (GitHub, 오픈소스, 약 14MB)를 다운로드해 `resources/hunspell/`
  에 배치(사용자 승인 후 CUE가 다운로드). **git에 커밋**하기로 결정
  (Offline First 원칙, 사용자 승인).
- custom_theology.dic — 시드 데이터 포함 (성경 66권 + 신학 용어)

### 2.2 TLI 패키지 구조 (리팩터링 후)

```
core/tli/
├── __init__.py          # SpellEngine, create_spell_engine export
├── spell_engine.py      # SpellEngine Protocol + factory
└── hunspell_adapter.py  # HunspellSpellEngine 구현체
```

**핵심 API:**
- `create_spell_engine() -> SpellEngine` — best-available 엔진 반환
- `SpellEngine.check(text: str) -> list[dict]` — 맞춤법 검사
- `SpellEngine.add_to_custom_dictionary(word: str) -> bool` — 사용자 사전 추가

**설계 결정:**
- SpellEngine은 Protocol (structural subtyping) — 미래 엔진 교체 가능
- factory는 hunspell unavailable 시 no-op 엔진 반환 (crash-safe)
- hunspell_adapter 직접 import는 `core/tli/hunspell_adapter.py` ONLY

### 2.3 UI 연동 (ui/pages/sermon_draft.py)
- **개요 검토 단계:** "💾 수정 반영" 버튼 클릭 시 서론+대지+결론 전체 검사
- **본문 확장 단계:** 확장 완료 시 전체 설교문 검사
- 각 오류에 대해 "✓ 정상" 버튼으로 오탐 단어 추가
- custom_theology.dic에 추가된 단어는 재검사 시 제외

### 2.4 사용자 사전 파일
- 경로: `resources/hunspell/custom_theology.dic`
- 형식: hunspell .dic (첫 줄 = 단어 수, 이후 줄 = 단어)
- 시드 데이터: 성경 66권 이름 + 주요 신학 용어

---

## §3. 구현 상세

### 3.1 core/tli/spell_engine.py — Protocol + factory

```python
class SpellEngine(Protocol):
    def check(self, text: str) -> list[dict]: ...

def create_spell_engine() -> SpellEngine:
    try:
        from .hunspell_adapter import HunspellSpellEngine
        return HunspellSpellEngine()
    except Exception:
        return _NoOpSpellEngine()  # crash-safe
```

### 3.2 core/tli/hunspell_adapter.py — 구현체 (CUE 정정)

- `HunspellSpellEngine.check(text)` — 실제 hunspell(ko_KR)로 검사
- `HunspellSpellEngine.add_to_custom_dictionary(word)` — 사용자 사전에 추가
- lazy-load: 첫 check() 호출 시 ko_KR dictionary 로드
- custom_theology.dic 단어는 검사에서 완전히 제외(조사가 붙은 형태도
  `_is_custom_word_with_josa()`로 인식 — 아래 §CUE 정정 참고)

**§CUE 정정 — spylls → 실제 hunspell 교체 경위:**

C1의 원본 구현(spylls)을 CUE가 실제 문장으로 검증한 결과:
```
"하나님은 우리를 사랑하십니다. 그러므로 우리도 서로 사랑해야 합니다."
→ 하나님은, 우리를, 우리도, 합니다  (4단어 전부 오탐)
```
직접 원인을 추적한 결과 spylls는 이 사전(ko-aff-dic)의 접사/합성어
플래그를 완전히 지원하지 못해 "하나님"/"우리"/"사랑" 같은 **사전에
분명히 존재하는 기본 단어조차 조회에 실패**했다(반면 "사랑하십니다"
같은 활용형은 우연히 통과 — 일관성 없음). spylls는 순수 파이썬
재구현체로, 자체 문서에도 실제 hunspell C 라이브러리 대비 기능이
일부 누락돼 있다고 명시돼 있다.

실제 hunspell C 라이브러리(PyHunSpell)로 교체 후 동일 문장 재검증:
```
"하나님은 우리를 사랑하십니다. 그러므로 우리도 서로 사랑해야 합니다.
 됬어 됐어. 창세기와 출애굽기를 읽어보세요."
→ 됬어  (실제 오타 하나만 정확히 검출, 나머지는 정상 통과)
```
`됬어`(오타)와 `됐어`(정타)를 정확히 구분하는 것도 확인됨.

**남은 보정 1건**: hunspell 자체는 표준 사전 단어의 조사/어미 활용을
정확히 처리하지만, `custom_theology.dic`(성경책 이름 등)은 문자열
그대로만 등록돼 있어 "출애굽기를"처럼 조사가 붙으면 그대로는 못
찾는다. hunspell 재조회에는 손대지 않고, custom_words 매칭에만 좁혀
흔한 조사(은/는/이/가/을/를/도/와/과/의/에/로/만/며 등)를 뗀 뒤
재확인하는 `_is_custom_word_with_josa()`를 추가했다.

### 3.3 resources/hunspell/custom_theology.dic

**시드 데이터:**
- 성경 66권 전체 이름 (창세기 ~ 요한계시록)
- 주요 신학 용어: 칭의, 성화, 삼위일체, 경륜, 은혜, 구원, 속죄, 부활 등

### 3.4 ui/pages/sermon_draft.py 연동

```python
# OLD: from core.spellcheck import check_korean_spelling
# NEW:
from core.tli.spell_engine import create_spell_engine

# Usage:
_engine = create_spell_engine()
errors = _engine.check(all_text)
```

**개요 검토 단계:**
1. "💾 수정 반영" 버튼 클릭 → `_spellcheck_pending_outline` 플래그 설정
2. 다음 render에서 `create_spell_engine().check()` 호출
3. 오류가 있으면 warning 배너 + 각 단어별 "✓ 정상" 버튼
4. "✓ 정상" 클릭 → `add_to_custom_dictionary()` → session_state 플래그 해제 → rerun

**본문 확장 단계:**
1. 모든 대지 확장 완료 시 `check_korean_spelling()` 호출
2. 오류가 있으면 다운로드 전 warning 표시
3. 각 단어별 "✓ 정상" 버튼으로 오탐 제거

---

## §4. 테스트 결과 (CUE 정정 반영)

### 4.1 tests/test_tli_hunspell_adapter.py — 18개 모두 통과

spylls 기반 테스트 15개에서 hunspell로 교체하며 mock 대상을
`spylls.hunspell.Dictionary.from_files` → `hunspell.HunSpell`로 갱신하고,
실제 판정 정확도를 검증하는 3개 신규 테스트를 추가했다:
`test_obvious_typo_is_flagged`("됬어" 오탐 검출),
`test_correct_conjugation_not_flagged`("됐어" 오탐 방지),
`test_common_words_not_falsely_flagged`("하나님"/"우리"/"사랑" 회귀 방지).

또한 `TestTLIAddToCustom`의 두 테스트가 **실제 `resources/hunspell/
custom_theology.dic` 파일에 직접 썼던 버그**를 발견해 수정했다 —
실행할 때마다 `DBMA_TEST_WORD_014/015`가 파일에 누적됐고, 파일 끝에
개행이 없어 기존 마지막 단어("성결")와 이어붙어 `성결DBMA_TEST_WORD_014`
로 데이터가 손상되는 사고로 이어졌다(발견 즉시 수동 복구, 테스트는
`/tmp` 임시 파일로 격리하도록 수정 — 실제 리소스 파일을 더 이상
건드리지 않음).

```
pytest tests/test_tli_hunspell_adapter.py -q
18 passed
```

### 4.2 전체 회귀

```
pytest tests/ -q
812 passed, 11 warnings in 153.31s
```

---

## §5. 변경 파일 목록

| 파일 | 작업 | 설명 |
|------|------|------|
| `core/tli/__init__.py` | **신규** | TLI package init (SpellEngine export) |
| `core/tli/spell_engine.py` | **신규** | SpellEngine Protocol + factory |
| `core/tli/hunspell_adapter.py` | **신규(CUE 재작성)** | HunspellSpellEngine — 실제 hunspell C 라이브러리 사용 |
| `core/spellcheck.py` | **삭제** | TLI 패키지로 마이그레이션됨 |
| `resources/hunspell/ko_KR.aff`, `ko_KR.dic` | **신규(CUE)** | spellcheck-ko/hunspell-dict-ko 0.7.94, 약 14MB, 사용자 승인 후 다운로드 |
| `resources/hunspell/custom_theology.dic` | **수정(CUE)** | 테스트 오염으로 손상된 마지막 줄 복구, 트레일링 개행 추가 |
| `ui/pages/sermon_draft.py` | **수정** | spell_engine factory 경유로 호출 (§2.3) |
| `tests/test_tli_hunspell_adapter.py` | **수정(CUE)** | hunspell mock 대상 갱신, 정확도 회귀 테스트 3건 추가, 실제 리소스 파일 오염 버그 수정 |
| `tests/test_spellcheck.py` | **삭제** | test_tli_hunspell_adapter.py로 마이그레이션 |
| `requirements.txt` | **수정(CUE)** | `hunspell` 추가 + Apple Silicon 설치 우회 절차 코멘트 |

---

## §6. 검증 항목

- [x] custom_theology.dic 경로 정확함 (`resources/hunspell/custom_theology.dic`)
- [x] 66권 성경책 이름이 custom_theology.dic에 모두 포함
- [x] 주요 신학 용어가 custom_theology.dic에 포함
- [x] `check_korean_spelling("")` → 빈 리스트 반환
- [x] `check_korean_spelling("칭의는 구원의 핵심 교리입니다.")` → "칭의"가 오류로 표시되지 않음
- [x] `check_korean_spelling("창세기와 출애굽기를 읽어보세요.")` → 성경책 이름이 오류로 표시되지 않음
- [x] `add_to_custom_dictionary()` → True 반환 + 실제 파일에 기록
- [x] 사전 로드 실패 시 크래시 없이 빈 리스트 반환(hunspell.HunSpell 생성자 mock)
- [x] hunspell 모듈이 import되지 않아도 크래시 없이 빈 리스트 반환
- [x] factory 패턴: spell_engine.create_spell_engine() → SpellEngine interface
- [x] no-op fallback: hunspell unavailable 시 crash-safe
- [x] 전체 회귀 812개 모두 통과
- [x] TLI 패키지: hunspell_adapter 직접 import는 core/tli/hunspell_adapter.py ONLY
- [x] (CUE 추가) "됬어"(오타) 검출, "됐어"(정타) 미검출 — 실제 판정 정확도
- [x] (CUE 추가) "하나님"/"우리"/"사랑" 기본 단어 오탐 없음 — spylls 시절 회귀 방지

---

## §7. 제한 사항 및 향후 개선 (CUE 정정)

1. **한국어 사전 이제 실제로 동작함(CUE):** ko_KR.aff/dic을 설치하고
   spylls→hunspell 교체 후, 실제 문장 기준으로 정확도를 확인했다
   (§3.2 참고). 다만 오픈소스 사전(spellcheck-ko)이라 신조어·구어체
   표현은 여전히 오탐 가능 — `custom_theology.dic`으로 계속 보강.

2. **custom_theology.dic 조사 결합:** 성경책 이름 등에 조사가 바로
   붙으면(예: "출애굽기를") 문자열 완전일치만으로는 못 찾는다 —
   `_is_custom_word_with_josa()`로 흔한 조사만 보정(§3.2). 모든
   조사·복합 활용을 다 잡지는 못함(예: 매우 드문 조사 조합).

3. **UI 연동:** Streamlit rerun 패턴으로 인한 약간의 지연이 있을 수 있음
   - 플래그 기반 비동기 검사로 최소화

4. **TLI 패키지 확장:** Dictionary / Style / Citation / Named Entity 엔진은 별도 Task Order로 추가

5. **설치 재현성:** hunspell pip 패키지가 Apple Silicon을 공식 지원하지
   않아 심볼릭 링크 우회가 필요하다(§2.1). 다른 개발 환경에서 이
   기능을 쓰려면 동일 절차를 다시 밟아야 함 — 자동화 스크립트는
   아직 없음(향후 과제).

---

## §8. 정정 (CUE 2026-07-24)

### §8.1 단어 수 정정
- **오류:** 보고서에서 "283개 단어"라고 잘못 보고
- **정확한 수:** `grep -v "^#" resources/hunspell/custom_theology.dic | grep -v "^$" | sort -u | wc -l` → **262개**
- **원인:** 파일의 주석 줄, 빈 줄, 첫 줄의 단어 카운트 숫자를 포함해서 세었음
- **교훈:** 다음부터는 파일을 직접 열어 센 뒤 보고할 것

### §8.2 추가 보강 항목 제거
- "케셀링" 등 확인 안 된 신학자 이름은 출처가 명확하지 않으므로 임의 추가하지 않음
- "《교리학提要》" 등 한자가 섞인 용어도 표준 순한글 사전 형식과 맞지 않으므로 제외
- **원칙:** 신학 용어/인명을 추가할 때는 반드시 검증 가능한 출처를 밝히고, 출처 없이 추측으로 채우지 않음

## §9. CUE 검토 요청

C1이 직접 커밋하지 않습니다. CUE의 검토 후 merge 절차를 따릅니다.

**검토 사항:**
1. `core/tli/` 패키지 구조가 TLI Architecture Vision v1과 호환되는가?
2. SpellEngine Protocol + factory 패턴이 적절한가?
3. custom_theology.dic의 시드 데이터 (262개) 가 충분한가?
4. ui/pages/sermon_draft.py의 연동이 UX적으로 적절한가?
5. 추가 테스트가 필요한가?

**CUE 검토 후 다음 단계:**
- 검토 피드백 반영
- CUE 승인 후 merge
- Human HQ가 참고할 출처를 정하면 그때 검증된 용어만 추가
