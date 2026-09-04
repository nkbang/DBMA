"""DBMA — core/tli/hunspell_adapter.py 단위 테스트.

Task: C1-TASK-ORDER-014 §3

[버그 수정 2026-07-24, CUE] spylls(순수 파이썬 hunspell 리더)는 이
한국어 사전의 접사 규칙을 제대로 처리하지 못해(실측: "하나님"/"우리"/
"사랑" 같은 기본 단어까지 오탐) 실제 hunspell C 라이브러리(PyHunSpell
바인딩)로 교체했다 — 아래 테스트도 그에 맞춰 갱신.

- (a) 정상적인 한국어 문장 → 오류 없음
- (b) 명백한 오타("됬어") → 오류 포함, 정타("됐어")는 통과
- (c) custom_theology.dic에 등록된 단어는 오류에서 제외됨(조사 붙은 형태 포함)
- (d) hunspell/사전 로드 실패 시 빈 리스트 반환(크래시 안 함) — mock으로 흉내
- (e) SpellEngine Protocol + factory 구조 검증
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 프로젝트 루트를 sys.path에 추가
_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


class TestTLICustomWords(unittest.TestCase):
    """custom_theology.dic 로드 테스트 — 사전 의존성 불필요."""

    def test_custom_dictionary_path_exists(self):
        from core.tli.hunspell_adapter import _CUSTOM_THEOLOGY_DIC
        path = _CUSTOM_THEOLOGY_DIC
        self.assertTrue(path.exists(), f"custom_theology.dic이 존재해야 함: {path}")

    def test_custom_words_load(self):
        from core.tli.hunspell_adapter import _load_custom_words
        words = _load_custom_words()
        self.assertIsInstance(words, set)
        self.assertGreater(len(words), 0, "custom_theology.dic에 최소 시드 단어가 있어야 함")

    def test_bible_books_in_custom_dict(self):
        """66권 성경책 이름이 custom_theology.dic에 포함되어야 함."""
        from core.tli.hunspell_adapter import _load_custom_words
        from core.sermon.bible_books import BIBLE_BOOKS
        words = _load_custom_words()
        for name, _ in BIBLE_BOOKS:
            self.assertIn(name, words, f"성경책 '{name}'이 custom_theology.dic에 있어야 함")

    def test_theological_terms_in_custom_dict(self):
        """주요 신학 용어가 custom_theology.dic에 포함되어야 함."""
        from core.tli.hunspell_adapter import _load_custom_words
        words = _load_custom_words()
        expected_terms = {"칭의", "성화", "삼위일체", "경륜", "은혜", "구원", "속죄", "부활"}
        for term in expected_terms:
            self.assertIn(term, words, f"신학 용어 '{term}'이 custom_theology.dic에 있어야 함")


class TestTLIAddToCustom(unittest.TestCase):
    """add_to_custom_dictionary 테스트.

    [버그 수정 2026-07-24, CUE] 원래 테스트가 실제 resources/hunspell/
    custom_theology.dic 파일에 직접 썼다 — 실행할 때마다 더미 단어가
    누적되고, 파일 끝에 개행이 없어서 기존 마지막 단어("성결")와
    이어붙어 데이터가 손상되는 사고로 이어졌다(실측 확인 후 수동 복구).
    tmp_path로 격리해 실제 리소스 파일을 절대 건드리지 않게 한다."""

    def test_add_word_returns_true(self):
        from core.tli import hunspell_adapter
        engine = hunspell_adapter.HunspellSpellEngine()
        with patch.object(hunspell_adapter, "_CUSTOM_THEOLOGY_DIC", Path("/tmp/dbma_test_custom.dic")):
            Path("/tmp/dbma_test_custom.dic").write_text("", encoding="utf-8")
            result = engine.add_to_custom_dictionary("DBMA_TEST_WORD_014")
            self.assertTrue(result)
            Path("/tmp/dbma_test_custom.dic").unlink(missing_ok=True)

    def test_added_word_in_custom_dict(self):
        from core.tli import hunspell_adapter
        tmp_dic = Path("/tmp/dbma_test_custom2.dic")
        tmp_dic.write_text("", encoding="utf-8")
        with patch.object(hunspell_adapter, "_CUSTOM_THEOLOGY_DIC", tmp_dic):
            engine = hunspell_adapter.HunspellSpellEngine()
            engine.add_to_custom_dictionary("DBMA_TEST_WORD_015")
            words = hunspell_adapter._load_custom_words()
            self.assertIn("DBMA_TEST_WORD_015", words)
        tmp_dic.unlink(missing_ok=True)


class TestTLISpellEngineCheck(unittest.TestCase):
    """HunspellSpellEngine.check 테스트 — 사전 미설치 환경에서도 동작해야 함."""

    def test_returns_list(self):
        from core.tli.hunspell_adapter import HunspellSpellEngine
        engine = HunspellSpellEngine()
        result = engine.check("이것은 테스트 문장입니다.")
        self.assertIsInstance(result, list)

    def test_empty_string(self):
        from core.tli.hunspell_adapter import HunspellSpellEngine
        engine = HunspellSpellEngine()
        result = engine.check("")
        self.assertEqual(result, [])

    def test_short_words_only(self):
        """2글자 미만 단어만 있으면 빈 리스트."""
        from core.tli.hunspell_adapter import HunspellSpellEngine
        engine = HunspellSpellEngine()
        result = engine.check("나 너")
        self.assertEqual(result, [])

    def test_custom_words_not_flagged(self):
        """custom_theology.dic에 있는 단어는 오류로 표시되지 않아야 함."""
        from core.tli.hunspell_adapter import HunspellSpellEngine
        engine = HunspellSpellEngine()
        # "칭의"는 custom dictionary에 있으므로 오류로 표시되지 않음
        result = engine.check("칭의는 구원의 핵심 교리입니다.")
        for err in result:
            self.assertNotEqual(err["word"], "칭의",
                               f"'칭의'가 오류로 표시되면 안 됨: {result}")

    def test_bible_book_names_not_flagged(self):
        """성경책 이름은 오류로 표시되지 않아야 함(조사가 붙은 형태 포함)."""
        from core.tli.hunspell_adapter import HunspellSpellEngine
        engine = HunspellSpellEngine()
        result = engine.check("창세기와 출애굽기를 읽어보세요.")
        flagged = {err["word"] for err in result}
        self.assertNotIn("창세기와", flagged)
        self.assertNotIn("출애굽기를", flagged)

    def test_obvious_typo_is_flagged(self):
        """[CUE 검증 2026-07-24] 명백한 오타는 실제로 잡혀야 한다 —
        "됬어"(오타) vs "됐어"(정타)를 구분할 수 있어야 실질적으로
        쓸모 있는 기능이다."""
        from core.tli.hunspell_adapter import HunspellSpellEngine
        engine = HunspellSpellEngine()
        result = engine.check("정말 됬어 좋았다.")
        flagged = {err["word"] for err in result}
        self.assertIn("됬어", flagged)

    def test_correct_conjugation_not_flagged(self):
        from core.tli.hunspell_adapter import HunspellSpellEngine
        engine = HunspellSpellEngine()
        result = engine.check("정말 됐어 좋았다.")
        flagged = {err["word"] for err in result}
        self.assertNotIn("됐어", flagged)

    def test_biblical_proper_names_and_places_not_flagged(self):
        """[2026-07-24, 사용자 요청] 신학사전 확장 — 성경 인명/지명이
        조사가 붙어도 오탐되지 않아야 함."""
        from core.tli.hunspell_adapter import HunspellSpellEngine
        engine = HunspellSpellEngine()
        result = engine.check("므비보셋은 다윗을 만나러 예루살렘으로 갔고, 스룹바벨은 성전을 재건했다.")
        flagged = {err["word"] for err in result}
        self.assertEqual(flagged, set(), f"성경 인명/지명이 오탐됨: {flagged}")

    def test_common_words_not_falsely_flagged(self):
        """[CUE 검증 2026-07-24] spylls 시절 "하나님"/"우리"/"사랑" 같은
        기본 단어가 오탐됐던 회귀 방지 테스트."""
        from core.tli.hunspell_adapter import HunspellSpellEngine
        engine = HunspellSpellEngine()
        result = engine.check("하나님은 우리를 사랑하십니다.")
        flagged = {err["word"] for err in result}
        self.assertEqual(flagged, set(), f"기본 단어가 오탐됨: {flagged}")


class TestTLIDictLoadFailure(unittest.TestCase):
    """사전 로드 실패 시 빈 리스트 반환 테스트 (크래시 금지)."""

    def test_dict_none_returns_empty_list(self):
        """[버그 수정 2026-07-24, CUE] 실제 hunspell.HunSpell() 생성자가
        예외를 던지는 경우를 흉내내 크래시 없이 빈 리스트를 반환하는지
        확인한다(engine._dict를 직접 None으로 미는 건 재로드로 덮어써져
        검증이 안 됨 — _ensure_loaded가 매번 새로 시도하기 때문)."""
        from core.tli import hunspell_adapter
        engine = hunspell_adapter.HunspellSpellEngine()
        with patch("hunspell.HunSpell", side_effect=RuntimeError("mock load failure")):
            result = engine.check("테스트 문장")
        self.assertEqual(result, [])

    def test_hunspell_not_installed(self):
        """hunspell 모듈이 설치되지 않은 경우에도 크래시 없이 동작해야 함."""
        with patch.dict(sys.modules, {"hunspell": None}):
            import importlib
            from core.tli import hunspell_adapter
            importlib.reload(hunspell_adapter)
            engine = hunspell_adapter.HunspellSpellEngine()
            result = engine.check("테스트")
            self.assertEqual(result, [])
            importlib.reload(hunspell_adapter)  # 다음 테스트를 위해 정상 상태로 복구


class TestTLIFactory(unittest.TestCase):
    """create_spell_engine() factory 테스트."""

    def test_returns_engine_with_check(self):
        from core.tli.spell_engine import create_spell_engine
        engine = create_spell_engine()
        # check 메서드가 있어야 함
        self.assertTrue(hasattr(engine, "check"))
        result = engine.check("테스트 문장")
        self.assertIsInstance(result, list)

    def test_noop_fallback_when_hunspell_missing(self):
        """hunspell이 없으면 no-op 엔진(또는 로드 실패 시 빈 결과)을 반환해야 함."""
        with patch.dict(sys.modules, {"hunspell": None}):
            import importlib
            from core.tli import hunspell_adapter
            importlib.reload(hunspell_adapter)
            from core.tli import spell_engine
            importlib.reload(spell_engine)
            engine = spell_engine.create_spell_engine()
            result = engine.check("테스트")
            self.assertEqual(result, [])
            importlib.reload(hunspell_adapter)  # 다음 테스트를 위해 정상 상태로 복구
            importlib.reload(spell_engine)


if __name__ == "__main__":
    unittest.main()