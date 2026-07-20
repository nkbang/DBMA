---
name: streamlit-ui
description: "DBMA Streamlit UI 개발 규칙: 탭 구조 유지, 상태 명시, 한글 UI 메시지, 에러 표시, Mac 친화적 흐름."
applyTo: "ui/**/*.py"
---

# DBMA Streamlit UI 개발 규칙

## UI 아키텍처

### 탭 구조
```
메인 탭
├── 📄 문서 업로드
├── 🔍 검색
├── 💬 생성
├── 📊 평가
└── ⚙️ 설정
```

각 탭은 독립적인 함수로 관리:
```python
def render_upload_tab():
    """문서 업로드 탭 렌더링."""

def render_search_tab():
    """검색 탭 렌더링."""

def render_generation_tab():
    """생성 탭 렌더링."""
```

---

## UI 개발 규칙

### 1. 상태 표시
```python
import streamlit as st

# ✓ 좋음: 명확한 상태 표시
if "processing" not in st.session_state:
    st.session_state.processing = False

st.status("처리 중...", state="running")  # 진행 중
st.success("완료!")                         # 완료
st.error("오류 발생")                      # 오류
st.warning("주의")                         # 경고
```

### 2. 한글 UI 메시지
```python
# ✓ 한글 UI 메시지
st.header("📄 문서 업로드")
st.write("지원되는 형식: PDF, DOCX, TXT")

# ✗ 영어 메시지
st.header("Document Upload")
```

### 3. 탭 제어 (필요 시 비활성화)
```python
# 처리 중일 때 다른 탭 비활성화
if st.session_state.get("processing", False):
    st.warning("처리 중입니다. 완료될 때까지 대기하세요.")
    # 다른 입력 위젯을 disabled=True로 설정
else:
    # 일반 UI 표시
```

---

## 탭별 개발 규칙

### 📄 문서 업로드 탭
```python
def render_upload_tab():
    """문서 업로드 및 처리."""
    
    st.header("📄 문서 업로드")
    
    uploaded_file = st.file_uploader(
        "문서 선택",
        type=["pdf", "docx", "txt"],
        help="신학 문서를 선택하세요 (PDF/DOCX/TXT)"
    )
    
    if uploaded_file:
        st.info(f"선택됨: {uploaded_file.name}")
        
        if st.button("처리 시작"):
            st.session_state.processing = True
            try:
                # 처리 로직
                logger.info("[ui:upload] processing: %s", uploaded_file.name)
                result = process_document(uploaded_file)
                st.success("처리 완료!")
                st.session_state.processing = False
            except Exception as e:
                st.error(f"처리 실패: {str(e)}")
                logger.error("[ui:upload] failed: %s", str(e))
```

### 🔍 검색 탭
```python
def render_search_tab():
    """쿼리 검색 및 결과 표시."""
    
    st.header("🔍 검색")
    
    query = st.text_input(
        "질문 입력",
        placeholder="신학 용어 또는 개념에 대해 물어보세요",
        help="한글 또는 영문 입력 가능"
    )
    
    if query:
        logger.info("[ui:search] query: %s", query)
        
        results = retrieve_documents(query)
        
        if results:
            for i, result in enumerate(results, 1):
                st.subheader(f"결과 {i}")
                st.write(result["text"])
                st.caption(f"유사도: {result['score']:.2%}")
        else:
            st.info("관련된 문서가 없습니다.")
```

### 💬 생성 탭
```python
def render_generation_tab():
    """RAG 기반 응답 생성."""
    
    st.header("💬 응답 생성")
    
    question = st.text_area(
        "질문",
        placeholder="자세한 질문을 입력하세요"
    )
    
    if st.button("응답 생성"):
        st.session_state.processing = True
        
        with st.spinner("응답 생성 중..."):
            logger.info("[ui:generation] question: %s", question)
            response = generate_response(question)
            
            st.session_state.processing = False
            st.markdown(response)
            
            st.info(f"생성 시간: {elapsed_time:.1f}초")
```

### 📊 평가 탭
```python
def render_evaluation_tab():
    """RAG 성능 평가."""
    
    st.header("📊 평가")
    
    st.metric("검색 정확도", "85.2%", "+2.1%")
    st.metric("응답 품질", "4.5 / 5", "")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("정밀도")
        st.progress(0.87)
    with col2:
        st.write("재현율")
        st.progress(0.82)
```

### ⚙️ 설정 탭
```python
def render_settings_tab():
    """시스템 설정."""
    
    st.header("⚙️ 설정")
    
    with st.form("settings_form"):
        chunk_size = st.slider(
            "청크 크기",
            min_value=500,
            max_value=2000,
            value=1200,
            step=100
        )
        
        overlap = st.slider(
            "청크 겹침",
            min_value=0,
            max_value=500,
            value=200,
            step=50
        )
        
        top_k = st.slider(
            "상위 K개",
            min_value=1,
            max_value=20,
            value=5
        )
        
        if st.form_submit_button("저장"):
            save_settings({
                "chunk_size": chunk_size,
                "overlap": overlap,
                "top_k": top_k
            })
            st.success("설정이 저장되었습니다!")
            logger.info("[ui:settings] saved: chunk_size=%d", chunk_size)
```

---

## 에러 처리

```python
try:
    result = process_document(file)
except FileNotFoundError:
    st.error("파일을 찾을 수 없습니다.")
    logger.error("[ui] file not found: %s", file)
except ValueError as e:
    st.error(f"입력 오류: {str(e)}")
    logger.error("[ui] input error: %s", str(e))
except Exception as e:
    st.error("예상치 못한 오류가 발생했습니다.")
    logger.error("[ui] unexpected error: %s", str(e), exc_info=True)
```

---

## Mac 친화적 흐름

- 드래그 앤 드롭 지원
- 파일 선택 다이얼로그는 Mac 표준 UI 사용
- Cmd+S (저장) 같은 단축키 인식
- 터미널에서 `streamlit run dbma_ui.py`로 실행 (`dbma.py`는 archive/legacy/dbma.py로 이동 완료되어 더 이상 프로젝트 루트에 존재하지 않음, production 실행은 `dbma_ui.py`→`ui/app.py` 사용)

---

## 성능 최적화

```python
# 캐싱 사용
@st.cache_data
def load_embeddings():
    """임베딩 모델 로드 (캐싱)."""
    return load_model()

@st.cache_resource
def get_database():
    """벡터DB 연결 (리소스 캐싱)."""
    return connect_chroma()
```

---

## 테스트

```python
# UI 테스트 (streamlit testing framework)
def test_upload_tab():
    """업로드 탭 테스트."""
    # Streamlit 테스트 방식 참고
```

---

## 금지 사항 (Streamlit)

❌ **절대 금지**
- 무한 루프 또는 블로킹 작업 (progress bar 또는 spinner 사용)
- 전역 상태 변경 없이 session_state 사용
- 영문 UI 메시지 (한글 필수)
- 오류 무시: 항상 st.error() 또는 st.warning() 표시
