import os
import sys
from pathlib import Path

# Project root = parent of `api/`
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app  # Flask instance from app.py