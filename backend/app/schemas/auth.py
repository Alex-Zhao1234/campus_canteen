from pydantic import BaseModel, ConfigDict, Field


class SendCodeIn(BaseModel):
    email: str = Field(min_length=3, max_length=100)


class SendCodeOut(BaseModel):
    sent: bool
    dev_code: str | None = None


class VerifyIn(BaseModel):
    email: str = Field(min_length=3, max_length=100)
    code: str = Field(min_length=6, max_length=6)


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
