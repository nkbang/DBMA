"""
core/embedder.py — 임베딩 유틸리티 (안전한 import)

이 모듈은 import 시점에 외부 의존성을 로드하지 않습니다.
첫 embed() 호출 시 sentence_transformers를 지연 로드합니다.
"""

_model = None
_MODEL_IMPORT_ERROR_MSG = (
    "sentence_transformers가 설치되지 않았습니다. pip install sentence-transformers"
)


def _get_model():
    """모델을 지연 로딩합니다."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError as e:
            raise ImportError(_MODEL_IMPORT_ERROR_MSG)
    return _model


def embed(text: str):
    """텍스트를 임베딩 벡터로 변환합니다."""
    model = _get_model()
    return model.encode(text).tolist()
