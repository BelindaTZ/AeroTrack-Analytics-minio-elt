FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# En desarrollo, docker-compose monta ./webapp:/app y sobreescribe esto.
# En producción (sin volumen), esta copia es la fuente de verdad.
COPY webapp/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
