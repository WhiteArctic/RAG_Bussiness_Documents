# Dockerfile de producción para Cloud Run.
#
# Decisiones de diseño (defendibles en entrevista):

# 1) Imagen base 'slim': Python oficial pero ligera. Menos peso = arranque más
#    rápido (importa en Cloud Run por los cold starts) y menor superficie de
#    ataque. No usamos 'alpine' porque suele dar problemas al compilar wheels
#    (p. ej. numpy) por usar musl en vez de glibc.
FROM python:3.11-slim

# 2) Variables de entorno de Python para contenedores:
#    - PYTHONDONTWRITEBYTECODE: no generar .pyc (no sirven en un contenedor efímero).
#    - PYTHONUNBUFFERED: logs salen en tiempo real a stdout -> Cloud Logging.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 3) Copiamos SOLO requirements primero e instalamos. Aprovecha la caché de capas
#    de Docker: si el código cambia pero las deps no, no reinstala todo. Build
#    más rápido en cada despliegue.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4) Ahora sí, el resto del código y los documentos.
COPY app/ ./app/
COPY data/ ./data/

# 5) Usuario no-root: si alguien compromete el contenedor, no tiene privilegios
#    de root. Buena práctica de seguridad exigida en producción.
RUN useradd --create-home appuser
USER appuser

# 6) Cloud Run inyecta el puerto en la variable $PORT (por defecto 8080).
#    Debemos escuchar ahí, no en un puerto fijo hardcodeado.
ENV PORT=8080
EXPOSE 8080

# 7) Arranque. Usamos la forma shell para que $PORT se expanda. En producción
#    uvicorn con --workers se ajustaría según CPU; Cloud Run suele preferir
#    1 worker por instancia y dejar que la plataforma escale horizontalmente.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
