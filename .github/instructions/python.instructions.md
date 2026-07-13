---
name: python-files
description: "DBMA Python 파일 수정 규칙: 함수 단위 작업, 한글 주석/로그, type hints 필수, 기존 구조 유지, 테스트 후 커밋."
applyTo: "**/*.py"
---

# DBMA Python 파일 수정 규칙

## Python 코드 작성 표준

### 1. 임포트 정렬
```python
# 표준 라이브러리
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict

# 써드파티
import numpy as np
import pandas as pd
from llama_index.core import SimpleDirectoryReader

# 로컬 임포트
from core.config import Config
from core.utils import logger
```

### 2. Type Hints 필수
```python
def extract_text(file_path: str, max_pages: Optional[int] = None) -> str:
    """문서에서 텍스트 추출."""
    
def process_chunks(chunks: List[str], metadata: Dict[str, any]) -> Dict[str, List]:
    """청크 처리."""
```

### 3. 로깅
```python
logger.info("[extract] started: path=%s", file_path)
logger.debug("[extract] found %d pages", page_count)
logger.warning("[extract] page %d corrupted", page_num)
logger.error("[extract] failed: %s", error_msg)
```

### 4. 한글 주석 및 docstring
```python
def normalize_text(text: str, remove_punctuation: bool = True) -> str:
    """
    텍스트 정규화 수행.
    
    특수 문자 제거, 공백 정리, 인코딩 통일.
    히브리어/헬라어 문자 보존.
    
    Args:
        text: 입력 텍스트
        remove_punctuation: 특수 문자 제거 여부 (기본값: True)
    
    Returns:
        정규화된 텍스트
    
    Raises:
        ValueError: 입력이 빈 문자열인 경우
    """
```

---

## 파일별 수정 가이드

### `core/extractors.py` - 문서 추출
- 새로운 파일 형식 추가할 때: 기존 함수 구조 유지
- 폴더: `PDF`, `DOCX`, `TXT` 각각의 클래스/함수 분리
- 반환값: `(text: str, metadata: dict)` 형태 강제
- 테스트: 각 형식별로 샘플 파일로 테스트

### `core/text_normalizer.py` - 텍스트 정제
- 단계별 처리: `normalize_whitespace` → `normalize_unicode` → `normalize_special_chars`
- 한글/히브리어/헬라어 보존 확인
- 설정 객체 사용: `config.NORMALIZATION_RULES`

### `core/chunking_optimizer.py` - 청킹
- chunk_size와 overlap은 설정에서 읽음
- 문장 경계 존중: 단어 중간에 끊지 말 것
- 메타데이터 전달: chunk마다 `source_file`, `chunk_id`, `position` 포함
- 로그: 청크 수, 평균 크기, 제목 추출 여부

### `core/embedder.py` - 임베딩
- 모델: `bge-m3:latest` 기본값
- 배치 처리: 성능 고려 (기본 batch_size=32)
- 캐싱: 같은 텍스트는 재임베딩 금지
- 로그: 총 문서 수, 임베딩 완료 수, 소요 시간

### `core/retrieval.py` - 검색
- 쿼리 전처리 필수
- 상위 K개 결과만 반환: `top_k=5` (기본값)
- 유사도 스코어 포함
- 메타데이터도 함께 반환

### `core/ingest.py` - 저장소 관리
- 문서 ID 중복 확인
- 업데이트 vs 신규 구분
- 트랜잭션 안전성 고려 (실패 시 롤백)

---

## 수정 작업 체크리스트

### 수정 전
- [ ] 대상 함수의 호출처 모두 찾음?
- [ ] 입출력 타입 확인함?
- [ ] 기존 테스트 있나?
- [ ] 다른 파일과 의존성 있나?

### 수정 중
- [ ] Type hints 추가함?
- [ ] 한글 설명/로그 추가함?
- [ ] 기존 로그 레벨 유지함?
- [ ] 예외 처리 추가함?

### 수정 후
- [ ] import 정렬 확인?
- [ ] 문법 오류 없나?
- [ ] 로그 출력 확인?
- [ ] 간단한 테스트 실행?
- [ ] 기존 기능 깨지지 않았나?

---

## 금지 사항 (Python)

❌ **절대 금지**
- f-string 대신 `%` 포매팅: `logger.info("[module] %s", var)` 사용
- 전역 변수 남용
- 한글 변수명
- 예외 무시: `except: pass`
- 매직 넘버: `1200` → `config.CHUNK_SIZE`

---

## 테스트 예시

```python
# tests/test_extractors.py
def test_extract_pdf():
    """PDF 추출 테스트."""
    file_path = "tests/fixtures/sample.pdf"
    text, metadata = extract_pdf(file_path)
    
    assert len(text) > 0, "추출된 텍스트가 없음"
    assert "source_file" in metadata, "메타데이터 누락"
    logger.info("[test] PDF 추출 성공: %d chars", len(text))
```

---

## 커밋 메시지 예시

```
[core/extractors] DOCX 형식 지원 추가

- DOCX 파일에서 텍스트 추출하는 함수 추가
- 메타데이터 (제목, 작성자) 포함
- 기존 PDF/TXT 추출과 동일한 인터페이스 유지

테스트: tests/fixtures/sample.docx로 검증 완료
```
