#!/usr/bin/env python
"""Run the new PDFMagick stack (FastAPI + Vue)."""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path


class NewStackRunner:
    def __init__(self):
        self.processes = []

    def start_api(self):
        """Start the FastAPI backend."""
        print("🚀 Starting FastAPI backend on http://localhost:8000")
        cmd = [sys.executable, "run_api.py"]
        proc = subprocess.Popen(cmd, cwd=Path(__file__).parent)
        self.processes.append(("API", proc))

    def start_frontend(self):
        """Start the Vue/Nuxt frontend."""
        web_dir = Path(__file__).parent / "web"

        # Check if node_modules exists
        if not (web_dir / "node_modules").exists():
            print("📦 Installing Vue/Nuxt dependencies (first time setup)...")
            result = subprocess.run(["npm", "install"], cwd=web_dir)
            if result.returncode != 0:
                print("❌ Failed to install dependencies")
                return None

        print("💚 Starting Vue frontend on http://localhost:3000")
        # Change to web directory and run npm
        proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=web_dir,
            env={**os.environ, 'NODE_ENV': 'development'}
        )
        self.processes.append(("Frontend", proc))
        return proc

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n🛑 Shutting down services...")
        self.shutdown()
        sys.exit(0)

    def shutdown(self):
        """Terminate all processes."""
        for name, proc in self.processes:
            print(f"  Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def run(self):
        """Run the new stack."""
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        print("=" * 60)
        print("🎨 PDFMagick - New Stack")
        print("=" * 60)
        print()

        try:
            # Start API first
            self.start_api()
            time.sleep(2)  # Give API time to start

            # Start frontend
            if self.start_frontend() is None:
                self.shutdown()
                return

            print()
            print("=" * 60)
            print("✅ All services started successfully!")
            print()
            print("Available at:")
            print("  💚 Vue App:    http://localhost:3000")
            print("  🚀 API:        http://localhost:8000")
            print("  📄 API Docs:   http://localhost:8000/docs")
            print()
            print("Press Ctrl+C to stop all services")
            print("=" * 60)

            # Keep running and monitor processes
            while True:
                time.sleep(1)
                for name, proc in self.processes:
                    if proc.poll() is not None:
                        print(f"\n⚠️  {name} has stopped unexpectedly!")
                        self.shutdown()
                        sys.exit(1)

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.shutdown()


if __name__ == "__main__":
    runner = NewStackRunner()
    runner.run()