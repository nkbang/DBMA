"""Regression test — core/embedder.py runtime hardening (ported from
tests/test_dbma_embed_texts_hardening.py, SPRINT20-I-D-2).

Guards the same contract as the legacy dbma._embed_texts test, now on the
official runtime path (core/embedder.py::_OllamaEmbedder / _embed_via_ollama):
  1. oversized-input guard  → ValueError before hitting Ollama
  2. selective retry        → EOF/timeout/500 retried, 404 not
  3. _is_retryable_ollama_error classification

No live Ollama needed — _embed_via_ollama / _check_ollama are monkeypatched.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import core.embedder as embedder


class TestOversizedInputGuard:
    def test_oversized_input_raises_before_calling_ollama(self):
        oversized = "a" * (embedder._MAX_SAFE_EMBED_TOKENS + 100) * embedder._APPROX_CHARS_PER_TOKEN
        try:
            embedder._embed_via_ollama(oversized, "bge-m3:latest")
            assert False, "expected ValueError"
        except ValueError:
            pass

    def test_normal_sized_input_not_rejected(self, monkeypatch):
        monkeypatch.setattr(embedder, "_embed_via_ollama", lambda text, model: [0.0] * embedder.EMBEDDING_DIMENSION)
        e = embedder._OllamaEmbedder("bge-m3:latest", fallback=False)
        e._ollama_available = True
        assert len(e.embed("short text")) == embedder.EMBEDDING_DIMENSION


class TestSelectiveRetry:
    def test_retries_on_eof_and_succeeds(self, monkeypatch):
        state = {"n": 0}

        def flaky(text, model):
            state["n"] += 1
            if state["n"] < 2:
                raise Exception('Post ".../tokenize": EOF (status code: 400)')
            return [0.0] * embedder.EMBEDDING_DIMENSION

        monkeypatch.setattr(embedder, "_embed_via_ollama", flaky)
        monkeypatch.setattr(embedder.time, "sleep", lambda s: None)
        e = embedder._OllamaEmbedder("bge-m3:latest", fallback=False)
        e._ollama_available = True
        assert len(e.embed("x")) == embedder.EMBEDDING_DIMENSION
        assert state["n"] == 2

    def test_does_not_retry_on_non_retryable_error(self, monkeypatch):
        state = {"n": 0}

        def failing(text, model):
            state["n"] += 1
            raise Exception("model 'llama3.1' not found (status code: 404)")

        monkeypatch.setattr(embedder, "_embed_via_ollama", failing)
        monkeypatch.setattr(embedder.time, "sleep", lambda s: None)
        e = embedder._OllamaEmbedder("bge-m3:latest", fallback=False)
        e._ollama_available = True
        try:
            e.embed("x")
            assert False, "expected raise"
        except Exception:
            pass
        assert state["n"] == 1

    def test_gives_up_after_max_attempts_on_persistent_eof(self, monkeypatch):
        state = {"n": 0}

        def always_eof(text, model):
            state["n"] += 1
            raise Exception("EOF")

        monkeypatch.setattr(embedder, "_embed_via_ollama", always_eof)
        monkeypatch.setattr(embedder.time, "sleep", lambda s: None)
        e = embedder._OllamaEmbedder("bge-m3:latest", fallback=False)
        e._ollama_available = True
        try:
            e.embed("x")
            assert False, "expected raise"
        except Exception:
            pass
        assert state["n"] == embedder._EMBED_MAX_ATTEMPTS


class TestIsRetryableOllamaError:
    def test_eof_is_retryable(self):
        assert embedder._is_retryable_ollama_error(Exception("... EOF ...")) is True

    def test_http_500_is_retryable(self):
        assert embedder._is_retryable_ollama_error(Exception("HTTP Error 500")) is True

    def test_timeout_is_retryable(self):
        assert embedder._is_retryable_ollama_error(Exception("Read timeout")) is True

    def test_model_not_found_is_not_retryable(self):
        assert embedder._is_retryable_ollama_error(Exception("model 'x' not found (status code: 404)")) is False


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
