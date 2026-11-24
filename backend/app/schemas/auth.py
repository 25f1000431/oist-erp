from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    login_id: str = Field(min_length=1, max_length=180)
    password: str = Field(min_length=1, max_length=256)


class UserSummary(BaseModel):
    id: int
    role: str
    login_id: str
    email: str | None
    department_id: int

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: UserSummary
