"""회귀 — SermonDraftService가 repeat_penalty를 실제로 쓰는지 확인
(2026-09-15, S1-4 배포 사양 품질 실측).

기존 코드는 "설교문은 긴 출력이 정상"이라는 이유로 repeat_penalty·
num_predict를 아예 적용하지 않았다. llama3.2:3b 실측 결과 repeat_penalty
부재 자체가 퇴행 반복(같은 문구를 20회+ 그대로 반복)을 유발했다 —
groundedness 0/5. repeat_penalty=1.3을 추가하자 3.0/5로 개선됐다(같은
프롬프트·모델). num_predict는 `_gen_options()`의 1024를 그대로 쓰지
않는다(실측상 문장 중간에서 잘림) — `_sermon_gen_options()`은 별도로
`DEFAULT_SERMON_NUM_PREDICT`(기본 2048)를 쓴다.

ollama.generate를 가로채 실제로 전달되는 options만 검사한다 — 실제
Ollama 호출은 하지 않는다.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.generation as gen  # noqa: E402
from core.generation import SermonDraftService  # noqa: E402
from core.retrieval import RankedCandidate  # noqa: E402


@pytest.fixture
def captured_options(monkeypatch):
    calls: list[dict] = []

    def fake_generate(model=None, prompt=None, options=None):
        calls.append(options)
        return {
            "response": "제목: 테스트\n서론: 서론\n대지1: 대지\n결론: 결론"
        }

    monkeypatch.setattr(gen.ollama, "generate", fake_generate)
    return calls


def _one_candidate() -> list[RankedCandidate]:
    return [RankedCandidate(tsu_id="t1", content="참고 자료 본문", final_score=0.9)]


class TestGenerateOutlineOptions:
    def test_repeat_penalty_applied(self, captured_options):
        service = SermonDraftService()
        service.generate_outline("로마서 5:1-5, 고난 중의 소망", _one_candidate())

        assert captured_options, "ollama.generate가 호출되지 않았다"
        options = captured_options[0]
        assert options["repeat_penalty"] == gen.DEFAULT_REPEAT_PENALTY

    def test_uses_sermon_num_predict_not_qa_num_predict(self, captured_options):
        service = SermonDraftService()
        service.generate_outline("로마서 5:1-5, 고난 중의 소망", _one_candidate())

        options = captured_options[0]
        assert options["num_predict"] == gen.DEFAULT_SERMON_NUM_PREDICT
        # 회귀: Q&A 전용 1024로 되돌아가지 않았는지 명시적으로 확인
        if gen.DEFAULT_SERMON_NUM_PREDICT != gen.DEFAULT_NUM_PREDICT:
            assert options["num_predict"] != gen.DEFAULT_NUM_PREDICT


class TestExpandPointOptions:
    def test_repeat_penalty_applied(self, captured_options):
        service = SermonDraftService()
        service.expand_point("대지 1", "로마서 5:1-5, 고난 중의 소망", _one_candidate())

        assert captured_options
        options = captured_options[0]
        assert options["repeat_penalty"] == gen.DEFAULT_REPEAT_PENALTY

    def test_uses_sermon_num_predict(self, captured_options):
        service = SermonDraftService()
        service.expand_point("대지 1", "로마서 5:1-5, 고난 중의 소망", _one_candidate())

        options = captured_options[0]
        assert options["num_predict"] == gen.DEFAULT_SERMON_NUM_PREDICT
