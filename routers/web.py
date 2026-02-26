"""Web routes: HTML pages."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/", name="web_index")
async def index(request: Request):
    """Home with links to chess and admin."""
    templates = request.app.state.templates
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/chess", name="web_chess")
async def chess(request: Request):
    """Chess board and play UI."""
    templates = request.app.state.templates
    return templates.TemplateResponse("chess.html", {"request": request})
