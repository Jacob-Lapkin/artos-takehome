"""Flask app factory and blueprint registration.

Defines `create_app()` to initialize the Flask app, load configuration,
enable CORS, and register route blueprints. Minimal setup for local dev.
"""

from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from app.config import Config, ensure_data_dirs
from app.routes.ingest import ingest_bp
from app.routes.search import search_bp
from app.routes.upload import upload_bp
from app.routes.generate import generate_bp
from app.routes.runs import runs_bp
from app.routes.refine import refine_bp
from app.routes.docs import docs_bp

# Load .env for local dev if available
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


def create_app() -> Flask:
    app = Flask(__name__)
    # Basic config
    app.config.from_object(Config)
    ensure_data_dirs()
    # Allow all origins for local development, including preflight for file upload
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=False,
        expose_headers=["Content-Disposition"],
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "OPTIONS"],
    )

    # Blueprints
    app.register_blueprint(ingest_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(generate_bp)
    app.register_blueprint(runs_bp)
    app.register_blueprint(refine_bp)
    app.register_blueprint(docs_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
