"""Docs routes: GET /docs (Swagger UI) and /openapi.yaml (spec)

Serves the OpenAPI YAML from the repository docs folder and a minimal
Swagger UI page that renders the spec.
"""

from __future__ import annotations

import os
from flask import Blueprint, Response, current_app


docs_bp = Blueprint("docs", __name__)


def _repo_root() -> str:
    # app/routes/docs.py → up two dirs to repo root
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@docs_bp.get("/openapi.yaml")
def openapi_yaml() -> Response:
    path = os.path.join(_repo_root(), "docs", "openapi.yaml")
    if not os.path.exists(path):
        return Response("openapi.yaml not found", status=404)
    with open(path, "rb") as f:
        data = f.read()
    # Swagger UI accepts YAML content; text/yaml is fine
    return Response(data, mimetype="text/yaml")


@docs_bp.get("/docs")
def swagger_ui() -> Response:
    # Minimal Swagger UI using CDN assets; loads spec from /openapi.yaml
    html = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>API Docs | Swagger UI</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
    <style>
      body { margin: 0; padding: 0; }
      #swagger-ui { width: 100%; height: 100vh; }
    </style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.onload = () => {
        window.ui = SwaggerUIBundle({
          url: '/openapi.yaml',
          dom_id: '#swagger-ui',
          presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
          layout: 'BaseLayout',
          deepLinking: true,
          docExpansion: 'none',
          defaultModelsExpandDepth: 0,
        });
      };
    </script>
  </body>
  </html>
    """.strip()
    return Response(html, mimetype="text/html")

