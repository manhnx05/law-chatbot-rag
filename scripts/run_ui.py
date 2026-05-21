#!/usr/bin/env python
"""Run Streamlit UI"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    os.system("streamlit run src/ui/app.py")
