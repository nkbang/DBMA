import streamlit as st
import os
import glob
import shutil
import warnings
import logging
import datetime
import re
import unicodedata
from typing import List, Dict, Optional

from bs4 import BeautifulSoup
from docx import Document
from ebooklib import epub, ITEM_DOCUMENT
from striprtf.striprtf import rtf_to_text

# 