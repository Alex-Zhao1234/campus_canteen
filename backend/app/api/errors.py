"""把异常统一转成响应壳 {code, data: null, msg}。"""

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

from app.services.errors import (
    AuthError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
)


def _envelope(status: int, msg: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": status, "data": None, "msg": msg})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return _envelope(404, str(exc))

    @app.exception_handler(AuthError)
    async def _auth(_: Request, exc: AuthError) -> JSONResponse:
        return _envelope(401, str(exc))

    @app.exception_handler(BadRequestError)
    async def _bad_request(_: Request, exc: BadRequestError) -> JSONResponse:
        return _envelope(400, str(exc))

    @app.exception_handler(ForbiddenError)
    async def _forbidden(_: Request, exc: ForbiddenError) -> JSONResponse:
        return _envelope(403, str(exc))

    @app.exception_handler(ConflictError)
    async def _conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return _envelope(409, str(exc))

    @app.exception_handler(RateLimitError)
    async def _rate_limit(_: Request, exc: RateLimitError) -> JSONResponse:
        return _envelope(429, str(exc))

    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException) -> JSONResponse:
        return _envelope(exc.status_code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _envelope(422, "参数错误：" + "; ".join(str(e["msg"]) for e in exc.errors()))
