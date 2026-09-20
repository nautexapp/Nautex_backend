import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.identity import AuthenticatedUser
from app.db.models import Course, User
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.services.storage import generate_academy_read_sas

router = APIRouter(prefix="/courses", tags=["Cursos"])


class CourseResponse(BaseModel):
    id: uuid.UUID
    name: str
    documents: dict | None = None

    model_config = {"from_attributes": True}


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: uuid.UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourseResponse:
    """
    Devuelve los datos del curso (nombre + índice de documentos).
    Solo accesible por el alumno matriculado en ese curso.
    """
    # Verificar que el usuario tiene acceso a este curso
    user_result = await db.execute(select(User).where(User.google_id == current_user.google_id))
    db_user = user_result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=403, detail="Usuario no encontrado")

    if db_user.course_id != course_id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este curso")

    course_result = await db.execute(select(Course).where(Course.id == course_id))
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    return CourseResponse(id=course.id, name=course.name, documents=course.documents)


@router.get("/{course_id}/documents/url")
async def get_course_document_url(
    course_id: uuid.UUID,
    section: str,
    file: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    Genera una URL SAS temporal de lectura para un documento del curso en Azure Blob Storage.
    Parámetros query: section (apuntes|examenes|documentos), file (ruta del fichero)
    """
    # Verificar acceso del usuario al curso
    user_result = await db.execute(select(User).where(User.google_id == current_user.google_id))
    db_user = user_result.scalar_one_or_none()
    if not db_user or db_user.course_id != course_id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este curso")

    # Sanity check: bloquear path traversal
    segments = file.replace("\\", "/").split("/")
    if any(s in ("", ".", "..") for s in segments):
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido")
    file = "/".join(segments)

    # Obtener el curso para saber el folder_reference
    course_result = await db.execute(select(Course).where(Course.id == course_id))
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Construir ruta usando folder_reference si existe, si no usar course_id
    base_folder = course.folder_reference or str(course_id)
    # Capitalizamos la sección porque en Azure las carpetas están creadas como Tests, Apuntes, etc.
    blob_path = f"{base_folder}/{section.capitalize()}/{file}"

    url = generate_academy_read_sas(settings, blob_path=blob_path)
    return {"url": url, "expires_in_seconds": settings.academy_sas_expiry_minutes * 60}


@router.get("/{course_id}/tests/{test_id}/questions-url")
async def get_course_test_questions_url(
    course_id: uuid.UUID,
    test_id: int,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    Genera una URL SAS temporal para el archivo JSON de preguntas de un test del curso.
    """
    # Verificar acceso del usuario al curso
    user_result = await db.execute(select(User).where(User.google_id == current_user.google_id))
    db_user = user_result.scalar_one_or_none()
    if not db_user or db_user.course_id != course_id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este curso")

    # Obtener el curso para leer el índice de tests
    course_result = await db.execute(select(Course).where(Course.id == course_id))
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    documents = course.documents or {}
    tests = documents.get("tests", [])
    test_info = next((t for t in tests if t.get("id") == test_id), None)
    if not test_info:
        raise HTTPException(status_code=404, detail="Test no encontrado en el curso")

    file_name = test_info.get("file")
    if not file_name:
        raise HTTPException(status_code=404, detail="El test no tiene archivo de preguntas asociado")

    # Sanity check
    segments = file_name.replace("\\", "/").split("/")
    if any(s in ("", ".", "..") for s in segments):
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido")
    file_name = "/".join(segments)

    base_folder = course.folder_reference or str(course_id)
    # Usamos Tests con mayúscula para coincidir con Azure
    blob_path = f"{base_folder}/Tests/{file_name}"
    url = generate_academy_read_sas(settings, blob_path=blob_path)
    return {"url": url, "expires_in_seconds": settings.academy_sas_expiry_minutes * 60}


@router.get("/{course_id}/examenes/{examen_id}/questions-url")
async def get_course_examen_questions_url(
    course_id: uuid.UUID,
    examen_id: int,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    Genera una URL SAS temporal para el archivo JSON de preguntas de un examen oficial.
    El archivo se busca en documents.examenes[] usando el campo questions_file,
    y se sirve desde la carpeta Examenes/ de Azure Blob Storage.
    """
    # Verificar acceso del usuario al curso
    user_result = await db.execute(select(User).where(User.google_id == current_user.google_id))
    db_user = user_result.scalar_one_or_none()
    if not db_user or db_user.course_id != course_id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este curso")

    # Obtener el curso
    course_result = await db.execute(select(Course).where(Course.id == course_id))
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    documents = course.documents or {}
    examenes = documents.get("examenes", [])
    examen_info = next((e for e in examenes if e.get("id") == examen_id), None)
    if not examen_info:
        raise HTTPException(status_code=404, detail="Examen no encontrado en el curso")

    file_name = examen_info.get("questions_file")
    if not file_name:
        raise HTTPException(status_code=404, detail="El examen no tiene archivo de preguntas asociado")

    # Sanity check
    segments = file_name.replace("\\", "/").split("/")
    if any(s in ("", ".", "..") for s in segments):
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido")
    file_name = "/".join(segments)

    base_folder = course.folder_reference or str(course_id)
    # Los exámenes están bajo Examenes/ en Azure
    blob_path = f"{base_folder}/Examenes/{file_name}"
    url = generate_academy_read_sas(settings, blob_path=blob_path)
    return {"url": url, "expires_in_seconds": settings.academy_sas_expiry_minutes * 60}

