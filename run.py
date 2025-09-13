#!/usr/bin/env python
"""Launch the PDFMagick Streamlit application."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from streamlit.web import cli as stcli

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "src/app.py", "--theme.primaryColor=#FF6B6B"]
    sys.exit(stcli.main())