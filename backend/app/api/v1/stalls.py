from fastapi import APIRouter

from app.api.deps import OrgServiceDep
from app.schemas.common import Envelope, ok
from app.schemas.org import StallDetailOut

router = APIRouter(prefix="/stalls")


@router.get("/{stall_id}", response_model=Envelope[StallDetailOut])
async def get_stall(stall_id: int, svc: OrgServiceDep):
    return ok(await svc.get_stall(stall_id))
