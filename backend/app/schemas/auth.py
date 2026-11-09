from pydantic import BaseModel, ConfigDict, Field


class SendCodeIn(BaseModel):
    email: str = Field(min_length=3, max_length=100)


class SendCodeOut(BaseModel):
    sent: bool
    # false 时前端直接调 verify（不带 code）即可登录
    code_required: bool = True
    dev_code: str | None = None


class VerifyIn(BaseModel):
    email: str = Field(min_length=3, max_length=100)
    # AUTH_CODE_REQUIRED=false 时可省略
    code: str | None = Field(default=None, min_length=6, max_length=6)


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campus_id: int
    nickname: str
    trust_score: float


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class AccessTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
