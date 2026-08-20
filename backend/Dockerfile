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

# Cinturón y tirantes con los saltos de línea de Windows: aunque .gitattributes
# fuerza LF, una copia clonada ANTES de existir ese fichero (o un ZIP hecho en
# Windows) trae el entrypoint en CRLF y el contenedor falla con un error que no
# se entiende: "exec /code/entrypoint.sh: no such file or directory". Quitar el
# \r aquí hace que la imagen arranque venga como venga el archivo.
RUN sed -i 's/\r$//' /code/entrypoint.sh && chmod +x /code/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/code/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
