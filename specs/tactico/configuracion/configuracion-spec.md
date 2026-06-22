# Especificación Táctica — Configuración

**Módulo:** Configuración
**Prefijo:** CFG
**Código fuente:** `app/configuracion/`
**Casos de uso cubiertos:** CU-T03 (Configurar parámetros del sistema por grupo), CU-T04 (Configurar parámetros de correo electrónico SMTP), CU-T05 (Configurar parámetros de inteligencia artificial), CU-T07 (Configurar umbrales de alertas del dashboard), CU-T08 (Configurar parámetros del pipeline ELT)
**Actor:** Administrador

---

## Funcionalidad 1: Panel de configuración por grupos (CU-T03)

Panel unificado con navegación lateral por 5 grupos. Cada grupo se guarda de forma independiente vía `POST /configuracion/{grupo}`. Los datos se persisten en PocketBase colección `configuracion_sistema`. Implementado en `app/configuracion/panel.py`.

### RF-CFG-001 — Navegación por 5 grupos
El panel muestra 5 grupos en la navegación lateral: Email / SMTP, Alertas y Umbrales, Pipeline ELT, Inteligencia Artificial, Sistema General. Cada grupo tiene icono y color distintivo.

### RF-CFG-002 — Guardado independiente por grupo
`POST /configuracion/{grupo}` actualiza solo los registros de `configuracion_sistema` cuyo campo `modulo` coincide con el grupo solicitado. Los demás grupos no se ven afectados.

### RF-CFG-003 — Tipos de campo según configuración
Cada parámetro se renderiza según su tipo: `string` → input text, `int`/`float` → input number con step, `bool` → select Sí/No, `password` → input password, `email` → input email. Los campos no editables se muestran deshabilitados.

### RF-CFG-004 — Campos sensibles enmascarados
Los registros con `sensible=True` se muestran como "••••••••" en la UI y tienen un badge rojo "Sensible". Al guardar, el valor "••••••••" se ignora (no se sobrescribe), preservando el valor existente.

### RF-CFG-005 — Auditoría de cambios
Cada guardado exitoso registra en auditoría con acción `editar`, módulo `configuracion`, recurso_tipo=`grupo` y recurso_id=`{nombre_grupo}`.

---

## Funcionalidad 2: Configuración SMTP (CU-T04)

Grupo `email` con 7 parámetros para el servidor de correo. Incluye prueba de conexión desde la UI con envío de email real. Implementado en `app/configuracion/panel.py`.

### RF-CFG-006 — Parámetros SMTP configurables
Siete parámetros: `email_smtp_host` (servidor), `email_smtp_port` (puerto, default 587), `email_remitente` (dirección from), `email_password` (contraseña SMTP, sensible), `email_usar_tls` (bool, default true), `email_alertas_activas` (bool), `email_destinatario` (dirección para alertas).

### RF-CFG-007 — Prueba de conexión SMTP desde UI
`POST /configuracion/email/test` lee la configuración actual de PocketBase, conecta via `smtplib`, envía un email de prueba al destinatario configurado (o al remitente si no hay destinatario) y retorna JSON con `{ok, mensaje}`. El resultado se muestra inline en la UI sin recargar la página.

### RF-CFG-008 — Auto-test al guardar
Al guardar el grupo email, el sistema redirige con parámetro `test_smtp=1` que dispara automáticamente la prueba de conexión vía JavaScript al cargar la página.

---

## Funcionalidad 3: Configuración de IA (CU-T05)

Grupo `ia` con 10 parámetros para proveedores de inteligencia artificial. Implementado en `app/configuracion/panel.py`.

### RF-CFG-009 — Proveedor de IA configurable
Parámetro `ia_proveedor` con valores: `openai`, `anthropic`, `gemini`, `custom`. Permite cambiar el backend de IA sin modificar código.

### RF-CFG-010 — API keys específicas por proveedor
Además de `ia_api_key` (genérica), existen claves específicas: `ia_api_key_grok` (xAI Grok 3 mini, para narrativa) y `ia_api_key_gemini` (Google Gemini 2.0 Flash, fallback). Todas son tipo `password` (sensibles).

### RF-CFG-011 — Parámetros de generación configurables
`ia_modelo` (nombre del modelo), `ia_endpoint` (endpoint custom para Ollama/proxy), `ia_max_tokens` (default 1000), `ia_temperatura` (default 0.3, rango 0.0–1.0), `ia_timeout_segundos` (default 30), `ia_activa` (bool, habilita/deshabilita el módulo).

---

## Funcionalidad 4: Umbrales de alertas (CU-T07)

Grupo `alertas` con 4 umbrales para alertas del dashboard y ranking de rutas. Implementado en `app/configuracion/panel.py`.

### RF-CFG-012 — Cuatro umbrales configurables
`alerta_otp_umbral_min` (float, OTP mínimo aceptable, default 0.80), `alerta_cancelacion_max` (float, tasa máxima de cancelaciones, default 0.05), `alerta_retraso_minutos` (int, minutos de retraso para alerta, default 15), `alerta_ruta_ineficiente` (float, desviación porcentual de ruta, default 0.15).

### RF-CFG-013 — Invalidación de caché al guardar alertas
Al guardar el grupo alertas, se invalida `invalidar_cache_alertas()` (KPIs del dashboard) e `invalidar_cache_umbral_ruta()` (ranking de eficiencia de rutas). Los cambios aplican inmediatamente sin reiniciar servicios.

---

## Funcionalidad 5: Configuración del pipeline ELT (CU-T08)

Grupo `pipeline` con 4 parámetros de ejecución del pipeline. Implementado en `app/configuracion/panel.py`.

### RF-CFG-014 — Parámetros del pipeline en UI
Cuatro parámetros: `pipeline_batch_size` (int, tamaño de lote carga PocketBase, default 5000), `pipeline_max_workers` (int, hilos concurrentes extract, default 10), `pipeline_reintentos` (int, reintentos por fallo, default 3), `pipeline_schedule` (string, horario).

### RF-CFG-015 — Selector de horario con presets + cron personalizado
El campo `pipeline_schedule` tiene un selector con presets: Manual, Diario, Cada hora, Semanal, Mensual, más una opción "Personalizado (cron)" que muestra un campo de texto para expresiones cron estándar.

### RF-CFG-016 — Validación de expresión cron con croniter
Al guardar, `_validar_schedule()` verifica la expresión cron con la biblioteca `croniter`. Si es inválida, retorna error descriptivo y no persiste el cambio.

### RF-CFG-017 — Sincronización con Airflow vía API REST
Al guardar el schedule, además de persistir en PocketBase, se sincroniza con Airflow mediante `airflow_client.set_variable("pipeline_schedule", valor)`. Si Airflow no responde, PocketBase queda actualizado pero se muestra advertencia al usuario.

---

### RNF-CFG-001 — Invalidación de caché por grupo
Cada grupo invalida únicamente las cachés que le corresponden al guardar: alertas → KPIs y rutas; IA → narrativa y LLM client; pipeline → Airflow variable; email → no hay caché (lectura directa de PB).

### RNF-CFG-002 — Sin reinicio de servicios
Los cambios de configuración aplican sin reiniciar FastAPI, Airflow ni ningún otro servicio. Las cachés se invalidan en memoria.

### RNF-CFG-003 — Timeout de sincronización Airflow
La llamada a la API de Airflow para `set_variable` tiene timeout de 15s. Si excede, PocketBase queda actualizado pero Airflow no, y se muestra mensaje al usuario.

---

### RN-CFG-001 — Los valores sensibles no se sobrescriben con el placeholder
Al guardar un grupo, si el valor enviado es "••••••••" (placeholder de campo sensible), el sistema omite la actualización de ese campo. Esto evita que el placeholder sobrescriba la contraseña real.

### RN-CFG-002 — Grupo "sistema" con 1 configuración
El grupo `sistema` contiene actualmente solo `horizonte_prediccion_max` (meses de proyección predictiva). Es un grupo de extensión futura.

### RN-CFG-003 — pipeline_schedule sincronizado pero no inmediato
El cambio de horario en Airflow puede tardar hasta ~300s en生效 debido al ciclo de parseo del scheduler de Airflow.

---

## Entradas y salidas

| CU | Entrada | Salida |
|----|---------|--------|
| CU-T03 | POST /configuracion/{grupo} con pares clave=valor del grupo | Redirección a /configuracion?msg=... con resultados |
| CU-T04 | POST /configuracion/email/test (sin body, lee de PB) | JSON {ok: bool, mensaje: str} |
| CU-T05 | POST /configuracion/ia con 10 parámetros | Redirección a /configuracion con mensaje |
| CU-T07 | POST /configuracion/alertas con 4 umbrales | Redirección + invalidación de cachés |
| CU-T08 | POST /configuracion/pipeline con 4 parámetros | Redirección + sincronización Airflow |

---

## Escenarios

### Camino feliz — Guardar configuración SMTP
1. El Admin navega a `GET /configuracion`, panel activo "Email / SMTP".
2. Completa los campos: host, puerto, remitente, contraseña, TLS activado.
3. Hace clic en "Guardar Email / SMTP".
4. `POST /configuracion/email` persiste los 7 valores en PocketBase.
5. El sistema redirige con `test_smtp=1`, el JS dispara `POST /configuracion/email/test`.
6. El sistema envía un email de prueba al destinatario y muestra resultado inline.

### Camino feliz — Configurar horario del pipeline
1. El Admin navega al grupo "Pipeline ELT".
2. Selecciona el preset "Diario" (@daily) en el selector de horario.
3. Ajusta batch_size a 10000 y hace clic en "Guardar Pipeline ELT".
4. `POST /configuracion/pipeline` valida @daily con croniter (válido), persiste en PB.
5. El sistema llama a `airflow_client.set_variable("pipeline_schedule", "@daily")`.
6. Redirige con mensaje de éxito.

### Manejo de errores
- **Expresión cron inválida:** Si el admin escribe un cron inválido (ej: "*/5 * *"), `croniter.is_valid()` retorna False, el sistema no persiste y redirige con error descriptivo.
- **Fallo de sincronización Airflow:** Si la API de Airflow no responde, PocketBase queda actualizado y se muestra advertencia: "PocketBase actualizado, pero Airflow no: {error}".
- **SMTP incompleto:** Si falta host o remitente, el test SMTP retorna "Configuración SMTP incompleta." sin intentar la conexión.
- **Error SMTP:** Si el servidor SMTP rechaza la conexión o credenciales, el test retorna el error exacto de `smtplib`.

---

## Criterios de aceptación

- **CU-T03:** Dado que el Administrador navega al panel de configuración, cuando selecciona un grupo, edita sus valores y guarda, entonces el sistema persiste solo los registros de ese grupo en PocketBase y registra la acción en auditoría.
- **CU-T04:** Dado que el Administrador configura los parámetros SMTP, cuando guarda y ejecuta la prueba de conexión, entonces el sistema envía un email real de verificación y muestra el resultado inline.
- **CU-T05:** Dado que el Administrador configura los parámetros de IA, cuando guarda, entonces el sistema persiste los valores, invalida las cachés de narrativa y LLM client, y los nuevos valores se usan en la siguiente llamada.
- **CU-T07:** Dado que el Administrador modifica los umbrales de alertas, cuando guarda, entonces el sistema invalida las cachés del dashboard y ranking de rutas para que los nuevos umbrales se reflejen inmediatamente.
- **CU-T08:** Dado que el Administrador configura el horario del pipeline, cuando el valor es una expresión cron válida, entonces el sistema persiste en PocketBase y sincroniza con Airflow vía API, informando del resultado de cada paso.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permisos `configuracion:ver` y `configuracion:configurar`.
- **PocketBase:** Colección `configuracion_sistema` para persistencia de todos los parámetros.
- **Airflow:** API REST para sincronización de `pipeline_schedule` vía `airflow_client.set_variable()`.
- **croniter:** Biblioteca Python para validación de expresiones cron.
- **smtplib:** Biblioteca estándar Python para prueba de conexión SMTP.
- **Dashboard KPIs:** Función `invalidar_cache_alertas()` en `app/dashboard/kpis.py`.
- **Ranking rutas:** Función `invalidar_cache_umbral_ruta()` en `app/rutas/ranking_eficiencia.py`.
- **IA narrativa:** Función `invalidar_cfg_cache()` en `app/utils/ia_narrativa.py`.
- **LLM client:** Función `invalidar_config()` en `app/asistente_ia/llm_client.py`.

---

## Casos de uso relacionados

- CU-T03 (Configurar parámetros del sistema por grupo)
- CU-T04 (Configurar parámetros de correo electrónico SMTP)
- CU-T05 (Configurar parámetros de inteligencia artificial)
- CU-T07 (Configurar umbrales de alertas del dashboard)
- CU-T08 (Configurar parámetros del pipeline ELT)

---

## Historias de usuario

- Como Administrador, quiero configurar el servidor SMTP desde la UI con prueba de conexión, para que el sistema pueda enviar notificaciones y correos transaccionales sin editar archivos de configuración.
- Como Administrador, quiero seleccionar el proveedor de IA y configurar sus API keys y parámetros, para adaptar el módulo de asistencia analítica al backend disponible.
- Como Administrador, quiero ajustar los umbrales de alertas del dashboard, para que las alertas reflejen los criterios operacionales del momento sin modificar código.
- Como Administrador, quiero configurar el horario y parámetros del pipeline ELT desde la UI, para controlar la frecuencia y resources de las extracciones automáticas.

---

## Fuera de alcance

- Configuración de red, proxies o certificados TLS del servidor.
- Gestión de usuarios y roles del sistema (cubierto en especificación de seguridad).
- Configuración de bases de datos externas o conexiones ODBC.
- Personalización de la UI de configuración por rol de usuario.
- Historial de cambios por parámetro individual (solo auditoría por grupo).
- Rollback automático de configuraciones.
- Variables de entorno del sistema operativo.
