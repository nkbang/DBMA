---
title: "NAE Dual Pipeline Clarification"
category: architecture
based_on:
  - docs/architecture/ADR-013-NAE-Vector-Store.md
created: 2026-08-01
---

# NAE Dual Pipeline Clarification

작성일: 2026-08-01
배경: CUE가 두 개의 별개 TSU/파이프라인 구현(`NAE/pipeline/` vs `core/tsu_builder.py`의 `nae_metadata` 확장)을 발견하고, 이를 실수로 인한 중복 아키텍처로 오인해 하나로 통합해야 하는지 HQ에 질의함. **답변: 중복이 아니라 의도된 이중 경로. 전체 DBMA와의 하모니(향후 통합 가능성)를 위해 둘 다 유지.**

## 두 경로의 역할 분담

### 경로 A — `NAE/pipeline/` + `NAE/corpus/` (ADR-013)
- **목적**: NAE 코퍼스 자체의 독립적인 연구·구축·검증
- **격리**: `core/`와 완전히 분리, 별도 Qdrant 인스턴스(`nae_qdrant`, 포트 7333/7334), 별도 컬렉션(`nae_tsu_v1`)
- **개념**: "Theological **Semantic** Unit" — LLM 기반 claim 추출, 정수 ID(`TSU-{n}`)
- **소비처**: 메인 DBMA `core/retrieval.py::RetrievalEngine`이 **읽지 않음** — ADR-013이 명시적으로 금지
- **현재 실행 이력**: PBC1765가 이 경로로 canonical 정규화 완료(2026-08-01, `docs/agents/cue/HQ-ADVISORY-PBC1765-CANONICAL-DECISION.md` 참고), TSU/embed/index는 품질 이슈로 아직 미실행

### 경로 B — `core/tsu_builder.py`(`nae_metadata` 블록) + `scripts/ingest_nae_source.py` (STEP4-D)
- **목적**: NAE 콘텐츠(침례교 신학 자료 등)를 **메인 DBMA 검색(`core/retrieval.py::RetrievalEngine`)에도 노출**시키기 위한 통합 경로
- **격리**: 기존 TSU 스키마에 순수 additive(`nae_metadata` 필드 하나만 추가), 기존 코퍼스에 영향 없음 — `docs/tasks/reports/NAE_METADATA_ADAPTER_ARCHITECTURE_v1.md` 설계
- **개념**: "Theological **Source** Unit"(TSU v1, 기존 DBMA 체계 그대로) — `TSU-{book_id}-{chunk_id}` ID
- **소비처**: 향후 메인 DBMA 검색 결과에 NAE 자료가 성경/기존 신학서와 함께 나타나는 것이 목표
- **현재 실행 이력**: 코드/테스트 완료(46개 테스트 통과, 커밋 `d32b716`), 실제 프로덕션 문서 ingest는 아직 미실행(원문 미확보)

## 왜 둘 다 필요한가

- 경로 A는 "NAE만의 독자적 검색/실험 환경"을 위한 것 — 향후 NAE가 별도 서비스/제품으로 발전할 가능성, 또는 메인 DBMA와 다른 임베딩·인덱싱 정책을 실험할 자유를 보장
- 경로 B는 "사용자가 DBMA 앱에서 검색할 때 침례교 신학 자료도 함께 나오게 하는 것" — 실제 최종 사용자 경험(전체 DBMA의 하모니) 목표
- 두 목적이 서로 다르므로, 한쪽을 없애면 다른 목적을 달성할 수 없음 — **통합/양자택일 논의 종료**

## 향후 작업 시 유의사항

- 새 NAE 관련 작업을 지시할 때는 **어느 경로**를 대상으로 하는지 명시할 것(예: "NAE/pipeline으로 canonical 처리" vs "core/tsu_builder.py 경로로 메인 검색에 노출")
- 두 경로의 raw 저장 위치가 다름에 유의: 경로 A는 `NAE/corpus/raw/archive_org/books/{ID}/`(`ocr.txt`/`original.pdf`/`hocr.html`), 경로 B는 `data/nae/sources/{genre}/`(txt) — 동일 원문이라도 각 경로에 맞는 형식으로 별도 배치 필요할 수 있음
- 두 경로의 source_id/추적 체계가 다를 수 있음 — `resources/theological_sources/baptist/source_manifest.yaml`(경로 B/등록 단계 공통) 하나로 서지 정보는 통합 관리하되, 실제 파이프라인 산출물 경로는 목적에 따라 분리 유지
