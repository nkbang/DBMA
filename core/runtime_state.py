"""core/runtime_state.py — Pipeline Runtime State Reader

Dashboard Processing Pipeline Status를 위한 런타임 상태 판독기.

데이터원:
  1. logs/project_events.jsonl  — 처리 이벤트 로그 (parse/clean/chunk 완료)
  2. output/{output_dir}/.batch_state.json  — BatchState (처리된 파일 목록)
  3. output/tsu/tsu_dataset.json  — TSU 데이터셋 존재 여부 (임베딩/인덱싱 상태)
  4. chroma_db persist directory — 벡터DB 인덱스 존재 여부

Pipeline 단계:
  extract → chunk → embedding → indexing → search

각 단계의 상태는 "pending", "active", "complete" 중 하나이며,
진행률(progress)은 이벤트 수와 파일 수 기반 계산.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from core.config import DEFAULT_TSU_MANIFEST_PATH


# ── 데이터 모델 ─────────────────────────────────────────────

class PipelineStageState:
    """단일 파이프라인 단계 상태."""
    
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    
    def __init__(self, stage: str, status: str, progress: int, detail: str = "") -> None:
        self.stage = stage
        self.status = status
        self.progress = progress
        self.detail = detail
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "progress": self.progress,
            "detail": self.detail,
        }


# ── 이벤트 로그 판독 ───────────────────────────────────────

def _read_event_log(log_path: Path) -> list[dict]:
    """project_events.jsonl에서 이벤트를 읽는다."""
    if not log_path.exists():
        return []
    try:
        events = []
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events
    except Exception:
        return []


def _count_events_by_type(events: list[dict], event_prefix: str) -> int:
    """이벤트 타입별 개수를 세고, 완료 상태인 것만 필터."""
    count = 0
    for e in events:
        evt = e.get("event", "")
        if evt.startswith(event_prefix) and e.get("status") == "DONE":
            count += 1
    return count


# ── BatchState 판독 ────────────────────────────────────────

def _load_batch_state(output_dir: Path) -> Dict[str, Any]:
    """.batch_state.json을 로드한다. 없으면 빈 딕셔너리."""
    state_file = output_dir / ".batch_state.json"
    if not state_file.exists():
        return {}
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        return {
            "processed": data.get("processed", []),
            "failed": data.get("failed", []),
            "timestamp": data.get("timestamp", ""),
        }
    except Exception:
        return {}


# ── TSU 데이터셋 판독 ─────────────────────────────────────

def _read_tsu_manifest(output_dir: Path) -> Dict[str, Any]:
    """TSU manifest(output/bench/tsu_manifest.json) 기반 상태 판독.

    [SPRINT17-RG-6B] output/tsu/tsu_dataset.json 경로는 어떤 생산자도 쓴 적이
    없는 obsolete 경로였다(SPRINT17-RG-1/RG-2에서 확인). scripts/build_tsu_dataset.py
    (SPRINT17-RG-6A)가 실제로 쓰는 manifest를 정본으로 삼는다.
    RetrievalEngine을 인스턴스화하지 않고 manifest 파일만 읽는다.
    """
    # [FIX] bench 경로는 config authority(DEFAULT_TSU_MANIFEST_PATH,
    # 기본 output/bench)로 고정 — output_dir(예: data/제련완성본)에서 파생하면
    # 실제 manifest 위치와 어긋나 임베딩 단계가 30%로 오표시된다.
    manifest_path = Path(DEFAULT_TSU_MANIFEST_PATH)
    status: Dict[str, Any] = {
        "manifest_exists": False,
        "generated_at": None,
        "tsu_count": 0,
        "source_document_count": 0,
    }
    if not manifest_path.exists():
        return status
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return status

    status["manifest_exists"] = True
    status["generated_at"] = data.get("generated_at")
    status["tsu_count"] = data.get("tsu_count", 0)
    status["source_document_count"] = data.get("source_document_count", 0)
    return status


def _check_tsu_dataset(output_dir: Path) -> tuple[bool, int]:
    """TSU 데이터셋 존재 여부 + TSU 개수.

    [SPRINT17-RG-6B] 함수 시그니처(반환 타입 tuple[bool, int])는 하위 호환을
    위해 그대로 유지한다. 내부 조회 경로만 obsolete했던
    output/tsu/tsu_dataset.json에서 _read_tsu_manifest()로 교체했다.
    """
    status = _read_tsu_manifest(output_dir)
    exists = status["manifest_exists"] and status["generated_at"] is not None
    return exists, status["tsu_count"]


# ── 벡터DB 인덱스 판독 ─────────────────────────────────────

def _check_vector_index(base_dir: Path) -> bool:
    """ChromaDB 인덱스 존재 여부."""
    chroma_dirs = [
        base_dir / "chroma_db",
        base_dir / "VectorDB",
    ]
    for d in chroma_dirs:
        if d.exists() and any(d.rglob("*")):
            return True
    return False


def get_index_size_bytes(base_dir: Optional[Path] = None) -> int:
    """벡터 인덱스(ChromaDB persist directory) 실제 디스크 사용량.

    core.config.CHROMA_PERSIST_DIR(기본 "chroma_db")를 그대로 신뢰한다 —
    Monitor 페이지의 "인덱스 크기" 카드가 하드코딩된 "156MB" 대신 이 값을
    쓴다.
    """
    from core.config import CHROMA_PERSIST_DIR

    if base_dir is None:
        base_dir = Path.cwd()
    index_dir = base_dir / CHROMA_PERSIST_DIR
    if not index_dir.is_dir():
        return 0
    return sum(f.stat().st_size for f in index_dir.rglob("*") if f.is_file())


def get_processing_throughput(
    event_log_path: Optional[Path] = None,
    idle_gap_threshold_sec: float = 60.0,
) -> Optional[Dict[str, Any]]:
    """최근 문서 처리 배치의 실측 처리 속도(파일/초).

    logs/project_events.jsonl은 여러 날에 걸친 개별 실행을 전부
    run_id="manual" 하나로 뭉쳐 기록한다 — 첫 이벤트~마지막 이벤트 구간을
    그대로 나누면 세션 사이 유휴 시간(최대 20시간+)까지 "처리 시간"으로
    잡혀 사실상 0에 가까운 값이 나온다(Preflight로 확인: 0.00035파일/초).
    연속 이벤트 간격이 idle_gap_threshold_sec 이하인 구간만 "활동 시간"으로
    합산해 유휴 구간을 제외한다.

    Returns:
        {"files_per_sec": float, "as_of": str} — 계산 불가(이벤트 부족/활동
        시간 0) 시 None. as_of는 마지막 이벤트 시각으로, 이 수치가 실시간이
        아니라 "그 시점 기준 스냅샷"임을 UI에서 명시하기 위함이다.
    """
    from datetime import datetime

    if event_log_path is None:
        event_log_path = Path.cwd() / "logs" / "project_events.jsonl"

    events = [e for e in _read_event_log(event_log_path) if e.get("ts")]
    if len(events) < 2:
        return None

    events.sort(key=lambda e: e["ts"])
    active_time = 0.0
    for i in range(1, len(events)):
        t0 = datetime.fromisoformat(events[i - 1]["ts"])
        t1 = datetime.fromisoformat(events[i]["ts"])
        gap = (t1 - t0).total_seconds()
        if 0 < gap <= idle_gap_threshold_sec:
            active_time += gap

    parse_completed = _count_events_by_type(events, "parse_completed")
    if active_time <= 0 or parse_completed == 0:
        return None

    return {
        "files_per_sec": parse_completed / active_time,
        "as_of": events[-1]["ts"],
    }


# ── 메인 상태 계산 함수 ───────────────────────────────────

def get_pipeline_status(
    base_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    event_log_path: Optional[Path] = None,
) -> list[PipelineStageState]:
    """파이프라인 전단계의 런타임 상태를 계산한다.

    Args:
        base_dir: DBMA 프로젝트 루트 디렉토리 (기본: 현재 디렉토리)
        output_dir: 처리 출력 디렉토리 (기본: {base_dir}/output)
        event_log_path: 이벤트 로그 파일 경로 (기본: {base_dir}/logs/project_events.jsonl)

    Returns:
        PipelineStageState 목록 (extract → chunk → embedding → indexing → search 순)
    """
    if base_dir is None:
        base_dir = Path.cwd()
    if output_dir is None:
        # [SPRINT17-Phase5-C4.1] config.yaml's directories.output_dir is the
        # single authority for where processing output actually lives — the
        # previous hardcoded base_dir/"output" pointed at a stale, unrelated
        # directory once output_dir was set to "data/제련완성본" (see
        # Phase5-C4 discovery: output/.batch_state.json and
        # output/registry/documents.json were day-old snapshots, not the
        # live state).
        from core.config import DEFAULT_OUTPUT_DIR
        output_dir = base_dir / DEFAULT_OUTPUT_DIR
    if event_log_path is None:
        event_log_path = base_dir / "logs" / "project_events.jsonl"

    # 이벤트 로그 읽기
    events = _read_event_log(event_log_path)
    
    # BatchState 읽기
    batch_state = _load_batch_state(output_dir)
    processed_count = len(batch_state.get("processed", []))
    failed_count = len(batch_state.get("failed", []))
    
    # TSU 데이터셋 체크
    # [SPRINT17-RG-6B] tsu_exists/tsu_doc_count는 하위 호환 위해 그대로 사용;
    # tsu_manifest_status는 상세 detail 문자열 구성에만 추가로 사용한다.
    tsu_exists, tsu_doc_count = _check_tsu_dataset(output_dir)
    tsu_manifest_status = _read_tsu_manifest(output_dir)
    
    # 벡터DB 인덱스 체크
    vector_index_exists = _check_vector_index(base_dir)

    # RAW 디렉토리에서 전체 문서 수 계산
    from core.config import DEFAULT_RAW_DIR, SUPPORTED_EXTENSIONS
    raw_dir = Path(DEFAULT_RAW_DIR)
    total_docs = 0
    if raw_dir.exists():
        total_docs = len([
            f for f in raw_dir.rglob("*")
            if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in SUPPORTED_EXTENSIONS
        ])

    # 각 단계별 상태 계산
    stages: list[PipelineStageState] = []

    # 1. 추출 (Extract)
    extract_events = _count_events_by_type(events, "parse_completed")
    if total_docs > 0 and processed_count >= total_docs:
        extract_status = PipelineStageState.COMPLETE
        extract_progress = 100
    elif extract_events > 0:
        extract_status = PipelineStageState.ACTIVE
        extract_progress = min(100, int((extract_events / max(total_docs, 1)) * 100))
    elif processed_count > 0:
        extract_status = PipelineStageState.ACTIVE
        extract_progress = min(100, int((processed_count / max(total_docs, 1)) * 100))
    else:
        extract_status = PipelineStageState.PENDING
        extract_progress = 0

    stages.append(PipelineStageState(
        stage="extract",
        status=extract_status,
        progress=extract_progress,
        detail=f"{extract_events} events, {processed_count} files processed",
    ))

    # 2. 청킹 (Chunk)
    chunk_events = _count_events_by_type(events, "chunk_completed")
    tsu_source_count = tsu_manifest_status.get("source_document_count", 0)
    if tsu_exists and tsu_source_count > 0:
        # TSU 데이터셋이 이미 존재한다는 것 자체가 해당 문서들의 청킹이
        # 끝났다는 직접 증거다 — event log는 마지막으로 기록된 실행 1회분만
        # 반영해 과거 배치 실행분을 누락시킨다(예: run_id="manual" 로그
        # 하나만 남아 12개 파일만 커버 → 89% 오표시, 실제로는 TSU manifest
        # 기준 74개 파일 처리 완료). 임베딩/인덱싱 단계와 동일하게 산출물
        # 존재 여부를 우선 신뢰한다.
        chunk_progress = min(100, int((tsu_source_count / max(total_docs, 1)) * 100))
        chunk_status = (
            PipelineStageState.COMPLETE if chunk_progress >= 100 else PipelineStageState.ACTIVE
        )
        if tsu_source_count >= total_docs:
            # manifest가 현재 RAW보다 많은 문서를 추적 중 — 과거 처리된
            # 문서가 이후 RAW에서 이동/삭제된 경우. "119/64"처럼 분자가 더
            # 큰 분수로 보이면 오해를 사므로 총 처리 문서 수로 표기한다.
            chunk_detail = f"TSU manifest 기준 {tsu_source_count}개 문서 청킹 완료 (현재 RAW {total_docs}개)"
        else:
            chunk_detail = f"TSU manifest 기준 {tsu_source_count}/{total_docs} 파일 청킹 완료"
    elif total_docs > 0 and extract_status == PipelineStageState.COMPLETE:
        chunk_status = PipelineStageState.ACTIVE if chunk_events < total_docs else PipelineStageState.COMPLETE
        chunk_progress = min(100, int((chunk_events / max(total_docs, 1)) * 100)) if total_docs > 0 else 0
        chunk_detail = f"{chunk_events} chunk events"
    elif chunk_events > 0:
        chunk_status = PipelineStageState.ACTIVE
        chunk_progress = min(100, int((chunk_events / max(total_docs, 1)) * 100))
        chunk_detail = f"{chunk_events} chunk events"
    elif extract_status == PipelineStageState.COMPLETE:
        chunk_status = PipelineStageState.ACTIVE
        chunk_progress = 50  # extract complete but no chunk events yet
        chunk_detail = f"{chunk_events} chunk events"
    else:
        chunk_status = PipelineStageState.PENDING if extract_status == PipelineStageState.PENDING else PipelineStageState.ACTIVE
        chunk_progress = 0
        chunk_detail = f"{chunk_events} chunk events"

    stages.append(PipelineStageState(
        stage="chunk",
        status=chunk_status,
        progress=chunk_progress,
        detail=chunk_detail,
    ))

    # 3. 임베딩 (Embedding)
    if tsu_exists and tsu_doc_count > 0:
        embedding_status = PipelineStageState.COMPLETE
        embedding_progress = 100
    elif chunk_status == PipelineStageState.COMPLETE:
        embedding_status = PipelineStageState.ACTIVE
        embedding_progress = 30  # just started
    else:
        embedding_status = PipelineStageState.PENDING if chunk_status == PipelineStageState.PENDING else PipelineStageState.ACTIVE
        embedding_progress = 0

    stages.append(PipelineStageState(
        stage="embedding",
        status=embedding_status,
        progress=embedding_progress,
        detail=(
            f"TSU manifest: {tsu_manifest_status['tsu_count']} TSUs from "
            f"{tsu_manifest_status['source_document_count']} documents "
            f"(generated_at={tsu_manifest_status['generated_at']})"
        ) if tsu_exists else "TSU manifest not found (output/bench/tsu_manifest.json)",
    ))

    # 4. 인덱싱 (Indexing)
    if vector_index_exists:
        indexing_status = PipelineStageState.COMPLETE
        indexing_progress = 100
    elif embedding_status == PipelineStageState.COMPLETE:
        indexing_status = PipelineStageState.ACTIVE
        indexing_progress = 50
    else:
        indexing_status = PipelineStageState.PENDING if embedding_status == PipelineStageState.PENDING else PipelineStageState.ACTIVE
        indexing_progress = 0

    stages.append(PipelineStageState(
        stage="indexing",
        status=indexing_status,
        progress=indexing_progress,
        detail=f"Vector index: {'found' if vector_index_exists else 'not found'}",
    ))

    # 5. 검색 (Search) — retrieval 모듈 가용성 기반
    try:
        from core.retrieval import RetrievalEngine
        search_status = PipelineStageState.COMPLETE
        search_progress = 100
    except ImportError:
        search_status = PipelineStageState.PENDING
        search_progress = 0

    stages.append(PipelineStageState(
        stage="search",
        status=search_status,
        progress=search_progress,
        detail="RetrievalEngine 가용" if search_status == PipelineStageState.COMPLETE else "RetrievalEngine 미로드",
    ))

    return stages


def get_pipeline_status_dict(
    base_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    event_log_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """파이프라인 상태를 딕셔너리 형태로 반환 (Dashboard용)."""
    stages = get_pipeline_status(base_dir, output_dir, event_log_path)
    return {s.stage: s.to_dict() for s in stages}