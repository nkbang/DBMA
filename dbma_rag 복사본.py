"""
dbma_rag.py — DBMA RAG 엔진
Qdrant 로컬 벡터 DB + fastembed MiniLM 임베딩

수정 사항:
  BUG-1  stats() 에서 컬렉션 미존재 예외 → try/except + _ensure_collection 보장
  BUG-2  stats 의 points_count: getattr 대신 client.count() 사용 (버전 무관)
  BUG-3  upsert 전 빈 텍스트 행 필터링
  BUG-4  embed 입력 타입 보장 (str 변환)
  BUG-5  빈 쿼리 IndexError 방어
  BUG-6  client.search() → client.query_points() (최신 qdrant-client 호환)
  BUG-7  build_context 의 'tota' 오타 수정 → NameError 제거
  NEW-1  3 단계 중복 방지 (ID 기반 upsert + doc_id+chunk_index + text_hash)
  NEW-2  duplicates_id, duplicates_hash 통계 추가
  NEW-3  text_hash 를 payload 에 자동 저장
  NEW-4  upsert_all_chunks() 누계 통계 (total_upserted, total_skipped, duplicates_id, duplicates_hash, dedup_ratio)
  NEW-5  stats() 에 indexed_chunks, jsonl_total_chunks, dedup_ratio 지표 추가
"""

import logging
import os
import json
import uuid
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

BASE_DIR            = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR  = BASE_DIR / "data" / "제련완성본"
DEFAULT_QDRANT_DIR  = BASE_DIR / "storage" / "qdrant_storage"
COLLECTION_NAME     = "dbma_chunks"
EMBEDDING_MODEL     = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_SIZE         = 384
DISTANCE            = models.Distance.COSINE


def _compute_text_hash(text: str) -> str:
    """청크 텍스트 SHA256 해시 (중복 방지용)"""
    return hashlib.sha256((text or "").strip().encode()).hexdigest()


class DBMARag:
    def __init__(
        self,
        output_dir: "str | os.PathLike" = DEFAULT_OUTPUT_DIR,
        qdrant_dir: "str | os.PathLike" = DEFAULT_QDRANT_DIR,
        collection_name: str = COLLECTION_NAME,
        embedding_model: str = EMBEDDING_MODEL,
    ):
        self.output_dir       = Path(output_dir)
        self.qdrant_dir       = Path(qdrant_dir)
        self.collection_name  = collection_name
        self.embedding_model  = embedding_model

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.qdrant_dir.mkdir(parents=True, exist_ok=True)

        self.client   = QdrantClient(path=str(self.qdrant_dir))
        self.embedder = TextEmbedding(model_name=self.embedding_model)
        self._ensure_collection()

    # ─── 컬렉션 보장 ──────────────────────────────────────────
    def _ensure_collection(self) -> None:
        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection_name in existing:
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=DISTANCE),
        )
        for field, schema in [
            ("doc_id",       models.PayloadSchemaType.KEYWORD),
            ("source_type",  models.PayloadSchemaType.KEYWORD),
            ("source_name",  models.PayloadSchemaType.KEYWORD),
            ("chunk_index",  models.PayloadSchemaType.INTEGER),
            ("text_hash",    models.PayloadSchemaType.KEYWORD),
        ]:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field,
                field_schema=schema,
            )

    # ─── JSONL 유틸 ──────────────────────────────────────────
    def _iter_chunk_files(self) -> List[Path]:
        return sorted(self.output_dir.glob("*_chunks.jsonl"))

    def _load_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"[JSONL] {path.name} 라인 {i} 파싱 실패: {e}")
        return rows

    # ─── 페이로드 빌더 ──────────────────────────────────────
    def _build_payload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "doc_id":         row.get("doc_id"),
            "chunk_id":       row.get("chunk_id"),
            "stem":           row.get("stem"),
            "source_name":    row.get("source_name"),
            "source_type":    row.get("source_type"),
            "chunk_index":    row.get("chunk_index"),
            "total_chunks":   row.get("total_chunks"),
            "char_count":     row.get("char_count"),
            "token_estimate": row.get("token_estimate"),
            "language":       row.get("language", {}),
            "anchors":        row.get("anchors", {}),
            "quality":        row.get("quality", {}),
            "text":           row.get("text", ""),
            "text_hash":      row.get("text_hash"),
            "created_at":     row.get("created_at"),
        }

    # ─── 임베딩 ─────────────────────────────────────────────
    def _embed_documents(self, texts: List[str]) -> List[List[float]]:
        # BUG-4 fix: 빈 문자열·None 방어, 반드시 str 변환
        safe = [str(t) if t else " " for t in texts]
        return [list(vec) for vec in self.embedder.embed(safe)]

    def _embed_query(self, query: str) -> List[float]:
        # BUG-5 fix: 빈 쿼리 방어
        q = query.strip() or " "
        results = list(self.embedder.query_embed(q))
        if not results:
            raise ValueError("쿼리 임베딩 생성 실패: 빈 결과")
        return list(results[0])

    # ─── 컬렉션 리셋 ─────────────────────────────────────────
    def reset_collection(self) -> None:
        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection_name in existing:
            self.client.delete_collection(self.collection_name)
        self._ensure_collection()

    # ─── 단일 JSONL 업서트 (3 단계 중복 방지) ──────────────────
    def upsert_chunks_from_file(self, jsonl_path: "str | os.PathLike") -> Dict[str, Any]:
        """
        수정된 버전: 3 단계 중복 방지
          ① ID 기반 upsert (기본 대체)
          ② doc_id + chunk_index 인메모리 중복 체크
          ③ text_hash 기반 Qdrant 중복 체크 (선택)
        """
        path = Path(jsonl_path)
        rows = self._load_jsonl(path)
        if not rows:
            return {
                "file": str(path),
                "upserted": 0,
                "skipped": 0,
                "duplicates_id": 0,
                "duplicates_hash": 0,
            }

        # ── 1) 빈 텍스트 + eligible=False 필터링 ───────────────────────
        valid_rows = [
            r for r in rows
            if (r.get("text") or "").strip()
            and r.get("indexing", {}).get("eligible", True)
        ]
        skipped_base = len(rows) - len(valid_rows)
        if not valid_rows:
            return {
                "file": str(path),
                "upserted": 0,
                "skipped": skipped_base,
                "duplicates_id": 0,
                "duplicates_hash": 0,
            }

        # ── 2) doc_id + chunk_index 인메모리 중복 체크 ──────────────────
        seen_doc_chunk = set()
        duplicates_id = 0
        filtered_rows = []

        for row in valid_rows:
            doc_id = row.get("doc_id")
            chunk_index = row.get("chunk_index")

            if doc_id and chunk_index:
                key = f"{doc_id}_{chunk_index}"
                if key in seen_doc_chunk:
                    duplicates_id += 1
                    continue
                seen_doc_chunk.add(key)

            filtered_rows.append(row)

        if duplicates_id:
            logger.warning(f"[UPSERT] {path.name}: {duplicates_id}개 doc_id+chunk_index 중복 스킵")

        # ── 3) text_hash 기반 Qdrant 중복 체크 (선택) ───────────────────
        duplicates_hash = 0
        final_rows = []

        for row in filtered_rows:
            text_hash = row.get("text_hash") or _compute_text_hash(row.get("text", ""))

            # text_hash 가 이미 컬렉션에 존재하는지 확인
            try:
                result = self.client.query_points(
                    collection_name=self.collection_name,
                    query_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="text_hash",
                                match=models.MatchText(text=text_hash)
                            )
                        ]
                    ),
                    limit=1,
                    with_payload=False,
                )
                if len(result.points) > 0:
                    duplicates_hash += 1
                    continue
            except Exception as e:
                logger.warning(f"[UPSERT] {path.name}: text_hash 체크 실패: {e}")

            final_rows.append(row)

        if duplicates_hash:
            logger.warning(f"[UPSERT] {path.name}: {duplicates_hash}개 text_hash 중복 스킵")

        # ── 4) 임베딩 + 업서트 ───────────────────────────────────────────
        if not final_rows:
            return {
                "file": str(path),
                "upserted": 0,
                "skipped": skipped_base + duplicates_id + duplicates_hash,
                "duplicates_id": duplicates_id,
                "duplicates_hash": duplicates_hash,
            }

        texts   = [row["text"] for row in final_rows]
        vectors = self._embed_documents(texts)

        points: List[models.PointStruct] = []
        for row, vector in zip(final_rows, vectors):
            # text_hash 를 메타데이터에 추가
            text_hash = row.get("text_hash") or _compute_text_hash(row.get("text", ""))
            payload = self._build_payload(row)
            payload["text_hash"] = text_hash  # ← 추가

            cid = row.get("chunk_id") or str(uuid.uuid4())
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, cid))

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            wait=True,
            points=points,
        )

        return {
            "file":           str(path),
            "upserted":       len(points),
            "skipped":        skipped_base + duplicates_id + duplicates_hash,
            "duplicates_id":  duplicates_id,
            "duplicates_hash": duplicates_hash,
            "doc_id":         final_rows[0].get("doc_id"),
            "source_name":    final_rows[0].get("source_name"),
        }

    # ─── 전체 JSONL 업서트 (누계 통계 포함) ───────────────────────
    def upsert_all_chunks(self) -> List[Dict[str, Any]]:
        """
        수정된 버전: 누계 통계 추가
          - total_upserted: 새로 인덱스된 총 청크
          - total_skipped: 스킵된 총 청크 (빈 텍스트 + 중복)
          - duplicates_id: doc_id+chunk_index 중복
          - duplicates_hash: text_hash 중복
          - dedup_ratio: 중복 제거율 (%)
        """
        files = self._iter_chunk_files()
        if not files:
            logger.warning("[UPSERT_ALL] 청크 JSONL 파일 없음")
            return []
        
        results = []
        total_upserted = 0
        total_skipped = 0
        total_duplicates_id = 0
        total_duplicates_hash = 0
        
        for path in files:
            try:
                result = self.upsert_chunks_from_file(path)
                results.append(result)
                
                # 누계 계산
                total_upserted += result.get("upserted", 0)
                total_skipped += result.get("skipped", 0)
                total_duplicates_id += result.get("duplicates_id", 0)
                total_duplicates_hash += result.get("duplicates_hash", 0)
                
            except Exception as e:
                logger.error(f"[UPSERT_ALL] {path.name} 실패: {e}", exc_info=True)
                results.append({"file": str(path), "upserted": 0, "error": str(e)})
        
        # ── 누계 결과 추가 ────────────────────────────────────────────
        total_input = total_upserted + total_duplicates_id + total_duplicates_hash + total_skipped
        dedup_ratio = (total_duplicates_id + total_duplicates_hash) / max(total_input, 1)
        
        results.append({
            "summary": True,
            "total_upserted":     total_upserted,
            "total_skipped":      total_skipped,
            "duplicates_id":      total_duplicates_id,
            "duplicates_hash":    total_duplicates_hash,
            "dedup_ratio":        dedup_ratio,
            "dedup_ratio_pct":    f"{dedup_ratio * 100:.1f}%",
        })
        
        return results

    # ─── 검색 ───────────────────────────────────────────────
    def search(
        self,
        query: str,
        limit: int = 5,
        source_type: Optional[str] = None,
        doc_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query_vector = self._embed_query(query)

        conditions = []
        if source_type:
            conditions.append(
                models.FieldCondition(key="source_type", match=models.MatchValue(value=source_type))
            )
        if doc_id:
            conditions.append(
                models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))
            )
        query_filter = models.Filter(must=conditions) if conditions else None

        # BUG-6 fix: client.search() deprecated → query_points() 사용
        # qdrant-client 구버전 호환을 위해 양쪽 시도
        try:
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                with_payload=True,
                limit=limit,
            )
            hits = response.points
        except AttributeError:
            # 구버전 fallback
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                with_payload=True,
                limit=limit,
            )

        results = []
        for hit in hits:
            payload = hit.payload or {}
            results.append({
                "score":       hit.score,
                "doc_id":      payload.get("doc_id"),
                "chunk_id":    payload.get("chunk_id"),
                "source_name": payload.get("source_name"),
                "source_type": payload.get("source_type"),
                "chunk_index": payload.get("chunk_index"),
                "text":        payload.get("text", ""),
                "anchors":     payload.get("anchors", {}),
                "quality":     payload.get("quality", {}),
            })
        return results

    # ─── 통계 (인덱스 지표 포함) ────────────────────────────────────
    def stats(self) -> Dict[str, Any]:
        """
        수정된 버전: 인덱스 지표 추가
          - indexed_chunks: 현재 Qdrant 에 인덱스된 청크 총수
          - jsonl_total_chunks: JSONL 파일 총 청크 수
          - dedup_ratio: JSONL 대비 실제 인덱스 비율
        """
        # BUG-1, BUG-2 fix: 컬렉션 존재 보장 + client.count() 로 포인트 수 정확히 조회
        self._ensure_collection()
        try:
            points_count = self.client.count(
                collection_name=self.collection_name,
                exact=True,
            ).count
        except Exception as e:
            logger.warning(f"[STATS] count 조회 실패: {e}")
            points_count = None

        local_files = self._iter_chunk_files()
        
        # JSONL 총 청크 수 계산
        jsonl_total = sum(len(self._load_jsonl(f)) for f in local_files)
        
        # 인덱스 비율 계산
        indexed_chunks = points_count or 0
        dedup_ratio = (jsonl_total - indexed_chunks) / max(jsonl_total, 1)
        
        return {
            "collection_name":      self.collection_name,
            "embedding_model":      self.embedding_model,
            "vector_size":          VECTOR_SIZE,
            "points_count":         points_count,
            "chunks_jsonl_files":   len(local_files),
            "output_dir":           str(self.output_dir),
            "qdrant_dir":           str(self.qdrant_dir),
            # ── 신규 지표 ────────────────────────────────────────────
            "indexed_chunks":       indexed_chunks,
            "jsonl_total_chunks":   jsonl_total,
            "dedup_ratio":          dedup_ratio,
            "dedup_ratio_pct":      f"{dedup_ratio * 100:.1f}%",
        }


# ─── 컨텍스트 빌더 ─────────────────────────────────────────
def build_context(results: List[Dict[str, Any]], max_chars: int = 4000) -> str:
    """검색 결과를 LLM 입력용 컨텍스트 문자열로 조립."""
    parts: List[str] = []
    total = 0  # BUG-7 fix: 'tota' 오타 수정 → NameError 제거
    for i, item in enumerate(results, start=1):
        block = (
            f"[{i}] {item.get('source_name', '?')} | chunk {item.get('chunk_index', '?')}\n"
            f"{(item.get('text') or '').strip()}\n"
        )
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts).strip()