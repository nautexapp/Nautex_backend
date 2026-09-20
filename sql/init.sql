-- ==============================================================================
-- Esquema Inicial de Base de Datos - Nautex API (PostgreSQL)
-- ==============================================================================

-- 1. Tabla schools: Escuelas náuticas asociadas y datos de contacto/branding
CREATE TABLE IF NOT EXISTS schools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    particularities JSONB,
    info JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Tabla courses: Cursos náuticos (PNB, PER, etc.) con índice de documentos y tests
-- El campo 'documents' contiene: { tests: [], apuntes: [], examenes: [], documentos: [] }
CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    folder_reference VARCHAR(512),
    documents JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Tabla registration_codes: Códigos de activación de escuela
CREATE TABLE IF NOT EXISTS registration_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) UNIQUE NOT NULL,
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE SET NULL,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_registration_codes_code ON registration_codes(code);

-- 4. Tabla users: Alumnos de la plataforma
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    google_id VARCHAR(128) UNIQUE NOT NULL,
    email VARCHAR(320) UNIQUE NOT NULL,
    progress JSONB DEFAULT '{}'::jsonb NOT NULL,
    school_id UUID REFERENCES schools(id) ON DELETE SET NULL,
    course_id UUID REFERENCES courses(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
