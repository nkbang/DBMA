# C1 Task Order 015 — 청킹 미리보기 시각화 + 향후 비주얼라이제이션 로드맵

발급: CUE (2026-07-26)
발급 사유: 사용자가 청킹 미리보기 결과를 텍스트 목록뿐 아니라 시각적으로
확인하고 싶다고 요청. 아울러 앞으로 추가할 시각화 항목을 문서로
미리 정리해두라고 함(Mermaid 등 사용).
대상: C1 (Cline 작업창 #1) — **반드시 새 Task/새 세션으로 시작**
성격: **구현 Task (§A) + 문서 Task (§B).** 두 부분은 독립적이며 순서
상관없이 진행 가능하나, 반드시 §A부터 끝내고 §B로 넘어갈 것(작은
단위로 수정 후 바로 검증 — CLAUDE.md 작업 방식 원칙).

---

## 0. 전제 확인 (구현 전 반드시 grep/read로 재확인)

- 대상 파일: `ui/pages/library.py`의 `_render_chunk_preview_section()`
  (2026-07-26 기준 356~414행 근처, C1이 실제 줄 번호는 직접
  `grep -n "_render_chunk_preview_section" ui/pages/library.py`로
  재확인할 것 — 이 문서 작성 후 줄 번호가 밀렸을 수 있음).
- 현재 이 함수는 청크를 `st.text_area` 목록으로만 보여주고, 상단에
  `quality.avg_noise`, `quality.avg_dup`, `quality.short_ratio`,
  `quality.passed` 캡션 한 줄만 있다. 청크별 길이 분포나 개별 품질
  차이를 그래프로 보여주는 부분은 없다 — 이번 Task로 추가한다.
- `result.chunks`는 문자열 리스트, `result.quality`는 dataclass 형태
  (avg_noise/avg_dup/short_ratio/passed 필드 보유 — 정확한 타입은
  `core/chunking_optimizer.py`에서 `ChunkQuality` 정의 확인할 것).

## A. 구현: 청킹 미리보기에 청크 길이 시각화 추가

### A.1 범위

`_render_chunk_preview_section()`의 `for i, chunk in enumerate(result.chunks)`
루프 **바로 위**(청크 목록이 나오기 전, 품질 캡션 다음)에 청크 길이
분포를 보여주는 막대그래프 하나만 추가한다.

```python
import pandas as pd  # 이미 다른 곳에서 pandas가 쓰이는지 먼저
                      # `grep -n "^import pandas\|^import pandas as pd" ui/pages/library.py`
                      # 로 확인 — 이미 있으면 재import하지 말 것

chunk_lengths = pd.DataFrame(
    {"chunk_idx": list(range(1, len(result.chunks) + 1)),
     "length": [len(c) for c in result.chunks]}
).set_index("chunk_idx")
st.bar_chart(chunk_lengths)
```

- `st.bar_chart`(Streamlit 내장, 추가 의존성 없음)만 사용한다.
  `plotly`/`altair`/`streamlit-mermaid` 같은 신규 패키지를 새로
  추가하지 말 것 — 내장 컴포넌트로 충분한 범위다.
- 그래프 위에 짧은 캡션 하나만 추가: 목표 chunk_size(기본 1200,
  `CLAUDE.md` 기준)를 기준선처럼 보여줄 필요는 없다(st.bar_chart는
  기준선 오버레이를 기본 지원하지 않음 — 억지로 추가하지 말 것,
  범위 밖).

### A.2 하지 말 것

- 청크 텍스트 목록(`st.text_area` 루프)은 그대로 둔다 — 대체하지 않고
  그래프를 "추가"만 한다.
- 새 시각화 라이브러리 설치 금지(§A.1 참고).
- `core/chunking_optimizer.py`, `core/processing.py` 수정 금지 —
  이번 Task는 UI 표시 레이어만 다룬다.
- 저장 포맷(`_save_chunk_snapshot`, `{stem}_chunks_meta.json`) 변경
  금지 — 이미 안정화된 부분(직전 커밋 `6d9d13e`).

### A.3 검증

- `streamlit run dbma_ui.py`로 실행 후, 이미 처리된 문서 하나를 선택해
  "🔍 청킹 미리보기" → "청킹 실행" → 막대그래프가 청크 개수만큼
  막대로 표시되는지 육안 확인.
- 회귀 테스트: `pytest tests/ -q` 전체 실행(이 변경은 UI 레이어라
  기존 단위 테스트에 영향 없어야 정상 — 혹시 깨지면 원인 보고).

---

## B. 문서: 향후 비주얼라이제이션 로드맵 (Mermaid)

### B.1 목적

지금 당장 구현하지 않을 것들까지 포함해서, "앞으로 어떤 시각화를
붙일 계획인지"를 한곳에 정리한다. 구현 착수 여부는 별도 Task Order로
결정하며, 이 문서 자체는 백로그 + 다이어그램 스케치 역할만 한다.

### B.2 신규 파일: `docs/VISUALIZATION_ROADMAP.md`

아래 구조로 작성(항목 내용은 예시 — C1이 실제 코드/파이프라인 구조를
`DBMA_ARCHITECTURE_MAP.md`, `docs/ARCHITECTURE_DIAGRAM.md` 참고해 맞춰
쓸 것, 근거 없이 지어내지 말 것):

```markdown
# DBMA 비주얼라이제이션 로드맵

## 완료
- [x] 청킹 미리보기 — 청크 길이 막대그래프 (2026-07-26, C1 Task Order 015)

## 계획 중 (우선순위 순)
- [ ] 청크 품질 히트맵 — 문서별 avg_noise/avg_dup을 표로 색상 강조
- [ ] 검색 결과 스코어 분포 — retrieval 단계 relevance score 히스토그램
- [ ] 파이프라인 전체 흐름도 (Mermaid, 아래 예시)

## 파이프라인 흐름 (Mermaid)

\`\`\`mermaid
flowchart LR
    A[원본 문서] --> B[추출]
    B --> C[정제]
    C --> D[청킹]
    D --> E[저장]
    E --> F[임베딩]
    F --> G[검색]
    G --> H[생성]
    H --> I[평가]
\`\`\`

(주: 이 흐름도는 CLAUDE.md의 "파이프라인 순서" 섹션과 반드시 일치시킬
것 — 불일치하면 CLAUDE.md 쪽이 기준.)
```

- Mermaid는 GitHub/VS Code 미리보기에서 렌더링되는 마크다운 코드
  블록으로만 사용한다 — Streamlit 앱 안에 Mermaid를 렌더링하는 신규
  컴포넌트(`streamlit-mermaid` 등)를 설치하지 않는다(§A.1과 동일
  이유 — 범위 밖, 필요해지면 별도 Task Order로 논의).
- "계획 중" 항목은 실제로 사용자/CUE가 언급한 것만 적을 것 — 임의로
  기능을 지어내 백로그에 넣지 말 것.

### B.3 하지 말 것

- 이 문서 작성만으로 §B.2의 "계획 중" 항목을 구현하지 않는다 —
  로드맵 정리 Task이지 구현 Task가 아니다.

---

## 완료 후

- 변경/신규 파일 목록, `pytest tests/ -q` 결과, 스크린샷(가능하면)을
  짧은 md로 `docs/agents/c1/` 아래 남길 것(파일명 자유, 예:
  `C1-TASK-ORDER-015-COMPLETE.md`).
- CUE 검토 요청 — CUE가 실제 코드 diff와 결과를 재검증한 뒤 커밋한다
  (C1이 직접 커밋하지 않음).

## 원칙 재확인

- "이미 존재합니다"라고 주장하기 전에 실제 파일을 열어 확인.
- 파일 경로·함수명·줄 번호는 실제 grep/read 결과에 근거할 것.
- 새 세션으로 시작 — 이 Task Order가 유일한 근거.
- 신규 패키지 설치는 이번 Task 범위에 없음 — 필요하다고 판단되면
  설치 전에 먼저 질문할 것.
</content>
