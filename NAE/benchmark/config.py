"""NAE Benchmark Configuration — 닫힌 vocabulary 상수.

TASK 2 (C1-TASK-ORDER-037):
- THEOLOGY_AREA_CATEGORIES: NAE/pipeline/tsu/config.py DOCTRINE_CATEGORIES import 별칭
- QUESTION_TYPES / DIFFICULTY_LEVELS / REVIEW_STATUSES 도 여기서 관리 (schema.py 에서 import)

중요: theology_area 값은 반드시 DOCTRINE_CATEGORIES를 import해서 참조할 것.
값을 복사하면 나중에 한쪽만 갱신되는 사고가 발생할 수 있음.
"""

from __future__ import annotations

# ------------------------------------------------------------------
# theology_area — DOCTRINE_CATEGORIES import 별칭 (값 복사 금지)
# ------------------------------------------------------------------
from NAE.pipeline.tsu.config import DOCTRINE_CATEGORIES as THEOLOGY_AREA_CATEGORIES

__all__ = [
    "THEOLOGY_AREA_CATEGORIES",
]
