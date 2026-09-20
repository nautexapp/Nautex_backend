"""
Script para actualizar los ficheros de examenes en la base de datos.

Annade los campos "solutions_file" y "questions_file" a cada item de examen
en el campo JSONB "documents" del curso.

Uso:
  1. Edita el dict EXAM_FILES con los nombres reales de los ficheros en Azure.
  2. Edita COURSE_ID con el UUID del curso que quieres actualizar.
  3. Ejecuta desde la raiz del proyecto Backend:
       python scripts/update_examenes_files.py

Estructura esperada en Azure (dentro de la carpeta del curso/Examenes/):
  andalucia-2023-marzo.pdf
  andalucia-2023-marzo-soluciones.pdf
  andalucia-2023-marzo-preguntas.json
"""

import asyncio
import os
import sys
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal, init_db
from app.db.models import Course

# --- CONFIGURA AQUI --------------------------------------------------------
# UUID del curso a actualizar
COURSE_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

# Dict de ficheros por id de examen.
# Clave: id del examen (int, igual que en documents.examenes[].id)
# Valor: dict con los campos opcionales a annadir/actualizar
# Deja como None o quita la clave si el fichero no existe todavia.
EXAM_FILES = {
    1: {
        "file":            "andalucia-2023-marzo.pdf",
        "solutions_file":  "andalucia-2023-marzo-soluciones.pdf",
        "questions_file":  "andalucia-2023-marzo-preguntas.json",
    },
    # Ejemplo de examen con solo PDF (sin soluciones ni test todavia):
    # 2: {
    #     "file":           "andalucia-2024-junio.pdf",
    #     "solutions_file": None,
    #     "questions_file": None,
    # },
}
# ---------------------------------------------------------------------------


async def main():
    init_db()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Course).where(Course.id == uuid.UUID(COURSE_ID))
        )
        course = result.scalar_one_or_none()

        if not course:
            print(f"Curso con id '{COURSE_ID}' no encontrado.")
            return

        documents = dict(course.documents or {})
        examenes  = list(documents.get("examenes", []))

        updated = 0
        for exam in examenes:
            exam_id = exam.get("id")
            if exam_id in EXAM_FILES:
                patches = EXAM_FILES[exam_id]
                for field, value in patches.items():
                    if value is not None:
                        exam[field] = value
                    elif field in exam:
                        del exam[field]
                updated += 1
                print(f"  Examen id={exam_id} ('{exam.get('name')}') actualizado.")
            else:
                print(f"  Examen id={exam_id} ('{exam.get('name')}') sin cambios.")

        documents["examenes"] = examenes
        course.documents = documents
        await db.commit()

        print(f"\nTotal: {updated} examen(es) actualizados en el curso '{course.name}'.")


if __name__ == "__main__":
    asyncio.run(main())
