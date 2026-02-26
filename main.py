"""FastAPI application for the AI plotter."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import Config
from dependencies import set_config
from services.database import init_db

from routers import admin, api, web

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = Config()
    Config.ensure_directories()
    init_db(config.DATABASE_URL)
    set_config(config)
    app.state.templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    yield


app = FastAPI(
    title="Chess Plotter",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(web.router, tags=["web"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(api.router, prefix="/api", tags=["api"])
