import streamlit as st


def inject_styles() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Noto Serif KR', serif; }
.dbma-header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); border-radius: 12px; padding: 28px 36px; margin-bottom: 24px; border-left: 5px solid #e94560; }
.dbma-header h1 { color: #fff; font-size: 1.8rem; font-weight: 700; margin: 0 0 4px 0; letter-spacing: -0.02em; }
.dbma-header p { color: #a8b2d8; font-size: 0.85rem; margin: 0; font-family: 'JetBrains Mono', monospace; }
.file-table-header { display: grid; grid-template-columns: 40px 1fr 90px 150px 80px; background: #161b22; padding: 9px 12px; font-size: 0.70rem; color: #8b949e; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 0.08em; border: 1px solid #21262d; border-radius: 8px 8px 0 0; }
.file-row { display: grid; grid-template-columns: 40px 1fr 90px 150px 80px; padding: 9px 12px; border: 1px solid #21262d; border-top: none; align-items: center; font-size: 0.80rem; background: #0d1117; }
.file-row:last-child { border-radius: 0 0 8px 8px; }
.file-row:hover { background: #161b22; }
.fname { color: #58a6ff; font-family: 'JetBrains Mono', monospace; font-size: 0.76rem; word-break: break-all; }
.fsize { color: #3fb950; font-family: 'JetBrains Mono', monospace; font-size: 0.74rem; }
.fdate { color: #8b949e; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; }
.fbadge { display: inline-block; background: #1f3a5f; color: #58a6ff; border-radius: 4px; padding: 1px 7px; font-size: 0.66rem; font-family: 'JetBrains Mono', monospace; font-weight: 500; text-align: center; min-width: 54px; }
.stat-row { display: flex; gap: 12px; margin-bottom: 16px; }
.stat-card { flex: 1; background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 13px 17px; }
.stat-label { font-size: 0.67rem; color: #8b949e; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 3px; font-family: 'JetBrains Mono', monospace; }
.stat-value { font-size: 1.35rem; font-weight: 700; color: #e6edf3; font-family: 'JetBrains Mono', monospace; }
.blue { color: #58a6ff; } .green { color: #3fb950; } .orange { color: #d29922; } .red { color: #f85149; }
.log-box { background: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 13px 17px; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #c9d1d9; max-height: 320px; overflow-y: auto; line-height: 1.9; }
.log-ok { color: #3fb950; } .log-warn { color: #d29922; } .log-err { color: #f85149; } .log-info { color: #58a6ff; }
.noise-bar-wrap { background: #21262d; border-radius: 6px; height: 14px; overflow: hidden; margin: 6px 0 2px; }
.noise-bar { height: 14px; border-radius: 6px; transition: width 0.4s; }
.analysis-card { background: #161b22; border: 1px solid #21262d; border-radius: 10px; padding: 16px 20px; margin-bottom: 12px; }
.analysis-card h4 { color: #e6edf3; font-size: 0.9rem; margin: 0 0 10px; font-weight: 600; }
.chunk-box { background: #0d1117; border-left: 3px solid #58a6ff; border-radius: 0 6px 6px 0; padding: 10px 14px; margin: 8px 0; font-family: 'JetBrains Mono', monospace; font-size: 0.73rem; color: #c9d1d9; line-height: 1.7; }
div[data-testid="stButton"] button { background: linear-gradient(135deg, #e94560, #c23152) !important; color: white !important; border: none !important; border-radius: 8px !important; font-family: 'Noto Serif KR', serif !important; font-weight: 600 !important; padding: 10px 28px !important; font-size: 0.95rem !important; }
section[data-testid="stSidebar"] { background: #0d1117; border-right: 1px solid #21262d; }
section[data-testid="stSidebar"] label { color: #c9d1d9 !important; }
section[data-testid="stSidebar"] .stTextInput input, section[data-testid="stSidebar"] .stNumberInput input { background: #161b22 !important; border-color: #30363d !important; color: #e6edf3 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.82rem !important; }
div[data-testid="stCheckbox"] { margin-bottom: 0 !important; padding: 2px 0 !important; }
</style>
""",
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
<div class="dbma-header">
    <h1>DBMA</h1>
    <p>David Bang Ministry Archive · RAG 데이터 정제 시스템 v3.3</p>
</div>
""",
        unsafe_allow_html=True,
    )
