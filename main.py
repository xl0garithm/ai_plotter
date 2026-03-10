"""FastAPI application for the AI plotter."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

from config import Config
from dependencies import set_config
from routers import admin, api, web
from services.database import init_db

BASE_DIR = Path(__file__).resolve().parent
NEO_CHESS_DIR = BASE_DIR / "Neo_Chess" / "dist" / "public"


class SPAStaticFiles(StarletteStaticFiles):
    """StaticFiles that serves index.html for non-file paths (SPA fallback)."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as e:
            if e.status_code == 404 and (not path or "." not in path.split("/")[-1]):
                return await super().get_response("index.html", scope)
            raise


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

if NEO_CHESS_DIR.exists():
    app.mount("/chess", SPAStaticFiles(directory=str(NEO_CHESS_DIR), html=True), name="chess")

app.include_router(web.router, tags=["web"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(api.router, prefix="/api", tags=["api"])
