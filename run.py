"""
CineWise Application Launcher
=============================
Starts both the FastAPI backend and Vite React frontend concurrently.
"""

import subprocess
import sys
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

def main():
    print("=" * 60)
    print("  Starting CineWise — IMDb-Style AI Movie Recommender")
    print("=" * 60)
    print("  Backend API:  http://127.0.0.1:8000")
    print("  Frontend UI:  http://localhost:5173")
    print("=" * 60)

    # 1. Start FastAPI backend
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=BASE_DIR
    )

    # Give backend a moment to spin up
    time.sleep(2)

    # 2. Start Vite React frontend
    # Use npx vite dev inside frontend dir
    cmd = "npm run dev" if os.name != "nt" else "cmd.exe /c npm run dev"
    frontend_proc = subprocess.Popen(
        cmd,
        cwd=FRONTEND_DIR,
        shell=True
    )

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down CineWise services...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    main()
