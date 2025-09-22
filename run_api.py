#!/usr/bin/env python
"""Run the FastAPI backend server."""

import sys
import uvicorn
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    print("🚀 Starting PDFMagick API server...")
    print("📄 API docs will be available at: http://localhost:8000/docs")
    print()

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )