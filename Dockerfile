FROM python:3.12-slim

WORKDIR /code

# WeasyPrint requiere librerías de sistema (Pango, Cairo, GDK-Pixbuf)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgobject-2.0-0 \
    libglib2.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    python-dotenv>=1.0.0 \
    pandas>=2.0.0 \
    pyarrow>=14.0.0 \
    minio>=7.2.0 \
    requests>=2.31.0 \
    httpx>=0.27.0 \
    fastapi>=0.111.0 \
    "uvicorn[standard]>=0.29.0" \
    jinja2>=3.1.0 \
    python-multipart>=0.0.9 \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    plotly>=5.18.0 \
    openpyxl>=3.1.0 \
    weasyprint>=62.0 \
    email-validator>=2.1.0 \
    croniter>=2.0.0 \
    scikit-learn>=1.4.0

# En desarrollo docker-compose monta ./app:/code/app (sobreescribe esto)
COPY app/ /code/app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]