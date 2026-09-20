from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.identity import AuthenticatedUser
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/ai", tags=["Motor de IA"])


@router.get("/")
async def ai_module_placeholder(
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict[str, str]:
    return {
        "status": "not_implemented",
        "message": "El motor de IA se integrará en una fase posterior.",
    }
