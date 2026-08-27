from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import WEBAPP_DIR

app = FastAPI(title="Mini Stadion", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")
app.mount("/assets", StaticFiles(directory=str(WEBAPP_DIR / "assets")), name="assets")
app.mount("/data", StaticFiles(directory=str(WEBAPP_DIR / "data")), name="data")


@app.get("/config.js")
async def config_js() -> FileResponse:
    return FileResponse(WEBAPP_DIR / "config.js", media_type="text/javascript")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEBAPP_DIR / "index.html")
