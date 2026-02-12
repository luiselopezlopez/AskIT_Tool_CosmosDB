# Multi-stage Dockerfile optimizado para Python 3.12 + Flask + Gunicorn
# Etapa 1: Builder - Instalar dependencias
FROM python:3.12-slim AS builder

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar paquetes Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Copiar solo requirements.txt primero para aprovechar caché de Docker
COPY requirements.txt .

# Instalar dependencias en un directorio específico
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# Etapa 2: Runtime - Imagen de producción mínima
FROM python:3.12-slim

# Establecer variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/usr/local/bin:$PATH \
    GUNICORN_WORKERS=4 \
    GUNICORN_THREADS=2 \
    PORT=8000

# Crear usuario no privilegiado para ejecutar la aplicación
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Establecer directorio de trabajo
WORKDIR /app

# Copiar dependencias instaladas desde la etapa builder
COPY --from=builder /install /usr/local

# Copiar código de la aplicación
COPY --chown=appuser:appuser app.py .

# Cambiar al usuario no privilegiado
USER appuser

# Exponer puerto 8000 (configurable via variable PORT)
EXPOSE 8000

# Healthcheck para verificar que la aplicación esté respondiendo
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health')" || exit 1

# Comando de arranque con Gunicorn para entorno productivo
# - bind: Escuchar en todas las interfaces en el puerto especificado (default: 8000)
# - workers: Número de procesos workers (configurable via GUNICORN_WORKERS, default: 4)
# - threads: Hilos por worker para manejar múltiples requests (configurable via GUNICORN_THREADS, default: 2)
# - worker-class: gthread para soporte de threading
# - worker-tmp-dir: Usar /dev/shm para evitar problemas de I/O
# - timeout: Timeout de 120 segundos para requests largos
# - access-logfile: Logs de acceso a stdout
# - error-logfile: Logs de errores a stderr
CMD gunicorn \
     --bind "0.0.0.0:${PORT:-8000}" \
     --workers "${GUNICORN_WORKERS:-4}" \
     --threads "${GUNICORN_THREADS:-2}" \
     --worker-class gthread \
     --worker-tmp-dir /dev/shm \
     --timeout 120 \
     --access-logfile - \
     --error-logfile - \
     --log-level info \
     app:app
