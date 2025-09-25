"""Development entrypoint for running the Flask API locally.

Usage:
- FLASK_APP=app.main:app flask run --reload
- python -m app.main
"""

from __future__ import annotations

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Simple built-in server for quick smoke testing
    app.run(host="127.0.0.1", port=5000, debug=True)
