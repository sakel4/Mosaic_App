FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app app

COPY --chown=app:app api/ /mosaic_app/backend/
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/entrypoint

WORKDIR /app/api
RUN mkdir -p /mosaic_app/backend/staticfiles \
    && chown app:app /app /mosaic_app/backend/staticfiles

USER app

EXPOSE 8000
ENTRYPOINT ["entrypoint"]
CMD ["gunicorn", "api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-", "--timeout", "60"]