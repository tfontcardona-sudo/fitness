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

# El entrypoint vive FUERA de /code, y no es un capricho.
#
# En desarrollo, docker-compose.dev.yml monta la carpeta del host encima de
# /code (hot-reload). Eso significa que el fichero de la IMAGEN queda tapado por
# el del PC: si ese viene con saltos de línea de Windows (CRLF), el shebang pasa
# a ser "#!/bin/sh\r", un intérprete que no existe, y Docker suelta un error que
# despista del todo:
#     exec /code/entrypoint.sh: no such file or directory
# (el fichero está; el que falta es el intérprete). Con el arranque copiado a
# /usr/local/bin, el montaje del host ya no puede taparlo: siempre se ejecuta la
# copia normalizada de la imagen. El sed limpia el CRLF por si la copia de
# origen venía de un clon hecho antes del .gitattributes o de un ZIP de Windows.
RUN sed -i 's/\r$//' /code/entrypoint.sh \
 && install -m 0755 /code/entrypoint.sh /usr/local/bin/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
