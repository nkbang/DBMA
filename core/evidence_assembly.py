"""core/evidence_assembly.py — Grounded Synthesis Phase 3: Multi-Query Evidence Assembly.

Phase 3의 목적: 이미 실행된 여러 retrieval query의 RankedCandidate[] 결과를
하나의 추적 가능한 Evidence Pool로 assembly한다.

Architecture boundary:
    Query A -> RankedCandidate[] (caller가 이미 실행)
    Query B -> RankedCandidate[] (caller가 이미 실행)
    Query C -> RankedCandidate[] (caller가 이미 실행)
                    downarrow
        assemble_evidence_pool_with_manifest() (this module)
                    downarrow
        EvidencePool + AssemblyManifest (assembly)

핵심 원칙:
    - Phase 3은 retrieval을 실행하지 않는다.
    - QueryProcessor/HybridQueryProcessor/RetrievalEngine/HybridRetriever를
      import하거나 호출하지 않는다.
    - 이미 실행된 RankedCandidate[]만 받아 Evidence로 변환하고 Pool에 assembly한다.
    - Phase 2의 duplicate 정책(overwrite, 마지막 값 유지)을 그대로 사용한다.
    - ranking을 다시 계산하지 않는다.
    - AssemblyManifest는 EvidencePool과 완전히 별개 -- EvidencePool 내부 상태 접근 안 함.

ABSOLUTE RULES:
    - No retrieval execution (no QueryProcessor/HybridQueryProcessor/RetrievalEngine/HybridRetriever)
    - No score recalculation
    - No re-ranking
    - No Evidence model change
    - No EvidencePool public contract change
    - No production data mutation
    - Manifest constructed solely from query_candidates input (no EvidencePool internals access)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from core.evidence_adapters.tsu_adapter import RankedCandidateEvidenceAdapter
from core.evidence_model import Evidence
from core.evidence_pool import EvidencePool, build_evidence_pool_from_ranked_candidates
from core.retrieval import RankedCandidate

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuerySpec:
    """Single retrieval query specification.

    Phase 3은 query를 생성하지 않는다 -- 호출자가 이미 만들어서 전달한다.
    이 클래스는 query의 metadata를 추적하기 위한 lightweight container다.
    """

    query: str
    role: str = "primary"
    order: int = 0


# QuerySpec + RankedCandidate[]의 명시적 대응을 위한 타입 별칭
# positional association -- 어떤 query가 어떤 candidate 그룹에 속하는지 절대 암묵적 순서 추정에 의존하지 않음
MultiQueryInput = list[tuple[QuerySpec, list[RankedCandidate]]]


@dataclass(frozen=True)
class AssemblyManifest:
    """질의 -> evidence_id 연관을 EvidencePool의 overwrite 정책과 무관하게 보존한다.

    EvidencePool.by_query()는 evidence_id당 마지막 build_query만 안다.
    이 manifest는 그 반대 방향(질의 -> 이 질의가 찾은 모든 evidence_id, 원 순위 순서)과
    정방향(evidence_id -> 이 근거를 찾은 모든 질의) 둘 다 완전히 보존한다.

    manifest 구성 로직은 EvidencePool 인스턴스의 내부 속성(_evidences, _index)에
    접근하지 않는다 -- 입력 query_candidates만으로 독립적으로 구성된다.
    """

    # 질의 순서대로: (QuerySpec, [evidence_id, ...]) -- candidates의 원 순위 순서 유지
    by_query_order: list[tuple[QuerySpec, list[str]]]
    # evidence_id -> 이 근거를 찾은 모든 QuerySpec.query (발견 순서)
    evidence_to_queries: dict[str, list[str]]

    def queries_for(self, evidence_id: str) -> list[str]:
        """Returns the list of query strings that produced this evidence_id."""
        return self.evidence_to_queries.get(evidence_id, [])


def _build_manifest(
    query_candidates: MultiQueryInput,
    candidate_evidence_ids: list[list[str]],
) -> AssemblyManifest:
    """Build AssemblyManifest solely from query_candidates input (no EvidencePool access).

    Parameters
    ----------
    query_candidates : MultiQueryInput
        The original input -- provides QuerySpec and ordering.
    candidate_evidence_ids : list[list[str]]
        Parallel list where each element is the evidence_ids extracted
        from the corresponding query's RankedCandidate[] (in ranking order).

    Returns
    -------
    AssemblyManifest
        Fully constructed manifest independent of EvidencePool internals.
    """
    by_query_order: list[tuple[QuerySpec, list[str]]] = []
    evidence_to_queries: dict[str, list[str]] = {}

    for (query_spec, _candidates), eids in zip(query_candidates, candidate_evidence_ids):
        by_query_order.append((query_spec, list(eids)))

        for eid in eids:
            if eid not in evidence_to_queries:
                evidence_to_queries[eid] = []
            evidence_to_queries[eid].append(query_spec.query)

    return AssemblyManifest(
        by_query_order=by_query_order,
        evidence_to_queries=evidence_to_queries,
    )


def _extract_evidence_ids(candidates: list[RankedCandidate]) -> list[str]:
    """Extract evidence_id using the SAME identity resolution as
    RankedCandidateEvidenceAdapter — so manifest keys always match
    the evidence_id actually stored in EvidencePool, including the
    tsu_id-missing fallback path."""
    return [
        RankedCandidateEvidenceAdapter._resolve_evidence_id(c.tsu_id or "", c)
        for c in candidates
    ]


def assemble_evidence_pool_with_manifest(
    query_candidates: MultiQueryInput,
) -> tuple[EvidencePool, AssemblyManifest]:
    """이미 실행된 여러 retrieval query의 RankedCandidate[]를 Evidence Pool + Manifest로 assembly.

    이 함수는 retrieval을 실행하지 않는다. 호출자가 이미 QueryProcessor/HybridQueryProcessor
    .process()를 실행한 뒤 반환된 ResponsePackage.top_k_results(list[RankedCandidate])를
    전달해야 한다.

    assemble_evidence_pool()과 동일하게 Pool을 만들되, manifest도 함께 반환한다.
    manifest는 EvidencePool과 완전히 별개 -- EvidencePool 내부 상태에 접근하지 않고
    query_candidates 입력만으로 독립적으로 구성된다.

    Parameters
    ----------
    query_candidates : MultiQueryInput
        list[tuple[QuerySpec, list[RankedCandidate]]]
        각 tuple은 (query_spec, candidate_list) 쌍이다.
        순서는 assembly 순서이자 query ordering의 기준이다.
        candidate_list의 순서는 기존 retrieval이 반환한 ranking order 그대로 유지된다.

    Returns
    -------
    tuple[EvidencePool, AssemblyManifest]
        Pool: 모든 query에서 얻은 Evidence가 assembly된 Pool.
              duplicate identity 정책(Phase 2 overwrite)이 적용된다.
              build_query는 각 query의 QuerySpec.query 문자열로 설정된다.
        Manifest: 어떤 질의가 어떤 evidence_id를 찾았는지 완전히 보존.

    Notes
    -----
    - Query ordering: 입력 순서(Priority Query -> Expanded Query 1 -> ...) 그대로 유지.
    - Candidate ordering: 각 query 내부에서 기존 retrieval이 반환한 candidate order(top_k_results) 그대로 유지.
    - Duplicate identity: 동일 evidence_id가 여러 query에서 발견되면 마지막 add가 overwrite (Phase 2 정책).
    - Manifest는 duplicate를 포함해 모든 발생을 기록 -- queries_for("E1") == ["A", "B"] 가능.
    - Ranking 불변: final_score/retrieval_score/bm25_score/theological_score/passage_score 모두 원본 값 그대로.
    """
    # Step 1: Extract evidence_ids from each query's candidates (ranking order)
    candidate_evidence_ids: list[list[str]] = []
    for _, candidates in query_candidates:
        candidate_evidence_ids.append(_extract_evidence_ids(candidates))

    # Step 2: Build manifest solely from input (no EvidencePool access)
    manifest = _build_manifest(query_candidates, candidate_evidence_ids)

    # Step 3: Build pool using Phase 2's existing function
    pool = EvidencePool()
    for query_spec, candidates in query_candidates:
        if not candidates:
            logger.debug(
                "assemble_evidence_pool_with_manifest: empty candidates for query %r (role=%s, order=%d)",
                query_spec.query,
                query_spec.role,
                query_spec.order,
            )
            continue

        pool = build_evidence_pool_from_ranked_candidates(
            candidates=candidates,
            query=query_spec.query,
            pool=pool,
        )

    return pool, manifest


def assemble_evidence_pool(
    query_candidates: MultiQueryInput,
) -> EvidencePool:
    """이미 실행된 여러 retrieval query의 RankedCandidate[]를 Evidence Pool로 assembly.

    이 함수는 retrieval을 실행하지 않는다. 호출자가 이미 QueryProcessor/HybridQueryProcessor
    .process()를 실행한 뒤 반환된 ResponsePackage.top_k_results(list[RankedCandidate])를
    전달해야 한다.

    Parameters
    ----------
    query_candidates : MultiQueryInput
        list[tuple[QuerySpec, list[RankedCandidate]]]
        각 tuple은 (query_spec, candidate_list) 쌍이다.
        순서는 assembly 순서이자 query ordering의 기준이다.
        candidate_list의 순서는 기존 retrieval이 반환한 ranking order 그대로 유지된다.

    Returns
    -------
    EvidencePool
        모든 query에서 얻은 Evidence가 assembly된 Pool.
        duplicate identity 정책(Phase 2 overwrite)이 적용된다.
        build_query는 각 query의 QuerySpec.query 문자열로 설정된다.

    Notes
    -----
    - Query ordering: 입력 순서(Priority Query -> Expanded Query 1 -> ...) 그대로 유지.
    - Candidate ordering: 각 query 내부에서 기존 retrieval이 반환한 candidate order(top_k_results) 그대로 유지.
    - Duplicate identity: 동일 evidence_id가 여러 query에서 발견되면 마지막 add가 overwrite (Phase 2 정책).
    - Ranking 불변: final_score/retrieval_score/bm25_score/theological_score/passage_score 모두 원본 값 그대로.
    """
    pool, _ = assemble_evidence_pool_with_manifest(query_candidates)
    return pool
