"""ParagraphResolver — 검색 히트를 canonical.json 원문 문단 전체로 확장한다.

[PM 정렬 감사 선결 #4 / 옵션 A — 문단 앵커드 근거]
설계: docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DESIGN_v1.md §4.4.1
Task Order: docs/NAE_PARAGRAPH_ANSWER_DELIVERY_IMPL_TASK_ORDER_001.md §2-1

TSU/Qdrant payload는 `(identifier, paragraph)`를 이미 상주시킨다
(NAE/pipeline/index/qdrant_store.py:41-88). 이 모듈은 그 두 값으로
`NAE/corpus/canonical/<identifier>/canonical.json`에서 원문 문단을 되찾는다.
검색·임베딩·인덱스·`builder_version`은 건드리지 않는다 — 읽기 전용.

복원 알고리즘은 신규가 아니다: `NAE/pipeline/verify/consistency.py:44-49`가
이미 build-time과 무관하게 canonical.json에서 문단을 재도출한다. 이 모듈은
그 패턴에 identifier 단위 캐시와 fail-soft 폴백을 더한 것이다.
"""
from __future__ import annotations

import functools
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from NAE.pipeline.tsu import config as tsu_config

logger = logging.getLogger("nae.paragraph_lookup")


@dataclass
class ResolvedParagraph:
    """canonical.json에서 되찾은 원문 문단 (또는 이웃 문단 묶음)."""

    text: str
    index: int
    page_start: int | None = None
    page_end: int | None = None
    scripture_references: list = field(default_factory=list)
    canonical_version: str = ""
    neighbor_indices: list[int] = field(default_factory=list)


@functools.lru_cache(maxsize=32)
def _load_canonical_index(identifier: str, canonical_root_str: str) -> dict[int, dict] | None:
    """identifier 단위로 canonical.json을 1회 파싱해 {paragraph_index: paragraph}
    dict로 만들어 캐시한다. 파일이 없으면 None.

    canonical_root를 문자열로 받는 이유: lru_cache 키는 hashable이어야 하고
    Path도 hashable이지만, 호출부가 매번 같은 Path 객체를 넘긴다는 보장이
    없어 문자열로 정규화한다.
    """
    path = Path(canonical_root_str) / identifier / "canonical.json"
    if not path.exists():
        logger.warning("[paragraph_lookup] canonical.json 없음: %s", path)
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("[paragraph_lookup] canonical.json 파싱 실패 %s: %s", path, exc)
        return None

    index: dict[int, dict] = {}
    for para in data.get("paragraphs", []):
        idx = para.get("index")
        if isinstance(idx, int):
            # pipeline_version을 문단마다 달아 두면 호출부가 canonical.json을
            # 다시 열지 않고도 canonical_version 대조를 할 수 있다.
            para = dict(para)
            para["_pipeline_version"] = str(data.get("pipeline_version", ""))
            index[idx] = para
    return index or None


def resolve(
    identifier: str,
    paragraph_index: int,
    *,
    canonical_root: Path | None = None,
    neighbors: int = 0,
    expected_canonical_version: str | None = None,
) -> ResolvedParagraph | None:
    """`(identifier, paragraph_index)` → 원문 문단.

    Parameters
    ----------
    identifier:
        TSU/payload의 `identifier` (canonical 디렉터리 이름).
    paragraph_index:
        payload의 `paragraph` 값.
    canonical_root:
        기본 `NAE/pipeline/tsu/config.CANONICAL_ROOT`. 테스트가 override.
    neighbors:
        0이면 단일 문단. n>0이면 `index-n … index+n` 문단 text를 `\\n\\n`으로
        이어 붙인다(같은 identifier 내, 범위 밖 인덱스는 건너뜀).
        `NAE_PARAGRAPH_NEIGHBORS` 튜닝 옵션의 값이 여기로 온다.
    expected_canonical_version:
        payload의 `canonical_version`. 주면 canonical.json의 `pipeline_version`과
        대조해 다르면 None을 반환한다(가정 1 — TSU 빌드 이후 canonical 재빌드).

    Returns
    -------
    ResolvedParagraph 또는 None (파일 부재 / 인덱스 부재 / 버전 불일치).
    실패는 로그만 남기고 예외를 전파하지 않는다 (ADR-024 §G fail-closed 정합).
    """
    if not identifier or paragraph_index is None:
        return None

    root = canonical_root or tsu_config.CANONICAL_ROOT
    para_index = _load_canonical_index(identifier, str(root))
    if para_index is None:
        return None

    base = para_index.get(paragraph_index)
    if base is None:
        logger.warning(
            "[paragraph_lookup] 문단 인덱스 없음: identifier=%s paragraph=%s",
            identifier, paragraph_index,
        )
        return None

    canonical_version = base.get("_pipeline_version", "")
    if (
        expected_canonical_version is not None
        and canonical_version
        and str(expected_canonical_version) != canonical_version
    ):
        logger.warning(
            "[paragraph_lookup] canonical_version 불일치: identifier=%s "
            "payload=%s canonical.json=%s",
            identifier, expected_canonical_version, canonical_version,
        )
        return None

    if neighbors and neighbors > 0:
        picked: list[dict] = []
        used: list[int] = []
        for i in range(paragraph_index - neighbors, paragraph_index + neighbors + 1):
            p = para_index.get(i)
            if p is not None:
                picked.append(p)
                used.append(i)
        text = "\n\n".join(p.get("text", "") for p in picked).strip()
        scripture_refs: list = []
        for p in picked:
            scripture_refs.extend(p.get("scripture_references", []) or [])
        pages = [p.get("page_start") for p in picked if p.get("page_start") is not None]
        page_ends = [p.get("page_end") for p in picked if p.get("page_end") is not None]
        return ResolvedParagraph(
            text=text,
            index=paragraph_index,
            page_start=min(pages) if pages else None,
            page_end=max(page_ends) if page_ends else None,
            scripture_references=scripture_refs,
            canonical_version=canonical_version,
            neighbor_indices=used,
        )

    return ResolvedParagraph(
        text=base.get("text", "").strip(),
        index=paragraph_index,
        page_start=base.get("page_start"),
        page_end=base.get("page_end"),
        scripture_references=base.get("scripture_references", []) or [],
        canonical_version=canonical_version,
        neighbor_indices=[paragraph_index],
    )


def clear_cache() -> None:
    """테스트에서 canonical_root를 바꿔 가며 검증할 때 캐시를 비운다."""
    _load_canonical_index.cache_clear()
