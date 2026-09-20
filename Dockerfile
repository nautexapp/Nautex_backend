# Usa una imagen oficial y ligera de Python 3.12
FROM python:3.12-slim

# Evita que Python genere archivos .pyc y fuerza a que la salida se muestre en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependencias del sistema necesarias para compilar librerías (ej: asyncpg)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo
WORKDIR /app

# Copia solo los requirements primero (aprovecha la caché de capas de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copia el código fuente
COPY . .

# Expone el puerto 80 (típico en contenedores de Azure)
EXPOSE 80

# Comando para arrancar la aplicación en producción usando Gunicorn con Uvicorn workers
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:80"]
