"""服务层业务异常。由 app/api/errors.py 统一转成响应壳。"""


class NotFoundError(Exception):
    def __init__(self, what: str, ident: int) -> None:
        super().__init__(f"{what}不存在：id={ident}")
        self.what = what
        self.ident = ident


class AuthError(Exception):
    """401：未登录、token 无效/过期、验证码错误。"""


class BadRequestError(Exception):
    """400：请求语义上不合法（如非校园邮箱）。"""


class ForbiddenError(Exception):
    """403：已登录但无权操作该资源。"""


class ConflictError(Exception):
    """409：与现有状态冲突（如当天已评价过该菜）。"""


class RateLimitError(Exception):
    """429：超出频率/配额限制。"""
