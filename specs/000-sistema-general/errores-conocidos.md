# Errores Conocidos y Soluciones

Troubleshooting para desarrolladores que working on AeroTrack Analytics.

---

## 1. SECRET_KEY no definida

**Síntoma:** App crashea al arrancar en Docker con `RuntimeError: SECRET_KEY obligatoria`.

**Causa:** No hay `SECRET_KEY` en `.env` o usa el valor por defecto `"changeme"`.

**Solución:**
```bash
# Generar clave segura
python -c "import secrets; print(secrets.token_hex(32))"

# Agregar a .env
SECRET_KEY=<valor generado>
```

**Nota:** En local (sin Docker) solo muestra warning pero permite arrancar.

---

## 2. PocketBase no responde

**Síntoma:** FastAPI muestra error 500 o timeout al hacer login.

**Causa:** PocketBase no está corriendo o no pasó health check.

**Solución:**
```bash
# Verificar estado
docker compose ps pocketbase

# Reiniciar
docker compose restart pocketbase

# Ver logs
docker compose logs pocketbase --tail=50
```

---

## 3. MinIO no encontrado

**Síntoma:** `Minio error: Connection refused` o `S3Error`.

**Causa:** MinIO no está corriendo o los buckets no existen.

**Solución:**
```bash
# Verificar MinIO
docker compose ps minio

# Recrear buckets
docker compose run --rm minio-init

# Verificar buckets
mc alias set local http://localhost:9000 admin admin1234
mc ls local/
```

---

## 4. Pipeline ELT falla en extract

**Síntoma:** Tarea `extract` en Airflow falla con timeout o error de conexión.

**Causas posibles:**
- PocketBase no tiene datos en `vuelos_raw`
- Configuración incorrecta de `PB_EMAIL`/`PB_PASSWORD`
- Timeout insuficiente (default 2h)

**Solución:**
```bash
# Verificar datos en PocketBase
# Abrir http://localhost:8090/_/ → colección vuelos_raw

# Verificar variables de entorno
docker compose exec airflow-scheduler env | grep PB_

# Ver logs del task
docker compose logs airflow-scheduler --tail=100
```

---

## 5. Transform falla con columnas faltantes

**Síntoma:** `KeyError: 'SomeColumn'` durante transform.

**Causa:** El CSV fuente no tiene la columna esperada o el nombre cambió.

**Solución:** Verificar que `data/airline_2m.csv` tenga todas las columnas del manifiesto en `aerotrack_tasks.py` (líneas 291-318).

---

## 6. FastAPI no importa módulos

**Síntoma:** `ModuleNotFoundError: No module named 'app.xxx'`.

**Causa:** Falta instalar dependencias o el Dockerfile no las incluye.

**Solución:**
```bash
# Verificar dependencias en Dockerfile
grep "pip install" Dockerfile

# Rebuild si es necesario
docker compose build --no-cache fastapi
docker compose up -d
```

---

## 7. WeasyPrint no disponible

**Síntoma:** Endpoint PDF devuelve HTTP 501.

**Causa:** WeasyPrint no está instalado (es opcional).

**Solución:** Esto es comportamiento esperado. El resto del sistema funciona normalmente. Para activar PDF, ver README.md sección "WeasyPrint".

---

## 8. RAG responde "No hay datos disponibles"

**Síntoma:** El asistente IA dice que no hay datos aunque el pipeline corrió.

**Causas posibles:**
1. El pipeline no ha corrido transform (no hay tablas en `aerotrack-dims`)
2. Todas las fuentes están desactivadas en `asistente_fuentes`
3. Los filtros no coinciden con datos existentes

**Solución:**
```bash
# 1. Verificar que existan archivos en MinIO
# http://localhost:9001 → bucket aerotrack-dims

# 2. Verificar fuentes activas
# http://localhost:8090/_/ → colección asistente_fuentes

# 3. Probar sin filtros
# Preguntar: "¿Cuál es el OTP global?"
```

---

## 9. JWT expira constantemente

**Síntoma:** Usuarios son deslogueados frecuentemente.

**Causa:** `TOKEN_EXPIRE_MINUTES` es muy bajo o la timezone está mal configurada.

**Solución:** Verificar en `.env`:
```
TOKEN_EXPIRE_MINUTES=60  # Default 60 minutos
```

---

## 10. Airflow no muestra DAGs

**Síntoma:** La UI de Airflow no muestra `aerotrack_elt_pipeline`.

**Causa:** Los archivos DAG no están montados correctamente en el contenedor.

**Solución:**
```bash
# Verificar que dags/ esté montado
docker compose exec airflow-webserver ls /opt/airflow/dags/

# Verificar sintaxis del DAG
docker compose exec airflow-webserver python /opt/airflow/dags/aerotrack_elt_dag.py

# Reiniciar scheduler
docker compose restart airflow-scheduler
```

---

## 11. Ruff marca errores de estilo

**Síntoma:** `ruff check` muestra errores N806, E701, etc.

**Causa:** Son convenciones del proyecto, no errores reales.

**Solución:** Están configurados en `pyproject.toml` para ser ignorados:
```toml
[tool.ruff.lint]
ignore = ["N806", "E701", "E702", "E402", ...]
```

Para ejecutar linting limpio:
```bash
ruff check app/ dags/
ruff format app/ dags/
```

---

## 12. Tests fallan por imports

**Síntoma:** `ModuleNotFoundError` al ejecutar `pytest`.

**Causa:** Falta instalar dependencias de desarrollo.

**Solución:**
```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

---

## 13. Puerto 8000 ya en uso

**Síntoma:** `Error: [Errno 10048] Address already in use`.

**Causa:** Otro proceso usa el puerto 8000.

**Solución:**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# O cambiar puerto en docker-compose.yml
ports:
  - "8001:8000"
```

---

## 14. Variables de entorno no se cargan

**Síntoma:** Las variables de `.env` no están disponibles en el código.

**Causa:** `load_dotenv()` no se ejecutó o el path es incorrecto.

**Solución:** Verificar que cada `config.py` tenga:
```python
from dotenv import load_dotenv
load_dotenv()  # O con path explícito
```

---

## 15. Presigned URLs no funcionan

**Síntoma:** URLs de descarga de reportes devuelven 403.

**Causa:** `MINIO_PUBLIC_URL` no coincide con la URL real de MinIO.

**Solución:** Verificar en `.env`:
```
MINIO_PUBLIC_URL=localhost:9000  # Sin http://
```
