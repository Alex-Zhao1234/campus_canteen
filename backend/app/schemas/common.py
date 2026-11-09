"""统一响应壳 {code, data, msg}，前端 client.ts 按此解析。"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    code: int = 0
    data: T | None = None
    msg: str = "ok"


def ok(data: T) -> Envelope[T]:
    return Envelope[T](data=data)
