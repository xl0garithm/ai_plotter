"""FastAPI dependencies: config, admin auth."""

from __future__ import annotations

import hmac
import hashlib
import logging
from typing import Annotated

from fastapi import Cookie, Request, Response
from fastapi.responses import RedirectResponse

from config import Config

logger = logging.getLogger(__name__)

# Single config instance (set at startup)
_config: Config | None = None


def get_config() -> Config:
    if _config is None:
        raise RuntimeError("Config not initialized")
    return _config


def set_config(c: Config) -> None:
    global _config
    _config = c


ADMIN_COOKIE = "admin"
ADMIN_COOKIE_MAX_AGE = 86400 * 7  # 7 days


def _sign(value: str, secret: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def _make_admin_cookie(secret: str) -> str:
    return _sign("logged_in", secret) + ".logged_in"


def set_admin_cookie(response: Response, config: Config) -> None:
    value = _make_admin_cookie(config.SECRET_KEY)
    response.set_cookie(
        key=ADMIN_COOKIE,
        value=value,
        max_age=ADMIN_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )


def clear_admin_cookie(response: Response) -> None:
    response.delete_cookie(ADMIN_COOKIE)


def is_admin_logged_in(
    admin_cookie: Annotated[str | None, Cookie(alias=ADMIN_COOKIE)] = None,
) -> bool:
    if not admin_cookie:
        return False
    try:
        sig, _ = admin_cookie.split(".", 1)
        expected = _sign("logged_in", get_config().SECRET_KEY)
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


async def require_admin(
    request: Request,
    admin_cookie: Annotated[str | None, Cookie(alias=ADMIN_COOKIE)] = None,
):
    """Dependency: redirect to admin login if not logged in."""
    if not is_admin_logged_in(admin_cookie):
        return RedirectResponse(url="/admin/login", status_code=302)
    return None


def require_admin_api(
    admin_cookie: Annotated[str | None, Cookie(alias=ADMIN_COOKIE)] = None,
) -> None:
    """Dependency: raise 401 if not logged in (for API routes)."""
    if not is_admin_logged_in(admin_cookie):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
