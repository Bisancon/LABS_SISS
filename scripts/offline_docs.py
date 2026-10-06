"""Запуск API с Swagger UI, не зависящим от CDN (нужно только для скриншотов
в среде без доступа к cdn.jsdelivr.net). Обычный запуск: uvicorn main:app.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from swagger_ui_bundle import swagger_ui_path

from main import app

app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != "/docs"]
app.mount("/swagger-static", StaticFiles(directory=swagger_ui_path), name="swagger-static")


# Встроенный Swagger UI 4.15.5 понимает только OpenAPI 3.0.x, а FastAPI отдаёт 3.1:
# для скриншотов приводим схему к 3.0 (на сам API это не влияет).
def _to_30(node):
    if isinstance(node, dict):
        any_of = node.get("anyOf")
        if any_of and any(i == {"type": "null"} for i in any_of):
            rest = [i for i in any_of if i != {"type": "null"}]
            if len(rest) == 1:
                node.pop("anyOf")
                node.update(rest[0])
                node["nullable"] = True
        for v in list(node.values()):
            _to_30(v)
    elif isinstance(node, list):
        for v in node:
            _to_30(v)


_orig_openapi = app.openapi


def _openapi_30():
    schema = _orig_openapi()
    if not schema.get("_converted"):
        schema["openapi"] = "3.0.3"
        _to_30(schema)
    return schema


app.openapi = _openapi_30


@app.get("/docs", include_in_schema=False)
def docs():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Agro Scoring API - Swagger UI",
        swagger_js_url="/swagger-static/swagger-ui-bundle.js",
        swagger_css_url="/swagger-static/swagger-ui.css",
    )


if __name__ == "__main__":
    import os
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")), log_level="warning")
