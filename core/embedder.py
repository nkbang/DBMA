"""
core/embedder.py — 임베딩 유틸리티 (안전한 import)

Primary backend : Ollama (BGE-M3, 다국어 강세 — config.yaml ollama.default_embed_model)
Fallback backend: sentence-transformers (all-MiniLM-L6-v2, legacy/경량)

이 모듈은 import 시점에 외부 의존성을 로드하지 않습니다.
첫 호출 시 필요한 백엔드를 지연 로드합니다.
"""

import json
import urllib.error
import urllib.request

_model = None
_MODEL_IMPORT_ERROR_MSG = (
    "sentence_transformers가 설치되지 않았습니다. pip install sentence-transformers"
)

_OLLAMA_HOST = "http://localhost:11434"
_OLLAMA_TIMEOUT_S = 30


def _get_model():
    """MiniLM(legacy) 모델을 지연 로딩합니다."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            raise ImportError(_MODEL_IMPORT_ERROR_MSG)
    return _model


def embed(text: str):
    """텍스트를 임베딩 벡터로 변환합니다 (legacy 경로: MiniLM, sentence-transformers)."""
    model = _get_model()
    return model.encode(text).tolist()


def _embed_via_ollama(text: str, model_name: str) -> list:
    """Ollama 서버(/api/embeddings)를 통해 BGE-M3 등으로 임베딩합니다."""
    payload = json.dumps({"model": model_name, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{_OLLAMA_HOST}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_OLLAMA_TIMEOUT_S) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    embedding = body.get("embedding")
    if not embedding:
        raise RuntimeError(f"Ollama 응답에 embedding 필드가 없습니다: {body}")
    return embedding


class _OllamaEmbedder:
    """BGE-M3(Ollama) 우선 임베더. Ollama 접속 불가 시 MiniLM으로 폴백합니다."""

    def __init__(self, model_name: str, fallback: bool = True):
        self.model_name = model_name
        self.fallback = fallback
        self._ollama_available = None

    def _check_ollama(self) -> bool:
        if self._ollama_available is not None:
            return self._ollama_available
        try:
            req = urllib.request.Request(f"{_OLLAMA_HOST}/api/tags", method="GET")
            urllib.request.urlopen(req, timeout=3)
            self._ollama_available = True
        except (urllib.error.URLError, OSError):
            self._ollama_available = False
        return self._ollama_available

    def embed(self, text: str) -> list:
        if self._check_ollama():
            try:
                return _embed_via_ollama(text, self.model_name)
            except Exception as e:
                if not self.fallback:
                    raise
                print(f"[core.embedder] Ollama 임베딩 실패({e}), MiniLM으로 폴백합니다.")
        if not self.fallback:
            raise RuntimeError(
                f"Ollama({_OLLAMA_HOST})에 연결할 수 없고 fallback=False로 설정되어 있습니다."
            )
        return embed(text)

    def encode(self, text: str, normalize_embeddings: bool = False) -> list:
        """임베딩을 반환합니다. (rag_benchmark.py 호환성을 위한 encode 메서드)

        Args:
            text: 임베딩할 텍스트
            normalize_embeddings: 벡터 정규화 여부 (MiniLM 경로에서만 지원)
        """
        vec = self.embed(text)
        if normalize_embeddings:
            norm = (sum(v ** 2 for v in vec) ** 0.5) or 1.0
            vec = [v / norm for v in vec]
        return vec

    def __call__(self, text: str) -> list:
        return self.embed(text)


def get_embedder(model_name=None, fallback: bool = True) -> "_OllamaEmbedder":
    """프로덕션 임베더를 반환합니다.

    Args:
        model_name: Ollama 모델명. None이면 config.yaml의
            ollama.default_embed_model(기본 "bge-m3:latest")을 사용합니다.
        fallback: Ollama 접속 실패 시 MiniLM으로 자동 폴백할지 여부.
            벤치마크처럼 백엔드를 고정해 비교해야 하는 경우 False로 설정해
            조용한 폴백을 방지하십시오.
    """
    if model_name is None:
        try:
            from core.config import DEFAULT_EMBED_MODEL
            model_name = DEFAULT_EMBED_MODEL
        except ImportError:
            model_name = "bge-m3:latest"
    return _OllamaEmbedder(model_name=model_name, fallback=fallback)