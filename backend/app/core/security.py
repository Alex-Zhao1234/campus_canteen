"""JWT 签发与解码。token 里带 type 区分 access / refresh，二者不可互用。"""

from datetime import UTC, datetime, timedelta
from typing import Literal

from jose import JWTError, jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]


def create_token(user_id: int, token_type: TokenType) -> str:
    settings = get_settings()
    if token_type == "access":
        ttl = timedelta(minutes=settings.access_token_minutes)
    else:
        ttl = timedelta(days=settings.refresh_token_days)
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "type": token_type, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: TokenType) -> int:
    """验签 + 校验类型，返回用户 id。任何问题都抛 ValueError。"""
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
    except JWTError as e:
        raise ValueError("token 无效或已过期") from e
    if payload.get("type") != expected_type:
        raise ValueError(f"需要 {expected_type} token")
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError("token 缺少用户标识") from e
