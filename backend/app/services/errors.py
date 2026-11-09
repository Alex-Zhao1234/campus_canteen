"""服务层业务异常。由 app/api/errors.py 统一转成响应壳。"""


class NotFoundError(Exception):
    def __init__(self, what: str, ident: int) -> None:
        super().__init__(f"{what}不存在：id={ident}")
        self.what = what
        self.ident = ident
