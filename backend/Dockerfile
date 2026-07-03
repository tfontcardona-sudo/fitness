FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Madrid

WORKDIR /code

# Dependencias del sistema para matplotlib/pillow/psycopg + LibreOffice headless
# (conversión determinista de los planes .docx → PDF, idéntica a la del QA) y fuentes.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libfreetype6 libjpeg62-turbo zlib1g curl \
    libreoffice-writer libreoffice-core fonts-liberation fonts-dejavu-core \
    fonts-crosextra-carlito \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /code/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/code/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
