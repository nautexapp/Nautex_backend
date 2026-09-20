-- ==============================================================================
-- Datos Iniciales (Seeds) para Nautex: Escuela Mistral y Curso PNB
-- ==============================================================================

-- 1. Insertar Escuela Náutica Mistral
INSERT INTO schools (id, name, info, particularities) VALUES (
    'ce03b093-2513-428f-bd79-0bddc2e8d2e2',
    'Escuela Náutica Mistral',
    '{
        "email": "info@cfnmistral.com",
        "phone": "956765932",
        "address": "Av. de la Banqueta, 49, La Línea de la Concepción",
        "website": "cfnmistral.com",
        "logo_url": "https://nautexdev.blob.core.windows.net/public/school_logos/mistral.avif"
    }'::jsonb,
    '{}'::jsonb
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    info = EXCLUDED.info;

-- 2. Insertar Curso PNB (Patrón para Navegación Básica) con temario completo
INSERT INTO courses (id, name, folder_reference, documents) VALUES (
    'b2c3d4e5-f6a7-8901-bcde-f12345678901',
    'Patrón para Navegación Básica (PNB)',
    'pnb',
    '{
        "tests": [
            {
                "id": 1,
                "file": "1. Nomenclatura nautica.json",
                "name": "Nomenclatura Náutica",
                "questions": 183
            },
            {
                "id": 2,
                "file": "2. Elementos de amarre y fondeo.json",
                "name": "Elementos de amarre y fondeo",
                "questions": 76
            },
            {
                "id": 3,
                "file": "3. Seguridad en la mar.json",
                "name": "Seguridad en la mar",
                "questions": 287
            },
            {
                "id": 4,
                "file": "4. Legislacion.json",
                "name": "Legislación",
                "questions": 135
            },
            {
                "id": 5,
                "file": "5. Balizamiento.json",
                "name": "Balizamiento",
                "questions": 106
            },
            {
                "id": 6,
                "file": "6. RIPA.json",
                "name": "Reglamento internacional para prevenir abordajes (RIPA)",
                "questions": 321
            }
        ],
        "apuntes": [
            {
                "id": 1,
                "file": "Balizamiento.pdf",
                "name": "Apuntes de Balizamiento",
                "pages": 1
            },
            {
                "id": 2,
                "file": "RIPA.pdf",
                "name": "Apuntes del RIPA",
                "pages": 6
            }
        ],
        "examenes": [
            {
                "id": 1,
                "file": "Andalucia/2023_Marzo.pdf",
                "solutions_file": "Andalucia/2023_Marzo_sol.pdf",
                "questions_file": "Andalucia/2023_Marzo.json",
                "name": "2023 - Marzo",
                "questions": 27
            },
            {
                "id": 2,
                "file": "Andalucia/2023_Junio.pdf",
                "solutions_file": "Andalucia/2023_Junio_sol.pdf",
                "questions_file": "Andalucia/2023_Junio.json",
                "name": "2023 - Junio",
                "questions": 27
            },
            {
                "id": 3,
                "file": "Andalucia/2023_Octubre.pdf",
                "solutions_file": "Andalucia/2023_Octubre_sol.pdf",
                "questions_file": "Andalucia/2023_Octubre.json",
                "name": "2023 - Octubre",
                "questions": 27
            },
            {
                "id": 4,
                "file": "Andalucia/2024_Abril.pdf",
                "solutions_file": "Andalucia/2024_Abril_sol.pdf",
                "questions_file": "Andalucia/2024_Abril.json",
                "name": "2024 - Abril",
                "questions": 27
            },
            {
                "id": 5,
                "file": "Andalucia/2024_Julio.pdf",
                "solutions_file": "Andalucia/2024_Julio_sol.pdf",
                "questions_file": "Andalucia/2024_Julio.json",
                "name": "2024 - Julio",
                "questions": 27
            },
            {
                "id": 6,
                "file": "Andalucia/2024_Noviembre.pdf",
                "solutions_file": "Andalucia/2024_Noviembre_sol.pdf",
                "questions_file": "Andalucia/2024_Noviembre.json",
                "name": "2024 - Noviembre",
                "questions": 27
            },
            {
                "id": 7,
                "file": "Andalucia/2025_Marzo.pdf",
                "solutions_file": "Andalucia/2025_Marzo_sol.pdf",
                "questions_file": "Andalucia/2025_Marzo.json",
                "name": "2025 - Marzo",
                "questions": 27
            },
            {
                "id": 8,
                "file": "Andalucia/2025_Julio.pdf",
                "solutions_file": "Andalucia/2025_Julio_sol.pdf",
                "questions_file": "Andalucia/2025_Julio.json",
                "name": "2025 - Julio",
                "questions": 27
            },
            {
                "id": 9,
                "file": "Andalucia/2025_Noviembre.pdf",
                "solutions_file": "Andalucia/2025_Noviembre_sol.pdf",
                "questions_file": "Andalucia/2025_Noviembre.json",
                "name": "2025 - Noviembre",
                "questions": 27
            },
            {
                "id": 10,
                "file": "Andalucia/2026_Marzo.pdf",
                "solutions_file": "Andalucia/2026_Marzo_sol.pdf",
                "questions_file": "Andalucia/2026_Marzo.json",
                "name": "2026 - Marzo",
                "questions": 27
            },
            {
                "id": 11,
                "file": "Andalucia/2026_Junio.pdf",
                "solutions_file": "Andalucia/2026_Junio_sol.pdf",
                "questions_file": "Andalucia/2026_Junio.json",
                "name": "2026 - Junio",
                "questions": 27
            },
            {
                "id": 12,
                "file": "Cataluña/2024-Junio.pdf",
                "name": "2024 - Junio",
                "questions": 27
            },
            {
                "id": 13,
                "file": "Cataluña/2024-Diciembre.pdf",
                "name": "2024 - Diciembre",
                "questions": 27
            },
            {
                "id": 14,
                "file": "Cataluña/2025-Junio.pdf",
                "name": "2025 - Junio",
                "questions": 27
            },
            {
                "id": 15,
                "file": "Cataluña/2025-Julio.pdf",
                "name": "2025 - Julio",
                "questions": 27
            },
            {
                "id": 16,
                "file": "Madrid/junio_2023.pdf",
                "name": "2023 - Junio",
                "questions": 27
            },
            {
                "id": 17,
                "file": "Madrid/noviembre_2023.pdf",
                "name": "2023 - Noviembre",
                "questions": 27
            },
            {
                "id": 18,
                "file": "Madrid/junio_2024.pdf",
                "name": "2024 - Junio",
                "questions": 27
            },
            {
                "id": 19,
                "file": "Madrid/noviembre_2024.pdf",
                "name": "2024 - Noviembre",
                "questions": 27
            },
            {
                "id": 20,
                "file": "Madrid/junio_2025.pdf",
                "name": "2025 - Junio",
                "questions": 27
            }
        ],
        "documentos": [
            {
                "id": 1,
                "file": "01. NOMENCLATURA NÁUTICA.pdf",
                "name": "Nomenclatura Náutica",
                "pages": 11
            },
            {
                "id": 2,
                "file": "02. ELEMENTOS DE AMARRE Y FONDE--O.pdf",
                "name": "Elementos de amarre y fondeo",
                "pages": 7
            },
            {
                "id": 3,
                "file": "03. SEGURIDAD EN LA MAR.pdf",
                "name": "Seguridad en la mar",
                "pages": 22
            },
            {
                "id": 4,
                "file": "04. LEGISLACIÓN.pdf",
                "name": "Legislación",
                "pages": 11
            },
            {
                "id": 5,
                "file": "05. BALIZAMIENTO.pdf",
                "name": "Balizamiento",
                "pages": 8
            },
            {
                "id": 6,
                "file": "06. RIPA.pdf",
                "name": "Reglamento internacional para prevenir abordajes (RIPA)",
                "pages": 28
            }
        ]
    }'::jsonb
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    folder_reference = EXCLUDED.folder_reference,
    documents = EXCLUDED.documents;

-- 3. Códigos de registro para que los alumnos puedan darse de alta
INSERT INTO registration_codes (code, school_id, course_id) VALUES
    ('TEST', 'ce03b093-2513-428f-bd79-0bddc2e8d2e2', 'b2c3d4e5-f6a7-8901-bcde-f12345678901'),
    ('PNB-MISTRAL', 'ce03b093-2513-428f-bd79-0bddc2e8d2e2', 'b2c3d4e5-f6a7-8901-bcde-f12345678901')
ON CONFLICT (code) DO NOTHING;
