"""Regression test — dbma.py::_embed_texts() runtime hardening (RC-HOTFIX-02).

Guards the oversized-input guard and the selective retry policy added to
fix the reported runtime error:

    인덱싱 실패: Ollama 임베딩 호출 실패 (model=bge-m3:latest):
    Post "http://127.0.0.1:65000/tokenize": EOF (status code: 400)

Root cause (RC-HOTFIX-01): Ollama's llama-server runner rejects inputs
exceeding its fixed physical batch size (2048 tokens); repeated rejection
was observed to kill the runner process, and requests arriving during its
restart window fail with a raw EOF. This test does not require a live
Ollama server — ollama.embed() is monkeypatched.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import dbma


class TestOversizedInputGuard:
    def test_oversized_input_raises_before_calling_ollama(self, monkeypatch):
        calls = []
        monkeypatch.setattr(dbma.ollama, "embed", lambda **kw: calls.append(kw) or {"embeddings": [[0.0]]})

        oversized_text = "a" * (dbma._MAX_SAFE_EMBED_TOKENS + 100) * dbma._APPROX_CHARS_PER_TOKEN
        try:
            dbma._embed_texts([oversized_text], model="bge-m3:latest")
            assert False, "expected ValueError"
        except ValueError:
            pass
        assert calls == [], "ollama.embed() must not be called for oversized input"

    def test_normal_sized_input_is_not_rejected(self, monkeypatch):
        monkeypatch.setattr(dbma.ollama, "embed", lambda **kw: {"embeddings": [[0.1, 0.2]]})
        result = dbma._embed_texts(["a short chunk of text"], model="bge-m3:latest")
        assert result == [[0.1, 0.2]]


class TestSelectiveRetry:
    def test_retries_on_eof_and_succeeds(self, monkeypatch):
        state = {"calls": 0}

        def flaky_embed(**kw):
            state["calls"] += 1
            if state["calls"] < 2:
                raise Exception('Post "http://127.0.0.1:65000/tokenize": EOF (status code: 400)')
            return {"embeddings": [[1.0]]}

        monkeypatch.setattr(dbma.ollama, "embed", flaky_embed)
        monkeypatch.setattr(dbma.time, "sleep", lambda s: None)

        result = dbma._embed_texts(["test"], model="bge-m3:latest")
        assert result == [[1.0]]
        assert state["calls"] == 2

    def test_does_not_retry_on_non_retryable_error(self, monkeypatch):
        state = {"calls": 0}

        def failing_embed(**kw):
            state["calls"] += 1
            raise Exception("model 'llama3.1' not found (status code: 404)")

        monkeypatch.setattr(dbma.ollama, "embed", failing_embed)
        monkeypatch.setattr(dbma.time, "sleep", lambda s: None)

        try:
            dbma._embed_texts(["test"], model="bge-m3:latest")
            assert False, "expected RuntimeError"
        except RuntimeError:
            pass
        assert state["calls"] == 1, "non-retryable errors must fail on the first attempt"

    def test_gives_up_after_max_attempts_on_persistent_eof(self, monkeypatch):
        state = {"calls": 0}

        def always_eof(**kw):
            state["calls"] += 1
            raise Exception("EOF")

        monkeypatch.setattr(dbma.ollama, "embed", always_eof)
        monkeypatch.setattr(dbma.time, "sleep", lambda s: None)

        try:
            dbma._embed_texts(["test"], model="bge-m3:latest")
            assert False, "expected RuntimeError"
        except RuntimeError:
            pass
        assert state["calls"] == dbma._EMBED_MAX_ATTEMPTS


class TestIsRetryableOllamaError:
    def test_eof_is_retryable(self):
        assert dbma._is_retryable_ollama_error(Exception("... EOF ...")) is True

    def test_http_500_is_retryable(self):
        assert dbma._is_retryable_ollama_error(Exception("HTTP Error 500: Internal Server Error")) is True

    def test_timeout_is_retryable(self):
        assert dbma._is_retryable_ollama_error(Exception("Read timeout")) is True

    def test_model_not_found_is_not_retryable(self):
        assert dbma._is_retryable_ollama_error(Exception("model 'x' not found (status code: 404)")) is False


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
