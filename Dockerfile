FROM python:3.12-slim

ENV HOST=0.0.0.0 \
    PORT=8000 \
    RPG_MULTI_SESSION=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY . /app

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/saves \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/health', timeout=2)"

CMD ["python", "web_app.py"]
