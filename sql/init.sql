-- Inicialización de la base de datos para Nautex

-- Tabla schools: Identifica a cada escuela cliente y centraliza sus particularidades
CREATE TABLE IF NOT EXISTS schools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    particularities JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabla courses: Índice de cada curso y sus documentos en Azure Blob Storage
-- El campo 'documents' contiene: { tests: [], apuntes: [], examenes: [], documentos: [] }
-- donde cada ítem tiene: { id, name, file, questions? | pages? | type? }
CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    folder_reference VARCHAR(512),
    documents JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabla registration_codes: Códigos que entrega la escuela a cada alumno
-- Cada código está asociado a una escuela y a un curso concreto
CREATE TABLE IF NOT EXISTS registration_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) UNIQUE NOT NULL,
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE SET NULL,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabla users: Centraliza el acceso y el historial del alumno
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entra_id VARCHAR(128) UNIQUE NOT NULL,
    email VARCHAR(320) UNIQUE NOT NULL,
    progress JSONB DEFAULT '{}'::jsonb NOT NULL,
    school_id UUID REFERENCES schools(id) ON DELETE SET NULL,
    course_id UUID REFERENCES courses(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
