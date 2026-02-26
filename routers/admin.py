"""Admin routes: login, dashboard."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from dependencies import (
    clear_admin_cookie,
    get_config,
    require_admin,
    set_admin_cookie,
)

router = APIRouter()


def _templates(request: Request):
    return request.app.state.templates


@router.get("/login", name="admin_login")
async def login_get(request: Request):
    templates = _templates(request)
    return templates.TemplateResponse(
        "admin_login.html",
        {"request": request, "flash": None},
    )


@router.post("/login", name="admin_login_post")
async def login_post(request: Request):
    form = await request.form()
    pin = form.get("pin", "")
    config = get_config()
    if pin == config.ADMIN_PIN:
        response = RedirectResponse(url="/admin/", status_code=302)
        set_admin_cookie(response, config)
        return response
    templates = _templates(request)
    return templates.TemplateResponse(
        "admin_login.html",
        {"request": request, "flash": "Invalid PIN"},
    )


@router.get("/logout", name="admin_logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    clear_admin_cookie(response)
    return response


@router.get("/", name="admin_dashboard")
async def dashboard(request: Request, _: None = Depends(require_admin)):
    config = get_config()
    enable_manual_upload = getattr(config, "ENABLE_MANUAL_UPLOAD", False)
    templates = _templates(request)
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "enable_manual_upload": enable_manual_upload,
        },
    )
