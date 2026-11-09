from fastapi import APIRouter

from app.api.deps import ReviewServiceDep
from app.schemas.common import Envelope, ok
from app.schemas.review import TagOut

router = APIRouter(prefix="/tags")


@router.get("", response_model=Envelope[list[TagOut]])
async def list_tags(svc: ReviewServiceDep):
    return ok(await svc.list_tags())
