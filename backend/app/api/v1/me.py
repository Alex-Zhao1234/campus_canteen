from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.auth import UserOut
from app.schemas.common import Envelope, ok

router = APIRouter(prefix="/me")


@router.get("", response_model=Envelope[UserOut])
async def me(user: CurrentUser):
    return ok(UserOut.model_validate(user))
