FROM python:3.13-slim

WORKDIR /code

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
    "passlib[bcrypt]>=1.7.4"

# En desarrollo docker-compose monta ./app:/code/app (sobreescribe esto)
COPY app/ /code/app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
