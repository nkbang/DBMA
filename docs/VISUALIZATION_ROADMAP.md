# DBMA 비주얼라이제이션 로드맵

## 완료
- [x] 청킹 미리보기 — 청크 길이 막대그래프 (`ui/pages/library.py`
      `_render_chunk_preview_section()`, `st.bar_chart`, 2026-07-27,
      C1 Task Order 015 §A)

## 계획 중
- [ ] 파이프라인 전체 흐름도 (Mermaid) — 아래 예시, CLAUDE.md의
      "파이프라인 순서" 섹션과 반드시 일치시킬 것

## 파이프라인 흐름 (Mermaid)

```mermaid
flowchart LR
    A[원본 문서] --> B[추출]
    B --> C[정제]
    C --> D[청킹]
    D --> E[저장]
    E --> F[임베딩]
    F --> G[검색]
    G --> H[생성]
    H --> I[평가]
```

(주: 이 흐름도는 CLAUDE.md의 "파이프라인 순서" 섹션과 반드시 일치시킬
것 — 불일치하면 CLAUDE.md 쪽이 기준.)

## 비고

- 이 문서는 백로그 + 다이어그램 스케치 역할만 한다 — 여기 있다고
  자동으로 구현되지 않는다. 구현 착수는 별도 Task Order로 결정.
- "계획 중" 항목은 실제로 사용자/CUE가 언급한 것만 적는다 — 임의로
  기능을 지어내 넣지 않는다(C1-TASK-ORDER-015 §B.2 원칙). 이번 문서
  작성 시점(2026-07-27) 기준, "청크 품질 히트맵"이나 "검색 결과 스코어
  분포" 같은 항목은 실제로 논의된 적이 없어 포함하지 않았다 —
  Task Order 015 원문의 "예시" 항목이었을 뿐 실제 백로그가 아니다.
- Mermaid는 GitHub/VS Code 미리보기에서 렌더링되는 마크다운 코드
  블록으로만 사용한다 — Streamlit 앱 안에 Mermaid를 렌더링하는 신규
  컴포넌트(`streamlit-mermaid` 등)는 설치하지 않는다.
