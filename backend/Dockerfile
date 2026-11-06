# Capa de lógica: Django + DRF servido por Gunicorn.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Primero las dependencias: si solo cambia el código, Docker reutiliza esta capa.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Usuario sin privilegios. staticfiles se crea acá para que el volumen herede
# el dueño correcto la primera vez que se monta.
RUN useradd --create-home --uid 1000 avigest \
    && mkdir -p /app/staticfiles \
    && chown -R avigest:avigest /app
USER avigest

EXPOSE 8000

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-"]
