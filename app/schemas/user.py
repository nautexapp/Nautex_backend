from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr


class SchoolInfoResponse(BaseModel):
    id: UUID
    name: str
    info: Optional[dict] = None

    model_config = {"from_attributes": True}


class UserMeResponse(BaseModel):
    id: UUID
    email: EmailStr
    google_id: str
    entra_id: Optional[str] = None
    progress: dict
    school_id: Optional[UUID] = None
    course_id: Optional[UUID] = None
    course_name: Optional[str] = None
    school: Optional[SchoolInfoResponse] = None

    model_config = {"from_attributes": True}


class UserSyncRequest(BaseModel):
    registration_code: Optional[str] = None


class UserSyncResponse(BaseModel):
    created: bool
    user: UserMeResponse


class TestProgressRequest(BaseModel):
    test_id: str
    total_questions: int
    correct_answers: int
