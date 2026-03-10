"""Web routes: HTML pages."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/", name="web_index")
async def index(request: Request):
    """Home with links to chess and admin."""
    templates = request.app.state.templates
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/chess-legacy", name="web_chess_legacy")
async def chess_legacy(request: Request):
    """Legacy chess board and play UI (Stockfish backend)."""
    templates = request.app.state.templates
    return templates.TemplateResponse("chess.html", {"request": request})
