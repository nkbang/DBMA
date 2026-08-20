> **CUE 정리 노트 (2026-08-18)**: 이 문서는 원래 "ADR-016"으로 작성됐으나
> 그 번호는 이미 다른 문서(NAE Metadata Authority Model Revision, Approved,
> 2026-08-03)가 선점하고 있고, 이 문서 자체는 한 번도 승인되지 않은 채
> (`PENDING HUMAN HQ APPROVAL`) 방치돼 있었다. 본문 내용(`RetrievalEngine`
> 독점 권한 계약)은 이미 Approved 상태인 `ADR-001-Retrieval-Engine-Authority.md`가
> 실질적으로 동일한 내용을 다루고 있어 — git grep 결과 이 파일을 참조하는
> 곳도 전혀 없어 — 새 번호를 부여해 되살리기보다 여기 파일명만 정리해
> 남겨둔다(git 추적 대상 아님, 참고용 draft로만 보존).

# ADR-016 (draft, 미승인·미번호): Retrieval Authority Contract

**Date:** 2026-07-24  
**Status:** PROPOSED — PENDING HUMAN HQ APPROVAL (never approved, orphaned)  
**Authority:** C1 Architecture Governor  
**Mission:** DBMA-SPRINT33-C1-ARCH-GOVERNANCE  

---

## 1. Context

DBMA의 검색 시스템은 `core/retrieval.py`의 `RetrievalEngine` 클래스가 유일한 검색 권한을 가진다. 이 계약은 검색 코드가 단일 모듈에 집중되도록 보장한다.

## 2. Decision

### 2.1 RetrievalEngine 독점 권한

**`core/retrieval.py::RetrievalEngine`** 은 DBMA의 **유일한** 검색 권한이다.

### 2.2 금지 사항

다음은 **금지**된다:

- 2차 검색 모듈 생성
- 병렬 검색 경로
- 중복 랭킹 로직
- `RetrievalEngine` 외부의 벡터 저장소 쿼리
- 직접 임베딩 유사도 계산 (검색 파이프라인 우회)

### 2.3 허용된 의존 관계

```
query_enhancements.py → retrieval.py (types only)
identity_registry.py → retrieval.py (metadata filter)
index_orchestrator.py → retrieval.py (rebuild)
ui/app.py → retrieval.py (read-only query)
ui/tabs.py → retrieval.py (read-only types)
```

## 3. Consequences

### Positive

- 검색 로직의 단일 진실 출처(Single Source of Truth)
- 검색 품질 개선 시 영향 범위 최소화
- regression 테스트의 명확한 대상

### Negative

- `retrieval.py` 변경 시 전체 시스템 영향 (High Migration Risk)
- 모든 검색 관련 변경은 ADR 승인 필요

## 4. Verification

### 4.1 Automated Checks

```python
# Forbidden: new retrieval code outside core/retrieval.py
import subprocess
result = subprocess.run(
    ["grep", "-r", "RetrievalEngine", "--include=*.py"],
    capture_output=True, text=True
)
for line in result.stdout.splitlines():
    if "core/retrieval.py" not in line:
        raise ValueError(f"RetrievalEngine found outside retrieval.py: {line}")
```

### 4.2 Manual Review Checklist

- [ ] 새 검색 코드가 `core/retrieval.py`에 있는지 확인
- [ ] 다른 모듈이 `RetrievalEngine`을 인스턴스화하지 않는지 확인
- [ ] 벡터 저장소 직접 쿼리 없는지 확인
- [ ] 랭킹 로직 중복 없는지 확인

## 5. Related Contracts

- ADR-017: Configuration Authority Contract (PROPOSED — PENDING HUMAN HQ APPROVAL)
- ADR-018: Data Store Authority Contract (PROPOSED — PENDING HUMAN HQ APPROVAL)

---

**END OF ADR-016**