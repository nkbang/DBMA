"""core/neighbor_index.py — ADR-034 이웃 청크 색인 (문장 창 확장의 공용 토대).

[J2, 2026-10-18] 이 모듈은 새 기능이 아니다. `core/retrieval.py::RetrievalEngine`
안에만 있던 ADR-034 이웃 색인 로직을 **그대로** 꺼낸 것이다.

왜 꺼냈는가 — 실측으로 드러난 구멍:

2026-09-18에 `USE_INVERTED_INDEX` 기본값이 `true`로 바뀌면서 프로덕션 질의는
`HybridQueryProcessor`를 탄다. 그런데 그 경로는
`ContextAssembler.assemble(candidates[:k], parsed_query)`를 **이웃 확장 인자
없이** 호출한다(`core/hybrid_candidate_pipeline.py:560`). 즉 Approved ADR-034의
문장 창 확장이 그날부터 사실상 비활성이었다. 실측(2026-10-18, 한국어 질의 4건
19블록): 근거 블록의 문장 종결률 **52.6%** — 같은 코드를 직접 호출한
시뮬레이션에서는 99.5%였다. 차이의 원인이 이 미배선이다.

`HybridQueryProcessor`는 `RetrievalEngine`을 만들지 않고 `_EngineCompat`
(이미 로드된 `tsu_by_id` 재사용)만 둔다. 그래서 이웃 색인을 양쪽에서 쓰려면
둘 중 하나가 필요했다 — 로직 복제(두 곳이 언젠가 어긋난다) 또는 공용 추출.
후자를 택했다.

동작·반환값은 종전 `RetrievalEngine.get_neighbor_context()`와 동일하다.
랭킹·스코어링·citation·임베딩에 영향이 없고, TSU 스키마도 건드리지 않는다
(`document_id`/`chunk_id`는 `core/tsu_builder.py`가 이미 넣는 필드다).
"""

from __future__ import annotations

from typing import Any, Optional


class NeighborIndex:
    """document_id → 문서 순서의 chunk_id 목록, chunk_id → TSU 인덱스.

    TSU 레코드 목록에 대해 읽기 전용이다. 목록을 복사하지 않고 참조만 들고
    있으므로(코퍼스는 로드 후 불변) 메모리 비용은 색인 두 개뿐이다.
    """

    def __init__(self, tsus: list[dict[str, Any]]) -> None:
        self._tsus = tsus
        self._chunk_id_to_idx: dict[str, int] = {}
        self._doc_chunk_order: dict[str, list[str]] = {}
        for idx, tsu in enumerate(tsus):
            chunk_id = tsu.get("chunk_id")
            if not chunk_id:
                continue
            self._chunk_id_to_idx[chunk_id] = idx
            document_id = tsu.get("document_id")
            if document_id:
                self._doc_chunk_order.setdefault(document_id, []).append(chunk_id)

    def neighbors(
        self, candidate_metadata: dict[str, Any], num_neighbors: int = 1
    ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """(before, after) — 같은 문서 안에서 바로 앞/뒤 청크의
        (chunk_id, content)를 문서 순서로 최대 num_neighbors개씩 돌려준다.

        문서 경계·단일 청크 문서·알 수 없는 chunk_id/document_id에서는 빈
        목록이다. 예외를 던지지 않는다("모르면 비워둔다").
        """
        document_id = candidate_metadata.get("document_id")
        chunk_id = candidate_metadata.get("chunk_id")
        if not document_id or not chunk_id or num_neighbors <= 0:
            return [], []
        order = self._doc_chunk_order.get(document_id)
        if not order:
            return [], []
        try:
            pos = order.index(chunk_id)
        except ValueError:
            return [], []

        def _lookup(chunk_pos: int) -> Optional[tuple[str, str]]:
            neighbor_id = order[chunk_pos]
            neighbor_idx = self._chunk_id_to_idx.get(neighbor_id)
            if neighbor_idx is None:
                return None
            return neighbor_id, self._tsus[neighbor_idx].get("content", "")

        before = [
            hit
            for offset in range(num_neighbors, 0, -1)
            if (npos := pos - offset) >= 0
            and (hit := _lookup(npos)) is not None
        ]
        after = [
            hit
            for offset in range(1, num_neighbors + 1)
            if (npos := pos + offset) < len(order)
            and (hit := _lookup(npos)) is not None
        ]
        return before, after
