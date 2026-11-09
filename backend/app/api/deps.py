"""路由层依赖。依赖链：get_db → get_org_service → 路由函数。"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.org_repo import OrgRepository
from app.services.org_service import OrgService


def get_org_service(db: Annotated[AsyncSession, Depends(get_db)]) -> OrgService:
    return OrgService(OrgRepository(db))


# 路由参数直接写 svc: OrgServiceDep 即可
OrgServiceDep = Annotated[OrgService, Depends(get_org_service)]
