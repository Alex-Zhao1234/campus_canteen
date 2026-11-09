from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"code": 0, "data": {"status": "ok"}, "msg": "ok"}
