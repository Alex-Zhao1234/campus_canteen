"""路由层依赖。依赖链：get_db → get_xxx_service → 路由函数；get_current_user 解析 Bearer token。"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models import User
from app.repositories.org_repo import OrgRepository
from app.repositories.ranking_repo import RankingRepository
from app.repositories.recommend_repo import RecommendRepository
from app.repositories.review_repo import ReviewRepository
from app.repositories.seat_repo import SeatRepository
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService
from app.services.errors import AuthError
from app.services.org_service import OrgService
from app.services.ranking_service import RankingService
from app.services.recommend_service import RecommendService
from app.services.review_service import ReviewService
from app.services.seat_service import SeatService

DbDep = Annotated[AsyncSession, Depends(get_db)]


def get_org_service(db: DbDep) -> OrgService:
    return OrgService(OrgRepository(db))


def get_auth_service(db: DbDep) -> AuthService:
    return AuthService(UserRepository(db))


def get_review_service(db: DbDep) -> ReviewService:
    return ReviewService(ReviewRepository(db))


def get_ranking_service(db: DbDep) -> RankingService:
    return RankingService(RankingRepository(db))


def get_recommend_service(db: DbDep) -> RecommendService:
    return RecommendService(RecommendRepository(db), OrgRepository(db))


def get_seat_service(db: DbDep) -> SeatService:
    return SeatService(SeatRepository(db))


# auto_error=False：没带头时自己抛 AuthError，保证走统一响应壳
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    db: DbDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if creds is None:
        raise AuthError("请先登录")
    try:
        user_id = decode_token(creds.credentials, "access")
    except ValueError as e:
        raise AuthError(str(e)) from e
    user = await UserRepository(db).get(user_id)
    if user is None:
        raise AuthError("用户不存在")
    return user


async def get_optional_user(
    db: DbDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User | None:
    """公开接口的"可选登录"：没带 token 或 token 无效都按游客处理。"""
    if creds is None:
        return None
    try:
        user_id = decode_token(creds.credentials, "access")
    except ValueError:
        return None
    return await UserRepository(db).get(user_id)


# 路由参数直接写 svc: OrgServiceDep / user: CurrentUser 即可
OrgServiceDep = Annotated[OrgService, Depends(get_org_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]
RankingServiceDep = Annotated[RankingService, Depends(get_ranking_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
RecommendServiceDep = Annotated[RecommendService, Depends(get_recommend_service)]
SeatServiceDep = Annotated[SeatService, Depends(get_seat_service)]
