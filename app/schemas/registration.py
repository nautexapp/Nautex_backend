from uuid import UUID

from pydantic import BaseModel, Field


class VerifyCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100, description="Código de escuela")


class VerifyCodeResponse(BaseModel):
    valid: bool
    school_name: str | None = None
    course_id: UUID | None = None
    course_name: str | None = None
    message: str | None = None
