from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Campus, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email_hash(self, email_hash: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email_hash == email_hash))

    async def first_campus_id(self) -> int | None:
        return await self.session.scalar(select(Campus.id).order_by(Campus.id).limit(1))

    async def create(self, *, email_hash: str, nickname: str, campus_id: int) -> User:
        user = User(email_hash=email_hash, nickname=nickname, campus_id=campus_id)
        self.session.add(user)
        await self.session.commit()
        return user
