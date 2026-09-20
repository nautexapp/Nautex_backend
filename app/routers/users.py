from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.identity import AuthenticatedUser
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.schemas.user import UserMeResponse, UserSyncRequest, UserSyncResponse
from app.services.users import get_user_by_entra_id, sync_user

router = APIRouter(prefix="/users", tags=["Usuarios y saldo"])


@router.post("/sync", response_model=UserSyncResponse)
async def sync_current_user(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: UserSyncRequest | None = None,
) -> UserSyncResponse:
    registration_code = body.registration_code if body else None
    user, created = await sync_user(db, identity, registration_code=registration_code)
    return UserSyncResponse(
        created=created,
        user=UserMeResponse.model_validate(user),
    )


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserMeResponse:
    user = await get_user_by_entra_id(db, identity.entra_id)
    if not user:
        user, _ = await sync_user(db, identity)
    return UserMeResponse.model_validate(user)


from app.schemas.user import TestProgressRequest

@router.put("/progress/tests", response_model=UserMeResponse)
async def update_progress_tests(
    body: TestProgressRequest,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserMeResponse:
    from app.services.users import update_test_progress
    user = await get_user_by_entra_id(db, identity.entra_id)
    if not user:
        user, _ = await sync_user(db, identity)
    
    user = await update_test_progress(
        db, user, test_id=body.test_id, total_questions=body.total_questions, correct_answers=body.correct_answers
    )
    return UserMeResponse.model_validate(user)

