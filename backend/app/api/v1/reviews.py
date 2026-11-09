from fastapi import APIRouter

from app.api.deps import CurrentUser, ReviewServiceDep
from app.schemas.common import Envelope, ok
from app.schemas.review import ReviewCreatedOut, ReviewCreateIn, ReviewDeletedOut

router = APIRouter(prefix="/reviews")


@router.post("", status_code=201, response_model=Envelope[ReviewCreatedOut])
async def create_review(body: ReviewCreateIn, user: CurrentUser, svc: ReviewServiceDep):
    return ok(await svc.create(user, body))


@router.delete("/{review_id}", response_model=Envelope[ReviewDeletedOut])
async def delete_review(review_id: int, user: CurrentUser, svc: ReviewServiceDep):
    return ok(await svc.delete(user, review_id))
