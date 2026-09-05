"""
run.py
======
Single-command launcher for the AI Firewall application.

Usage:
    python run.py
"""

import uvicorn

if __name__ == "__main__":
    print("[INFO] Starting AI Firewall server on http://localhost:8000 ...")
    print("  - Chatbot UI (1,000-char safe limit): http://localhost:8000/chat")
    print("  - Security Operations & Admin Suite:  http://localhost:8000/")
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
