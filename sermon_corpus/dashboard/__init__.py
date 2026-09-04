# DBMA Sermon Corpus - 대시보드 모듈
# 설교 빈도 및 키워드 시각화 대시보드
#
# [버그 수정, 2026-07-22] 존재하지 않는 SermonDashboard 클래스를 import
# 해서 sermon_corpus.dashboard 패키지 전체가 import 시점에 항상
# ImportError로 죽어있었다 — web_app.py는 클래스가 아니라 Streamlit
# 스크립트(함수형, `streamlit run`으로만 실행)라 애초에 이 이름의
# 클래스가 없다. 빈 패키지 마커로 되돌림.