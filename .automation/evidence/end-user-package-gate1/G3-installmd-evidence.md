# G3 Evidence — INSTALL.md 재작성

## 변경 사항 요약

### 8개 필수 섹션 포함 확인

| # | 섹션 | 위치 | 상태 |
|---|------|------|------|
| 1 | 사전 요구사항 (Python, 디스크, RAM, macOS 우선) | Section 1 | ✅ |
| 2 | Python/venv 준비 (`~/envs/dbma311` 관행 문서화) | Section 2 | ✅ |
| 3 | Ollama 설치 (macOS 기준 `brew install ollama`) | Section 3 | ✅ |
| 4 | 필요한 Ollama 모델 준비 (`bge-m3:latest`, `llama3.1:8b`) | Section 4 | ✅ |
| 5 | DBMA 설치/실행 (`pip install -r requirements.txt`, `streamlit run dbma_ui.py`) | Section 5 | ✅ |
| 6 | 최초 실행 확인 (Onboarding, 9개 페이지 로드) | Section 6 | ✅ |
| 7 | 기본 검색/Chat 사용 예시 | Section 7 | ✅ |
| 8 | 문제 발생 시 최소 진단 절차 (로그 위치, 흔한 오류 5개) | Section 8 | ✅ |

### Ollama 설치+모델 pull 안내 추가
- **Before**: INSTALL.md에 Ollama 관련 0건
- **After**: Section 3(Ollama 설치) + Section 4(모델 pull) 명시

### Qdrant 서술 처리
- **Before**: "Docker Services (Qdrant + n8n)" — "optional Sprint 2/3 services" (낡은 프레이밍)
- **After**: "고급 / 선택 기능" → "Qdrant (선택 사항)" — "DBMA production 검색에는 사용되지 않음" 명시

### 개발자용 잡다한 내용 축소
- Windows 상세 절차: 제거 (macOS 우선, Windows는 링크만)
- Conda/GPU/CUDA/ROCm/ROCm 상세: 전 섹션 제거
- Tesseract/poppler 상세: 흔한 오류 테이블로 통합

### End-user 흐름 검증
1. 사전 요구사항 → 2. Python/venv → 3. Ollama 설치 → 4. 모델 pull → 5. DBMA 설치 → 6. 실행 확인 → 7. 사용 예시 → 8. 문제 해결
- 순차적 흐름 명확

## 검증 체크리스트

| 항목 | 상태 |
|------|------|
| 8개 섹션 전부 포함 | ✅ |
| Ollama 설치+모델 pull 안내 | ✅ |
| Qdrant 필수 아님 명시 | ✅ |
| End-user 실제 따라갈 수 있는 흐름 | ✅ |
| Windows/Conda/GPU/CUDA/ROCm 과다 서술 제거 | ✅ |
| macOS 우선 | ✅ |
