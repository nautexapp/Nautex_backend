from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.identity import AuthenticatedUser
from app.db.models import RegistrationCode, User


async def get_user_by_google_id(session: AsyncSession, google_id: str) -> User | None:
    result = await session.execute(
        select(User).options(joinedload(User.school)).where(User.google_id == google_id)
    )
    return result.scalar_one_or_none()


# Alias para compatibilidad
get_user_by_entra_id = get_user_by_google_id


async def sync_user(
    session: AsyncSession,
    identity: AuthenticatedUser,
    registration_code: str | None = None,
) -> tuple[User, bool]:
    user = await get_user_by_google_id(session, identity.google_id)
    if user:
        if user.email != identity.email:
            user.email = identity.email
        return user, False

    # Usuario nuevo — buscar y vincular el código de escuela y curso si se proporcionó
    school_id = None
    course_id = None
    if registration_code:
        code_upper = registration_code.strip().upper()
        result = await session.execute(
            select(RegistrationCode).where(
                RegistrationCode.code == code_upper,
                RegistrationCode.is_used == False,  # noqa: E712
            )
        )
        reg_code = result.scalar_one_or_none()
        if reg_code:
            school_id = reg_code.school_id
            course_id = reg_code.course_id
            reg_code.is_used = True

    user = User(
        google_id=identity.google_id,
        email=identity.email,
        progress={},
        school_id=school_id,
        course_id=course_id,
    )
    session.add(user)
    await session.flush()
    return user, True


async def update_test_progress(
    session: AsyncSession, user: User, test_id: str, total_questions: int, correct_answers: int
) -> User:
    progress = user.progress or {}
    tests_prog = progress.get("tests", {
        "completed_test_ids": [],
        "total_questions_answered": 0,
        "total_correct_answers": 0,
    })
    
    # Guardar ID del test si no estaba registrado
    if test_id not in tests_prog["completed_test_ids"]:
        tests_prog["completed_test_ids"].append(test_id)
        
    tests_prog["total_questions_answered"] += total_questions
    tests_prog["total_correct_answers"] += correct_answers
    
    progress["tests"] = tests_prog
    
    user.progress = progress
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(user, "progress")
    
    await session.commit()
    return user
