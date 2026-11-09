from fastapi import APIRouter

from app.api.v1 import auth, canteens, dishes, health, me, stalls

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(canteens.router, tags=["canteens"])
api_router.include_router(stalls.router, tags=["stalls"])
api_router.include_router(dishes.router, tags=["dishes"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(me.router, tags=["me"])
# 后续：reviews / rankings / recommend
