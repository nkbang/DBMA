# tests/test_merge_sentence_fragments_overflow.py
"""
TDD 게이팅 테스트 — docs/PREFLIGHT-split-sentences-mixed-chunk-overflow.md
하위 결함 B(_merge_sentence_fragments가 oversized 단일 항목을 안 자르고
그대로 통과시켜 chunk_size 상한이 깨지는 문제)에 대한 실패 재현.

이 테스트는 현재(수정 전) 실패한다 — 의도된 것이다. C1(qwen3.6:35b-DBMAcode)
또는 CUE가 core/text_normalizer.py::_merge_sentence_fragments()를 수정해
이 테스트를 통과시키는 것이 목표다. core/chunking_optimizer.py 등 다른
파일 수정, 이 테스트 파일 자체의 assert 완화는 허용하지 않는다.

재현 근거: scripts/shadow_chunk_overflow_audit.py 실측(2026-07-20),
Beta corpus 12개 문서 중 영문 4개에서 4.6%(352/7736) 청크가 1.5x 상한
초과, 최악 6511자(target의 5.4배).
"""
import pytest

from core.text_normalizer import _merge_sentence_fragments


MAX_CHARS = 1200
OVERLAP_CHARS = 200


class TestMergeSentenceFragmentsOverflow:

    def test_oversized_single_fragment_never_exceeds_max_chars(self):
        """core/chunking_optimizer.py:305가 split_sentences_mixed()를
        호출하면, 개행 없는 입력에 대해 언제나 원문 전체를 '문장 1개'로
        돌려준다(근본 원인, Preflight 확정). 그 결과가 그대로
        _merge_sentence_fragments()에 들어왔을 때, 지금은 209행의
        `if len(sent) > max_chars: ...; chunks.append(sent)`가 자르지
        않고 통째로 통과시킨다 — 이 테스트가 그 결함을 재현한다."""
        long_single_sentence = ("이것은 매우 긴 한국어 문장입니다 " * 150).strip()
        assert len(long_single_sentence) > MAX_CHARS * 2  # 재현 전제조건

        chunks = _merge_sentence_fragments(
            [long_single_sentence], max_chars=MAX_CHARS, overlap_chars=OVERLAP_CHARS
        )

        assert all(len(c) <= MAX_CHARS for c in chunks), (
            f"chunk_size({MAX_CHARS}) 상한을 초과하는 청크가 있음: "
            f"{[len(c) for c in chunks if len(c) > MAX_CHARS]}"
        )

    def test_oversized_fragment_content_not_silently_dropped(self):
        """분할 시 word-safe 경계에서만 잘라야 하며(중간 단어 절단 금지),
        내용 손실이 없어야 한다 — 공백 정규화 정도의 차이는 허용."""
        long_single_sentence = ("이것은 매우 긴 한국어 문장입니다 " * 150).strip()
        chunks = _merge_sentence_fragments(
            [long_single_sentence], max_chars=MAX_CHARS, overlap_chars=OVERLAP_CHARS
        )

        reconstructed = "".join(c.replace(" ", "") for c in chunks)
        original_no_space = long_single_sentence.replace(" ", "")
        # overlap 캐리오버로 일부 문자가 중복 등장할 수 있으므로
        # "최소한 원문 글자 수만큼은 포함되어 있다"만 검증(엄격한 등치는
        # overlap 설계에 의존적이라 이 테스트의 범위 밖).
        assert len(reconstructed) >= len(original_no_space)

    def test_oversized_fragment_never_cuts_mid_word(self):
        """word-safe 절단: 각 청크의 시작/끝이 공백 경계와 맞아떨어져야
        한다(원문 내 단어를 반으로 쪼개지 않음). 공백으로 split한 뒤
        각 토큰이 어느 한 청크에 온전히 포함되는지로 검증."""
        long_single_sentence = ("이것은 매우 긴 한국어 문장입니다 " * 150).strip()
        chunks = _merge_sentence_fragments(
            [long_single_sentence], max_chars=MAX_CHARS, overlap_chars=OVERLAP_CHARS
        )
        original_tokens = set(long_single_sentence.split())
        for token in original_tokens:
            assert any(token in c for c in chunks), (
                f"토큰 '{token}'이 중간에 잘려 어느 청크에도 온전히 없음"
            )

    def test_normal_short_fragments_still_merge_as_before(self):
        """회귀 방지: 기존에 정상 동작하던 '짧은 문장 여러 개 병합' 경로는
        이번 수정으로 바뀌면 안 된다."""
        sentences = ["짧은 문장 하나.", "짧은 문장 둘.", "짧은 문장 셋."]
        chunks = _merge_sentence_fragments(
            sentences, max_chars=MAX_CHARS, overlap_chars=OVERLAP_CHARS
        )
        assert len(chunks) == 1
        assert chunks[0] == "짧은 문장 하나. 짧은 문장 둘. 짧은 문장 셋."

    def test_reproduces_preflight_synthetic_scale(self):
        """docs/PREFLIGHT-split-sentences-mixed-chunk-overflow.md가 보고한
        실제 재현 스케일(2999자 한국어 단일 문단)을 그대로 사용한
        회귀 앵커. 이 테스트가 통과하면 그 Preflight 문서의 '해결 전'
        재현 사례가 더 이상 재현되지 않는다는 뜻이다."""
        long_para = ("이것은 매우 긴 한국어 문단입니다. " * 150).strip()
        assert len(long_para) > 2900  # Preflight 문서의 2999자 스케일과 근접

        chunks = _merge_sentence_fragments(
            [long_para], max_chars=MAX_CHARS, overlap_chars=OVERLAP_CHARS
        )
        assert max(len(c) for c in chunks) <= MAX_CHARS
