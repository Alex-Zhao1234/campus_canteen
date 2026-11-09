"""邮箱验证码登录。

验证码存进程内字典（MVP 单进程），10 分钟过期，错 5 次作废，验证成功即销毁。
邮箱只以 sha256 哈希落库。
"""

import hashlib
import secrets
import time
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.core.security import create_token, decode_token
from app.models import User
from app.repositories.user_repo import UserRepository
from app.services.errors import AuthError, BadRequestError

CODE_TTL_SECONDS = 600
MAX_ATTEMPTS = 5


@dataclass
class _Entry:
    code: str
    expires_at: float
    attempts: int = 0


@dataclass
class CodeStore:
    _data: dict[str, _Entry] = field(default_factory=dict)

    def issue(self, email: str) -> str:
        code = f"{secrets.randbelow(10**6):06d}"
        self._data[email] = _Entry(code=code, expires_at=time.time() + CODE_TTL_SECONDS)
        return code

    def verify(self, email: str, code: str) -> bool:
        entry = self._data.get(email)
        if entry is None:
            return False
        if time.time() > entry.expires_at:
            del self._data[email]
            return False
        entry.attempts += 1
        if entry.attempts > MAX_ATTEMPTS:
            del self._data[email]
            return False
        if not secrets.compare_digest(entry.code, code):
            return False
        del self._data[email]  # 一次性
        return True

    def clear(self) -> None:
        self._data.clear()


code_store = CodeStore()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_email(email: str) -> str:
    return hashlib.sha256(normalize_email(email).encode()).hexdigest()


@dataclass
class SendCodeResult:
    sent: bool
    dev_code: str | None


@dataclass
class LoginResult:
    access_token: str
    refresh_token: str
    user: User


class AuthService:
    def __init__(self, users: UserRepository, store: CodeStore = code_store) -> None:
        self.users = users
        self.store = store

    def send_code(self, email: str) -> SendCodeResult:
        email = normalize_email(email)
        settings = get_settings()
        domain = email.rsplit("@", 1)[-1] if "@" in email else ""
        if not any(
            domain == d or domain.endswith("." + d) for d in settings.allowed_email_domain_list
        ):
            raise BadRequestError("请使用校园邮箱登录")
        code = self.store.issue(email)
        # 真实邮件发送在此接入；MVP 开发模式直接回传
        return SendCodeResult(sent=True, dev_code=code if settings.auth_echo_code else None)

    async def verify(self, email: str, code: str) -> LoginResult:
        email = normalize_email(email)
        if not self.store.verify(email, code):
            raise AuthError("验证码错误或已过期")
        user = await self.users.get_by_email_hash(hash_email(email))
        if user is None:
            campus_id = await self.users.first_campus_id()
            if campus_id is None:
                raise BadRequestError("系统尚未初始化校区，请先导入种子数据")
            nickname = f"同学#{secrets.randbelow(10**4):04d}"
            user = await self.users.create(
                email_hash=hash_email(email), nickname=nickname, campus_id=campus_id
            )
        return LoginResult(
            access_token=create_token(user.id, "access"),
            refresh_token=create_token(user.id, "refresh"),
            user=user,
        )

    async def refresh(self, refresh_token: str) -> str:
        try:
            user_id = decode_token(refresh_token, "refresh")
        except ValueError as e:
            raise AuthError(str(e)) from e
        if await self.users.get(user_id) is None:
            raise AuthError("用户不存在")
        return create_token(user_id, "access")
