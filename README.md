# Nautex - Backend API

API asíncrona de **Nautex · Escuela Náutica Digital**, construida con **FastAPI** y **Python 3.12**. Proporciona servicios de gestión de usuarios, escuelas náuticas asociadas, sincronización de contenidos náuticos desde Azure Blob Storage, simulación de exámenes oficiales, generación inteligente de preguntas y temarios mediante IA (DeepSeek), y procesamiento de pagos con MONEI.

---

## 🚀 Tecnologías

* **Framework**: FastAPI (con ASGI Uvicorn / Gunicorn)
* **Lenguaje**: Python 3.12
* **ORM & Base de Datos**: SQLAlchemy 2.0 (modo asíncrono con `asyncpg`) sobre PostgreSQL
* **Autenticación**: Microsoft Entra ID / Azure CIAM (validación de tokens JWT mediante firmas criptográficas JWKS)
* **Almacenamiento Cloud**: Azure Blob Storage (documentos PDF, exámenes oficiales, apuntes y generación de SAS tokens temporales)
* **Gestión de Secretos**: Azure Key Vault
* **Inteligencia Artificial**: DeepSeek API (`deepseek-v4-flash`) para extracción de contenido (PyMuPDF) y generación de tests
* **Pasarela de Pagos**: MONEI API

---

## 📋 Requisitos Previos

* **Python**: 3.12 o superior
* **Docker & Docker Compose**: Para levantar la base de datos PostgreSQL local
* Acceso a los servicios en la nube correspondientes (Azure Blob Storage, Entra ID / CIAM, DeepSeek) si se prueban integraciones completas

---

## ⚙️ Configuración del Entorno

1. Copia el archivo de variables de entorno de ejemplo:
   ```bash
   cp .env.example .env
   ```
2. Modifica `.env` con tus credenciales y configuración local. Para desarrollo local sin Azure Key Vault, puedes especificar directamente `STORAGE_CONNECTION_STRING`, `DATABASE_URL` y `AI_API_KEY`.

---

## 🗄️ Base de Datos Local

Levanta una instancia de PostgreSQL en Docker preconfigurada con el esquema inicial (`sql/init.sql`) y datos de prueba (`sql/seed.sql`):

```bash
docker compose up -d
```

Para detener el contenedor:
```bash
docker compose down
```

---

## 💻 Instalación y Ejecución Local

1. **Crear y activar entorno virtual**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Iniciar el servidor de desarrollo**:
   ```bash
   python run.py
   ```
   O alternativamente:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

4. **Documentación interactiva**:
   * Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   * ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
   * Endpoint de salud: [http://localhost:8000/health](http://localhost:8000/health)

---

## 📂 Estructura del Proyecto

```
app/
├── core/            # Utilidades de identidad y resolución de tenant
├── db/              # Modelos SQLAlchemy, motor y gestión de sesiones
├── dependencies/    # Inyección de dependencias (autenticación JWT, sesion DB)
├── routers/         # Endpoints de la API (users, courses, registration, ai)
├── schemas/         # Esquemas de validación Pydantic
├── services/        # Lógica de negocio (Azure Storage, IA, Key Vault, Pagos)
├── config.py        # Configuración centralizada vía Pydantic Settings
└── main.py          # Definición de la aplicación FastAPI, middlewares y CORS

scripts/             # Scripts administrativos (seed de academias, exámenes, etc.)
sql/                 # Scripts DDL de inicialización (init.sql, seed.sql)
Dockerfile           # Contenedor de producción con Gunicorn + UvicornWorker
docker-compose.yml   # Entorno de PostgreSQL local
```

---

## 🐳 Contenedor y Despliegue en Producción

El backend incluye un `Dockerfile` optimizado multicapa para producción:
* Expone el puerto `80`.
* Ejecuta `gunicorn` con 4 workers `uvicorn.workers.UvicornWorker`.
* El workflow `.github/workflows/docker-build.yml` compila y publica automáticamente la imagen en **GitHub Container Registry (`ghcr.io`)** al hacer push a `main`.
