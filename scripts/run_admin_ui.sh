#!/bin/bash
# 관리자 화면(Processing/Monitor) 미리보기용 임시 실행 스크립트.
export NAE_ADMIN_MODE=1
exec /Users/David/envs/dbma311/bin/streamlit run dbma_ui.py --server.headless true
