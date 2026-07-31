# NAE Baptist Library Standard v1

작성일: 2026-07-31
목적: 침례교 특화 Knowledge Base 구축을 위한 자료 분류 기준. 수집 우선순위와 RAG 활용 목적을 정의한다.
이 문서는 분류 기준만 정의하며, 실제 자료 수집/다운로드는 포함하지 않는다.

## 분류 체계

### 1. Baptist Confessions (침례교 신앙고백서)
- **우선순위**: 최상 (1순위)
- **예상 자료 유형**: 1689 London Baptist Confession, New Hampshire Confession, Baptist Faith and Message(1925/1963/2000) 등 공식 신앙고백 원문 및 주석
- **RAG 활용 목적**: 교리 질의에 대한 1차 근거 자료. 신학적 입장 판별의 기준점(anchor text)으로 사용 — 다른 자료의 `theological_position` 태깅 시 참조 기준

### 2. Baptist History (침례교 역사)
- **우선순위**: 중상 (2순위)
- **예상 자료 유형**: 침례교 기원사, 지역/교단 분립사, 주요 인물 전기, 한국 침례교 역사 자료
- **RAG 활용 목적**: 역사적 맥락 질의 응답, 특정 교리/관행의 역사적 배경 설명 근거

### 3. Baptist Theology (침례교 조직신학)
- **우선순위**: 최상 (1순위)
- **예상 자료 유형**: 침례교 신학자의 조직신학 저서, 교리 해설서
- **RAG 활용 목적**: 신학 질의응답의 핵심 본문. 설교 초안 생성 시 교리적 정합성 검증 근거

### 4. Church Practice (교회 실행/운영)
- **우선순위**: 중 (3순위)
- **예상 자료 유형**: 교회 정치(church polity), 침례/성찬 실행 지침, 회중 자치 관련 문서
- **RAG 활용 목적**: 실무 질의(예: "침례 예식 순서") 대응, 목회 매뉴얼 생성 보조

### 5. Missions (선교)
- **우선순위**: 중하 (4순위)
- **예상 자료 유형**: 선교 신학, 선교 역사 및 사례, 침례교 선교 단체 자료
- **RAG 활용 목적**: 선교 관련 설교/교육 자료 생성 지원

### 6. Pastoral Ministry (목회)
- **우선순위**: 중상 (2순위, 사용자 실사용 빈도 고려)
- **예상 자료 유형**: 목회학, 상담, 심방, 교회 행정 실무서
- **RAG 활용 목적**: 사용자가 목회자로서 가장 빈번히 참조할 가능성 높은 실무 자료 — Sermon Draft 기능과 직결

### 7. Biblical Commentary (성경 주석)
- **우선순위**: 최상 (1순위)
- **예상 자료 유형**: 침례교 신학자/목회자가 저술한 주석서, 강해서
- **RAG 활용 목적**: 본문 중심 질의응답의 핵심 근거. 기존 NAE 통합 검색(v3)의 성경 축과 직접 연결 — [[project_nae_unified_search_v3]]

## 수집 우선순위 요약

| 순위 | 분류 |
|---|---|
| 1 | Confessions, Theology, Biblical Commentary |
| 2 | Baptist History, Pastoral Ministry |
| 3 | Church Practice |
| 4 | Missions |

## 비고

- 본 분류는 `data/nae/sources/` 하위 4개 디렉토리(baptist, theology, commentary, public_domain)와 1:N 매핑됨 — 예: Confessions/History/Church Practice/Missions/Pastoral Ministry는 `sources/baptist/`, Biblical Commentary는 `sources/commentary/`, 순수 조직신학은 `sources/theology/`로 배치 예정.
- 실제 디렉토리 배치 규칙은 TASK 4 결과 및 향후 수집 단계에서 세분화 필요.
