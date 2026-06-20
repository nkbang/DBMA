import os
import warnings
import logging
import streamlit as st

os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", message=".*__path__.*")
logging.getLogger("transformers").setLevel(logging.ERROR)

st.set_page_config(
    page_title="DBMA 파싱 파이프라인",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_RAW_DIR = os.path.join(BASE_DIR, "data", "RAW")
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "data", "제련완성본")
SUPPORTED_EXTENSIONS = [".pdf", ".txt", ".md", ".docx", ".epub", ".html", ".htm", ".rtf"]
