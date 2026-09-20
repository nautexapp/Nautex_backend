import asyncio
import json
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal
from app.db.models import AcademyPackage
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Datos de prueba para insertar en la BD
MOCK_PACKAGES = [
    {
        "id": "per",
        "category": "nautica",
        "title": "Patrón de Embarcación de Recreo (PER)",
        "description": "Tests completos sobre navegación, seguridad, reglamento de abordajes y meteorología para el examen oficial del PER.",
        "price_cents": 1499,
        "is_active": True,
        "folder_reference": "per",
        "content_manifest": {
            "tests": [
                {"id": 1, "name": "Reglamento de abordajes (RIPA)", "questions": 25},
                {"id": 2, "name": "Navegación — Cartas y compás", "questions": 30},
                {"id": 3, "name": "Meteorología básica", "questions": 20},
                {"id": 4, "name": "Seguridad y equipos de salvamento", "questions": 22},
                {"id": 5, "name": "Motor y propulsión", "questions": 18}
            ],
            "apuntes": [
                {"id": 1, "name": "Guía completa del RIPA", "pages": 45},
                {"id": 2, "name": "Interpretación de cartas náuticas", "pages": 32},
                {"id": 3, "name": "Meteorología para navegantes", "pages": 28}
            ],
            "documentos": [
                {"id": 1, "name": "Temario oficial BOE", "type": "pdf"},
                {"id": 2, "name": "Tabla de mareas 2024", "type": "pdf"}
            ],
            "examenes": [
                {"id": 1, "name": "Examen oficial convocatoria 2022", "questions": 50},
                {"id": 2, "name": "Examen oficial convocatoria 2023", "questions": 50},
                {"id": 3, "name": "Examen oficial convocatoria 2024", "questions": 50}
            ]
        }
    },
    {
        "id": "patron-yate",
        "category": "nautica",
        "title": "Patrón de Yate (PY)",
        "description": "Temario completo para el PY: navegación astronómica, meteorología avanzada, maniobras y seguridad en alta mar.",
        "price_cents": 1999,
        "is_active": True,
        "folder_reference": "patron-yate",
        "content_manifest": {
            "tests": [
                {"id": 1, "name": "Navegación astronómica", "questions": 35},
                {"id": 2, "name": "Meteorología avanzada", "questions": 28},
                {"id": 3, "name": "Maniobra en alta mar", "questions": 30},
                {"id": 4, "name": "Reglamentación internacional", "questions": 25}
            ],
            "apuntes": [
                {"id": 1, "name": "Navegación por estrellas", "pages": 60},
                {"id": 2, "name": "Manual de maniobras en alta mar", "pages": 55}
            ],
            "documentos": [
                {"id": 1, "name": "Temario oficial PY", "type": "pdf"}
            ],
            "examenes": [
                {"id": 1, "name": "Examen oficial convocatoria 2022", "questions": 60},
                {"id": 2, "name": "Examen oficial convocatoria 2023", "questions": 60}
            ]
        }
    },
    {
        "id": "patron-costa",
        "category": "nautica",
        "title": "Patrón de Costa (PC)",
        "description": "Tests y apuntes para la titulación de Patrón de Costa: carta náutica, maniobra, propulsión y legislación marítima.",
        "price_cents": 1299,
        "is_active": True,
        "folder_reference": "patron-costa",
        "content_manifest": {
            "tests": [
                {"id": 1, "name": "Carta náutica y navegación", "questions": 30},
                {"id": 2, "name": "Legislación marítima", "questions": 15}
            ],
            "apuntes": [
                {"id": 1, "name": "Manual de carta náutica", "pages": 40}
            ],
            "documentos": [],
            "examenes": [
                {"id": 1, "name": "Examen oficial convocatoria 2023", "questions": 45}
            ]
        }
    },
    {
        "id": "opo-aux-admin",
        "category": "oposiciones",
        "title": "Auxiliar Administrativo del Estado",
        "description": "Tests completos sobre los temas del programa oficial: Constitución, Ley 39/2015, ofimática y más.",
        "price_cents": 1999,
        "is_active": True,
        "folder_reference": "opo-aux-admin",
        "content_manifest": {
            "tests": [
                {"id": 1, "name": "Constitución Española de 1978", "questions": 40},
                {"id": 2, "name": "Ley 39/2015", "questions": 35},
                {"id": 3, "name": "Ofimática básica", "questions": 25}
            ],
            "apuntes": [
                {"id": 1, "name": "Resumen Ley 39/2015", "pages": 20},
                {"id": 2, "name": "Esquemas de la Constitución", "pages": 15}
            ],
            "documentos": [
                {"id": 1, "name": "BOE convocatoria oficial", "type": "pdf"}
            ],
            "examenes": [
                {"id": 1, "name": "Examen Turno Libre 2022", "questions": 90},
                {"id": 2, "name": "Examen Turno Libre 2023", "questions": 90}
            ]
        }
    },
    {
        "id": "opo-guardia-civil",
        "category": "oposiciones",
        "title": "Guardia Civil — Escala Cabos y Guardias",
        "description": "Más de 60 tests que cubren todo el temario: ciencias jurídicas, materias socioculturales y técnico-científicas.",
        "price_cents": 2499,
        "is_active": True,
        "folder_reference": "opo-guardia-civil",
        "content_manifest": {
            "tests": [
                {"id": 1, "name": "Derecho Penal", "questions": 50},
                {"id": 2, "name": "Derecho Constitucional", "questions": 45},
                {"id": 3, "name": "Fuerzas y Cuerpos de Seguridad", "questions": 30}
            ],
            "apuntes": [
                {"id": 1, "name": "Código Penal Básico", "pages": 80}
            ],
            "documentos": [
                {"id": 1, "name": "BOE convocatoria Guardia Civil 2023", "type": "pdf"}
            ],
            "examenes": [
                {"id": 1, "name": "Simulacro oficial 2023", "questions": 100}
            ]
        }
    },
    {
        "id": "opo-correos",
        "category": "oposiciones",
        "title": "Personal Laboral de Correos",
        "description": "Prepárate para el proceso selectivo con tests del temario oficial de Correos actualizado.",
        "price_cents": 1499,
        "is_active": True,
        "folder_reference": "opo-correos",
        "content_manifest": {
            "tests": [
                {"id": 1, "name": "Productos y servicios postales", "questions": 40},
                {"id": 2, "name": "Procesos de admisión", "questions": 30}
            ],
            "apuntes": [
                {"id": 1, "name": "Temario Resumido Vol 1", "pages": 50}
            ],
            "documentos": [],
            "examenes": [
                {"id": 1, "name": "Examen Consolidación 2022", "questions": 100}
            ]
        }
    }
]

async def seed():
    logger.info("Conectando a la base de datos...")
    
    from app.db.session import init_db, AsyncSessionLocal
    init_db()
    
    async with AsyncSessionLocal() as db:
        for pkg_data in MOCK_PACKAGES:
            result = await db.execute(select(AcademyPackage).where(AcademyPackage.id == pkg_data["id"]))
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info(f"El paquete {pkg_data['id']} ya existe. Actualizando...")
                for key, value in pkg_data.items():
                    setattr(existing, key, value)
            else:
                logger.info(f"Creando paquete {pkg_data['id']}...")
                new_pkg = AcademyPackage(**pkg_data)
                db.add(new_pkg)
        
        await db.commit()
        logger.info("✅ Todos los paquetes han sido insertados o actualizados correctamente.")

if __name__ == "__main__":
    asyncio.run(seed())
