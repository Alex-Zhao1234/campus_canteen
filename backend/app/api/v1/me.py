from fastapi import APIRouter

from app.api.deps import CurrentUser, ReviewServiceDep
from app.schemas.auth import UserOut
from app.schemas.common import Envelope, ok
from app.schemas.review import MyReviewOut

router = APIRouter(prefix="/me")


@router.get("", response_model=Envelope[UserOut])
async def me(user: CurrentUser):
    return ok(UserOut.model_validate(user))


@router.get("/reviews", response_model=Envelope[list[MyReviewOut]])
async def my_reviews(user: CurrentUser, svc: ReviewServiceDep):
    return ok(await svc.list_mine(user))
