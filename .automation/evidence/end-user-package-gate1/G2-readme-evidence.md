# G2 Evidence — README.md 갱신

## 변경 사항 요약

### 1. `app/` 디렉터리 서술 제거
- **Before**: 프로젝트 구조에 `├── app/                   # 애플리케이션 모듈` 포함
- **After**: 전체 리라이팅으로 `app/` 서술 없음 (실존하지 않음)

### 2. ChromaDB 자기모순 해소
- **Before**: 
  - Line 42-44: "ChromaDB 벡터 저장소를 통한 문서 임베딩 및 검색" (사용 중으로 서술)
  - Line 88: "ChromaDB/Qdrant는 legacy corpus history로만 보존되며 검색 경로에서 쿼리되지 않음" (사용 안 함)
- **After**: 통일된 서술 — "ChromaDB / Qdrant는 legacy corpus history로만 보존되며, 현재 검색 경로에서 쿼리되지 않음"

### 3. 9개 UI 페이지 명시
- Dashboard, Library, Processing, Research, Chat, 설교문 작성, 설교 리뷰, Monitor, 도움말 표 형식 나열

### 4. Citation/Provenance 표시 언급 추가
- "검색 결과에 author, source_title, evidence_confidence 포함"

### 5. Dashboard / Monitor 분리 서술
- Dashboard: "사용자용 통계 대시보드 (처리된 문서 수, 진행 상황 등)"
- Monitor: "시스템 모니터링 (로그, 처리 상태, 성능 지표)"

### 6. NAE bridge(opt-in) 언급 추가
- "NAE Public Theology Module (opt-in)" 섹션으로 별도 기술

### 7. 개발자 내부 구조 과다 서술 제거
- ADR 번호, 모듈 경계, RetrievalEngine 내부 구조 등 제거
- "개발자 참고" 섹션에 링크만 남김

### 8. 버전 정보 정정
- **Before**: "버전: 1.0.0" (잘못됨)
- **After**: "**현재 버전**: `1.3.0` (`config.yaml::app.version` 기준)"

## 검증 체크리스트

| 항목 | 상태 |
|------|------|
| `app/` 서술 제거 | ✅ |
| ChromaDB 자기모순 해소 | ✅ |
| 9개 UI 페이지 명시 | ✅ |
| Citation/Provenance 언급 | ✅ |
| Dashboard/Monitor 분리 | ✅ |
| NAE opt-in 언급 | ✅ |
| 개발자 상세 과다 서술 없음 | ✅ |
| 버전 정보 SSOT 일치 | ✅ |
