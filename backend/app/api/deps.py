"""路由层依赖。依赖链：get_db → get_xxx_service → 路由函数；get_current_user 解析 Bearer token。"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models import User
from app.repositories.org_repo import OrgRepository
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService
from app.services.errors import AuthError
from app.services.org_service import OrgService

DbDep = Annotated[AsyncSession, Depends(get_db)]


def get_org_service(db: DbDep) -> OrgService:
    return OrgService(OrgRepository(db))


def get_auth_service(db: DbDep) -> AuthService:
    return AuthService(UserRepository(db))


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


# 路由参数直接写 svc: OrgServiceDep / user: CurrentUser 即可
OrgServiceDep = Annotated[OrgService, Depends(get_org_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]
