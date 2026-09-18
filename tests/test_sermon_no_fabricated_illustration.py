"""tests/test_sermon_no_fabricated_illustration.py — 예화 생성 금지 회귀 방지.

HQ 지시(2026-09-15): "예화는 절대 생성하지 않아야 한다. 없으면 없는대로
설교 원고를 신앙양심대로 작성해야 한다."

지시 이전 상태가 정확히 그 반대였다 — core/generation.py의
_EXPANSION_STYLE_GUIDANCE["주제설교"]가 "목회적 적용과 예화는 그 근거에서
자연스럽게 도출되게 하라"로 **예화를 요구**하고 있었다.

이 테스트가 상수만 보지 않고 **조립된 프롬프트**를 검사하는 이유: 상수가
남아 있어도 프롬프트에 끼워 넣는 배선이 끊기면 아무 효과가 없고, 그 상태로
상수 테스트는 통과한다. ollama.generate를 가로채 실제로 모델에 전달되는
문자열을 확인한다.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.generation as gen  # noqa: E402
from core.generation import (  # noqa: E402
    _EXPANSION_STYLE_GUIDANCE,
    _NO_FABRICATED_ILLUSTRATION_DIRECTIVE,
    SermonDraftService,
)
from core.retrieval import RankedCandidate  # noqa: E402


@pytest.fixture
def captured_prompts(monkeypatch):
    """ollama.generate 로 실제 전달되는 프롬프트를 모은다."""
    prompts: list[str] = []

    def fake_generate(model=None, prompt=None, options=None):
        prompts.append(prompt)
        # 개요 파서가 받아들이는 최소 형태 — 언어 오염 재시도를 유발하지 않는다.
        return {
            "response": (
                "제목: 시험 제목\n서론: 시험 서론\n"
                "대지1: 첫째\n대지2: 둘째\n대지3: 셋째\n결론: 시험 결론"
            )
        }

    monkeypatch.setattr(gen.ollama, "generate", fake_generate)
    return prompts


@pytest.fixture
def candidates() -> list[RankedCandidate]:
    return [
        RankedCandidate(
            tsu_id="TSU-ROM-test_chunk_00001",
            content="칭의는 믿음으로 말미암는다.",
            metadata={"source_file": "test.txt"},
            final_score=0.9,
        )
    ]


# ── 지시문 내용 ──────────────────────────────────────────────


def test_directive_forbids_fabrication_not_illustrations_themselves():
    """'예화를 쓰지 마라'가 아니라 '지어내지 마라'여야 한다 —
    참고 자료에 실제로 있는 예화는 출처를 밝히고 쓸 수 있다."""
    d = _NO_FABRICATED_ILLUSTRATION_DIRECTIVE
    assert "지어내지 마라" in d
    assert "출처" in d


def test_directive_makes_absence_an_acceptable_outcome():
    """HQ 지시의 핵심 — '없으면 없는대로'. 빈자리를 채우라는 압박이 없어야 한다."""
    d = _NO_FABRICATED_ILLUSTRATION_DIRECTIVE
    assert "예화 없이 쓰라" in d
    assert "결함이 아니다" in d


# ── 배선 (조립된 프롬프트에 실제로 들어가는가) ──────────────


def test_outline_prompt_carries_the_directive(captured_prompts, candidates):
    SermonDraftService().generate_outline("로마서 5:1-5, 소망", candidates)

    assert captured_prompts, "ollama.generate 가 호출되지 않았다"
    assert _NO_FABRICATED_ILLUSTRATION_DIRECTIVE in captured_prompts[0]


def test_expansion_prompt_carries_the_directive(captured_prompts, candidates):
    SermonDraftService().expand_point("첫째 대지", "로마서 5:1-5, 소망", candidates)

    assert captured_prompts, "ollama.generate 가 호출되지 않았다"
    assert _NO_FABRICATED_ILLUSTRATION_DIRECTIVE in captured_prompts[0]


@pytest.mark.parametrize("sermon_format", ["주제설교", "강해설교"])
def test_directive_applies_to_every_sermon_format(
    captured_prompts, candidates, sermon_format
):
    """형식에 따라 빠지는 구멍이 없어야 한다."""
    SermonDraftService().expand_point(
        "첫째 대지", "로마서 5:1-5, 소망", candidates, sermon_format=sermon_format
    )

    assert _NO_FABRICATED_ILLUSTRATION_DIRECTIVE in captured_prompts[0]


# ── 회귀: 예화를 요구하던 문구가 되살아나지 않는다 ──────────


@pytest.mark.parametrize("sermon_format", ["주제설교", "강해설교"])
def test_style_guidance_no_longer_requests_illustrations(sermon_format):
    """이 문구가 되돌아오면 지시문이 있어도 모델은 예화를 만든다 —
    요구와 금지가 같은 프롬프트에 함께 들어가기 때문이다."""
    guidance = _EXPANSION_STYLE_GUIDANCE[sermon_format]
    assert "예화" not in guidance, f"{sermon_format} 지침에 예화 요구가 되살아났다"
