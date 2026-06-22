import os
import warnings
import logging

APP_VERSION = "0.3.1"
APP_NAME = "DBMA 파싱 파이프라인"

warnings.filterwarnings("ignore", category=UserWarning)
logging.getLogger().setLevel(logging.ERROR)

# core/config.py 파일의 실제 위치: /Users/David/DBMA/core/config.py
# 여기서 한 단계 올라가면 프로젝트 루트: /Users/David/DBMA
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CORE_DIR)

DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_RAW_DIR = os.path.join(DATA_DIR, "RAW")
DEFAULT_OUTPUT_DIR = os.path.join(DATA_DIR, "제련완성본")

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".docx",
    ".epub",
    ".html",
    ".htm",
    ".rtf",
}
