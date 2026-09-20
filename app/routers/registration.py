from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import RegistrationCode
from app.db.session import get_db
from app.schemas.registration import VerifyCodeRequest, VerifyCodeResponse

router = APIRouter(prefix="/registration", tags=["Registro de alumnos"])


@router.post("/verify-code", response_model=VerifyCodeResponse)
async def verify_registration_code(
    body: VerifyCodeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VerifyCodeResponse:
    """
    Endpoint público (sin autenticación) que verifica si un código de escuela
    existe y no ha sido usado. Devuelve el nombre de la escuela y del curso si es válido.
    """
    result = await db.execute(
        select(RegistrationCode)
        .where(RegistrationCode.code == body.code.strip().upper())
        .options(
            selectinload(RegistrationCode.school),
            selectinload(RegistrationCode.course),
        )
    )
    reg_code = result.scalar_one_or_none()

    if reg_code is None or reg_code.is_used:
        return VerifyCodeResponse(
            valid=False,
            message="El código no es válido o ya ha sido utilizado.",
        )

    school_name = reg_code.school.name if reg_code.school else None
    course_id = reg_code.course_id
    course_name = reg_code.course.name if reg_code.course else None

    return VerifyCodeResponse(
        valid=True,
        school_name=school_name,
        course_id=course_id,
        course_name=course_name,
    )
