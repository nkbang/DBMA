# NAE TSU Indexer — Performance Backlog 001

**작성일:** 2026-08-10
**성격:** Architecture 영역 backlog 기록(코드 변경 없음).

## 문제

`NAE/pipeline/index/indexer.py::index_all()`은 `NAE/corpus/tsu/` 아래
모든 하위 디렉터리를 스캔한다. Human Review 배치가 진행될 때마다
`_batchNNNN_promotion_backup_<timestamp>/`, `_batchNNNN_remediation*_backup_<timestamp>/`
디렉터리가 감사 목적으로 계속 누적되고 있으며(배치당 1개 이상),
`index_all(dry_run=True)`가 이 백업 디렉터리들도 매번 스캔 대상에
포함시켜(비록 `review_status` 게이트로 인해 실제 인덱싱되지는 않지만)
배치가 늘어날수록 dry_run 호출 자체가 점점 느려지는 경향이 있다.

## 원칙(현재 유지)

- 기존 백업 디렉터리는 **삭제·이동·정리하지 않는다** — 감사 추적성
  (auditability)이 최우선.
- `indexer.py` 코드를 지금 임의로 수정하지 않는다(Architecture Freeze
  Rule과 동일한 이유 — Batch 진행 중 핵심 파이프라인 변경 금지).

## 권장 후속 조치(구현하지 않음, 기록만)

1. `indexer.py`가 스캔할 identifier 목록을 결정할 때, `_` 접두사가
   붙은 백업/remediation 디렉터리를 식별자 목록에서 제외하는 필터
   추가 검토(정규식 예: `^_.*_backup_\d{8}T\d{6}$`).
2. 제외되더라도 백업 디렉터리 자체는 파일시스템에 그대로 남아
   감사 시 수동 조회 가능해야 한다 — "인덱서 스캔에서 제외"와
   "삭제"는 다른 개념임을 명확히 구분.
3. 별도 maintenance 작업(Architecture 변경 승인 필요)에서 처리.
   현재 Batch 진행에는 영향 없음(성능 저하일 뿐, 정확성 문제 아님).

## 관련

Batch 1~10 기준 누적 백업 디렉터리 다수, `docs/NAE_TSU_4107_EXPANSION_STATE.md`
참고.
