from fastapi import APIRouter

from app.api.deps import AuthServiceDep
from app.schemas.auth import (
    AccessTokenOut,
    RefreshIn,
    SendCodeIn,
    SendCodeOut,
    TokenOut,
    UserOut,
    VerifyIn,
)
from app.schemas.common import Envelope, ok

router = APIRouter(prefix="/auth")


@router.post("/send-code", response_model=Envelope[SendCodeOut])
async def send_code(body: SendCodeIn, svc: AuthServiceDep):
    result = svc.send_code(body.email)
    return ok(SendCodeOut(sent=result.sent, dev_code=result.dev_code))


@router.post("/verify", response_model=Envelope[TokenOut])
async def verify(body: VerifyIn, svc: AuthServiceDep):
    result = await svc.verify(body.email, body.code)
    return ok(
        TokenOut(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            user=UserOut.model_validate(result.user),
        )
    )


@router.post("/refresh", response_model=Envelope[AccessTokenOut])
async def refresh(body: RefreshIn, svc: AuthServiceDep):
    return ok(AccessTokenOut(access_token=await svc.refresh(body.refresh_token)))
