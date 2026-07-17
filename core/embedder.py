"""
core/embedder.py — 임베딩 유틸리티 (안전한 import)

Primary backend : Ollama (BGE-M3, 다국어 강세 — config.yaml ollama.default_embed_model)
Fallback backend: sentence-transformers (all-mpnet-base-v2, legacy/경량)

이 모듈은 import 시점에 외부 의존성을 로드하지 않습니다.
첫 호출 시 필요한 백엔드를 지연 로드합니다.
"""

import json
import urllib.error
import urllib.request
import time
from sentence_transformers import SentenceTransformer

# Dimension validation for embedding consistency
from core.config import EMBEDDING_DIMENSION

# Custom exception for dimension mismatches
class DimensionMismatchError(Exception):
    """Raised when embedding dimension doesn't match expected dimension."""
    pass

_model = None
_model_load_failed = False
_MODEL_IMPORT_ERROR_MSG = (
    "sentence_transformers가 설치되지 않았습니다. pip install sentence-transformers"
)

_OLLAMA_HOST = "http://localhost:11434"
_OLLAMA_TIMEOUT_S = 30

# [CUE-20I ported from dbma.py RC-HOTFIX-02] Ollama's llama-server runner
# rejects inputs exceeding its fixed physical batch size; repeated
# rejection can kill the runner, and requests during its restart window
# fail with a raw "tokenize: EOF/timeout". This module only ever sends one
# text per request (no batching), so only the single-input size guard and
# selective retry apply here — see dbma.py::_embed_texts for the batching
# variant needed by callers that embed many texts in one request.
# [SPRINT20-I P2] 4 chars/token은 영어 기준 추정이라 한국어/헬라어/히브리어
# 신학 텍스트에서 실제 토큰을 과소평가한다(6511자 청크가 실제 ~3000 토큰).
# 그 결과 oversized 가드가 무력화되어 Ollama가 물리 batch(2048)를 초과한
# 입력에 HTTP 500을 반환하고, 반복 시 llama-server가 크래시했다(server.log
# "signal: killed"). 2 chars/token으로 보수화해 다국어 입력을 전송 전에 차단한다.
_APPROX_CHARS_PER_TOKEN = 2
_MAX_SAFE_EMBED_TOKENS = 1800
_RETRYABLE_ERROR_PATTERNS = ("eof", "connection", "timeout", "500")
_EMBED_MAX_ATTEMPTS = 3
_EMBED_BACKOFF_SECONDS = (1, 2, 4)


def _is_retryable_ollama_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(pattern in msg for pattern in _RETRYABLE_ERROR_PATTERNS)


def _get_model():
    """MiniLM(legacy) 모델을 지연 로딩합니다.

    로딩 실패(네트워크 차단, 모델 미설치 등)는 프로세스 수명 동안 고정
    (sticky)됩니다 — 실패할 때마다 매번 재시도하면 (예: huggingface_hub의
    재시도/백오프로 인해) 요청당 5초 이상 걸릴 수 있어, 이후 모든 호출이
    같은 실패를 반복하며 지연되는 것을 방지합니다.
    """
    global _model, _model_load_failed
    if _model_load_failed:
        raise RuntimeError(
            "MiniLM 모델 로딩이 이전에 실패했습니다 (이번 프로세스 동안 재시도하지 않음). "
            "네트워크/모델 캐시 상태를 확인한 뒤 프로세스를 재시작하십시오."
        )
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Use the model that provides 1024-dimensional embeddings for consistency
            # This ensures we're not mixing different dimension models
            _model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
        except ImportError:
            _model_load_failed = True
            raise ImportError(_MODEL_IMPORT_ERROR_MSG)
        except Exception as e:
            _model_load_failed = True
            raise RuntimeError(f"MiniLM 모델 로딩 실패: {e}") from e
    return _model


def embed(text: str):
    """텍스트를 임베딩 벡터로 변환합니다."""
    model = _get_model()
    embedding = model.encode(text)
    
    # Validate that the embedding has the expected dimension
    if len(embedding) != EMBEDDING_DIMENSION:
        raise DimensionMismatchError(
            f"임베딩 차원 불일치: 기대값 {EMBEDDING_DIMENSION}, 실제값 {len(embedding)}. "
            "모델이 예상과 다른 차원의 벡터를 생성했습니다. "
            "모델 변경 시 재인덱싱이 필요합니다."
        )
    return embedding


def _embed_via_ollama(text: str, model_name: str) -> list:
    """Ollama 서버(/api/embeddings)를 통해 BGE-M3 등으로 임베딩합니다."""
    estimated_tokens = len(text) // _APPROX_CHARS_PER_TOKEN if text else 0
    if estimated_tokens > _MAX_SAFE_EMBED_TOKENS:
        raise ValueError(
            f"임베딩 입력이 너무 큽니다(약 {estimated_tokens} 토큰 추정, "
            f"안전 한도 {_MAX_SAFE_EMBED_TOKENS} 토큰) — 청크 크기를 줄여 "
            f"다시 시도하세요. (chars={len(text)})"
        )
    # DEBUG: Log request details
    print("[OLLAMA EMBED REQUEST]")
    print(f"Request URL: {_OLLAMA_HOST}/api/embeddings")
    print(f"Model: {model_name}")
    print(f"Input Type: {type(text)}")
    print(f"Input Count: 1")
    print(f"First input length (char): {len(text) if text else 0}")
    print(f"Longest input length (char): {len(text) if text else 0}")
    print(f"Total characters: {len(text) if text else 0}")
    
    # Estimate token count (rough approximation)
    estimated_tokens = len(text) // 4 if text else 0  # Rough estimate
    print(f"Estimated tokens: {estimated_tokens}")
    
    payload = json.dumps({"model": model_name, "prompt": text}).encode("utf-8")
    print(f"JSON Payload Size (Bytes): {len(payload)}")
    print(f"HTTP Timeout: {_OLLAMA_TIMEOUT_S} seconds")
    
    req = urllib.request.Request(
        f"{_OLLAMA_HOST}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=_OLLAMA_TIMEOUT_S) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        
        elapsed_time = (time.time() - start_time) * 1000
        # DEBUG: Log response details
        print("[OLLAMA EMBED RESPONSE]")
        print(f"HTTP Status: {resp.getcode()}")
        print(f"Response Headers: {dict(resp.headers)}")
        print(f"Elapsed Time: {elapsed_time:.2f} ms")
        
        embedding = body.get("embedding")
        if not embedding:
            raise RuntimeError(f"Ollama 응답에 embedding 필드가 없습니다: {body}")
        return embedding
        
    except Exception as e:
        elapsed_time = (time.time() - start_time) * 1000
        # DEBUG: Log exception details
        print("[OLLAMA EMBED RESPONSE]")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {str(e)}")
        print(f"Elapsed Time: {elapsed_time:.2f} ms")
        # Print response body if available
        try:
            with urllib.request.urlopen(req, timeout=_OLLAMA_TIMEOUT_S) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                print(f"Response Body: {body}")
        except:
            pass  # Ignore if we can't read the body
        raise


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
            last_exc: Exception | None = None
            for attempt in range(1, _EMBED_MAX_ATTEMPTS + 1):
                try:
                    vector = _embed_via_ollama(text, self.model_name)
                    if len(vector) != EMBEDDING_DIMENSION:
                        raise DimensionMismatchError(
                            f"Ollama({self.model_name}) 임베딩 차원 불일치: "
                            f"기대값 {EMBEDDING_DIMENSION}, 실제값 {len(vector)}. "
                            "모델 설정을 확인하십시오 (재인덱싱 없이 벡터를 섞으면 "
                            "검색 컬렉션이 손상됩니다)."
                        )
                    return vector
                except (ValueError, DimensionMismatchError):
                    # oversized-input / dimension-mismatch — not transient, retrying
                    # or silently falling back to MiniLM won't fix a misconfigured
                    # embedding model, and would corrupt the vector store instead.
                    raise
                except Exception as e:
                    last_exc = e
                    if not _is_retryable_ollama_error(e) or attempt == _EMBED_MAX_ATTEMPTS:
                        break
                    time.sleep(_EMBED_BACKOFF_SECONDS[attempt - 1])
            if not self.fallback:
                raise last_exc
            print(f"[core.embedder] Ollama 임베딩 실패({last_exc}), MiniLM으로 폴백합니다.")
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