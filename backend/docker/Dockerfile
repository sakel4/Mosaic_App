FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app app

# Build context is backend/ (see docker-compose.prod.yml), so "." is the Django project root.
COPY --chown=app:app . /app/
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/entrypoint

RUN mkdir -p /app/staticfiles \
    && chown app:app /app /app/staticfiles

USER app

EXPOSE 8000
ENTRYPOINT ["entrypoint"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-", "--timeout", "60"]