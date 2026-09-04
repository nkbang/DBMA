"""NAE Incremental Ingestion Architecture v1 (NAE-INCREMENTAL-INGESTION-001).

이 패키지는 기존 Production(3,319 verified TSU, Qdrant `nae_tsu_v1` 1,281
vectors)을 재처리하지 않고, 새/변경 자료만 증분 처리하기 위한 계층이다.

범위: `NAE_CORPUS_INGESTION_STANDARD_v1.md`(설계 단계, 미구현)가 정의하는
"Registration -> Validation -> ... -> TSU" 앞단(신규 원문 발견/등록/OCR/TSU
최초 생성)은 이 패키지의 범위가 아니다 — 그 파이프라인 자체가 아직
구현되어 있지 않다(2026-08-11 감사 확인). 이 패키지는 **TSU 레코드가 이미
존재하는 시점부터** — content hash 기반 NEW/UNCHANGED/CHANGED 판정,
processing state 추적, embedding/indexing 증분 실행, Production Manifest
생성 — 을 담당한다. 앞단 파이프라인이 구현되면 그 출력(TSU 레코드)을 그대로
이 패키지에 넘기면 된다.
"""
