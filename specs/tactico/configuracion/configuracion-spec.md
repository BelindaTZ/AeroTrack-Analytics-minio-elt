# Especificación Táctica — Configuración

**Módulo:** Configuración
**Prefijo:** CFG
**Código fuente:** `app/configuracion/`
**Casos de uso cubiertos:** CU-T03 (Ver panel de configuración general), CU-T04 (Configurar y probar servicio de correo electrónico), CU-T05 (Configurar umbrales de alertas analíticas), CU-T06 (Configurar y programar ejecución del pipeline), CU-T07 (Monitorear métricas de almacenamiento MinIO), CU-T08 (Ver estado de salud de servicios del sistema), CU-T09 (Configurar parámetros del asistente IA)
**Actor:** Administrador

---

## Funcionalidad 1: Panel de configuración por grupos (CU-T03)

Panel unificado con navegación lateral por 5 grupos. Cada grupo se guarda de forma independiente. Los datos se persisten en la colección de configuración del sistema.

### RF-CFG-001 — Navegación por 5 grupos
El sistema debe mostrar un panel de configuración con navegación lateral por 5 grupos: Email / SMTP, Alertas y Umbrales, Pipeline ELT, Inteligencia Artificial, Sistema General. Cada grupo tiene icono y color distintivo.

### RF-CFG-002 — Guardado independiente por grupo
El sistema debe actualizar únicamente los registros de configuración cuyo grupo coincide con el solicitado. Los demás grupos no se ven afectados.

### RF-CFG-003 — Tipos de campo según configuración
El sistema debe renderizar cada parámetro de configuración según su tipo de dato: texto, numérico (con paso configurable), booleano (Sí/No), contraseña o email. Los campos no editables se muestran deshabilitados.

### RF-CFG-004 — Campos sensibles enmascarados
El sistema debe enmascarar los campos sensibles en la interfaz y marcarlos con indicador visual. Al guardar, si el valor enviado corresponde al placeholder de enmascarado, el sistema debe ignorarlo y preservar el valor real existente.

### RF-CFG-005 — Auditoría de cambios
El sistema debe registrar en auditoría cada guardado exitoso de configuración, identificando el grupo modificado.

---

## Funcionalidad 2: Configuración SMTP (CU-T04)

Grupo `email` con 7 parámetros para el servidor de correo. Incluye prueba de conexión con envío de email real.

### RF-CFG-006 — Parámetros SMTP configurables
El sistema debe permitir configurar siete parámetros SMTP: servidor, puerto (default 587), dirección remitente, contraseña SMTP (sensible), uso de TLS (default activado), activación de alertas por email y dirección destinataria de alertas.

### RF-CFG-007 — Prueba de conexión SMTP desde UI
El sistema debe permitir probar la conexión SMTP utilizando la configuración actual, enviando un email de prueba al destinatario configurado (o al remitente si no hay destinatario) y mostrando el resultado inline sin recargar la página.

### RF-CFG-008 — Auto-test al guardar
Al guardar el grupo de configuración de email, el sistema debe disparar automáticamente la prueba de conexión SMTP.

---

## Funcionalidad 3: Configuración de IA (CU-T09)

Grupo `ia` con 10 parámetros para proveedores de inteligencia artificial.

### RF-CFG-009 — Proveedor de IA configurable
El sistema debe ofrecer un parámetro de proveedor de IA con opciones: openai, anthropic, gemini, custom. Permite cambiar el backend de IA sin modificar código.

### RF-CFG-010 — API keys específicas por proveedor
El sistema debe gestionar claves de API diferenciadas: una clave genérica y claves específicas para los proveedores xAI Grok (para narrativa) y Google Gemini (fallback). Todas las claves son campos sensibles.

### RF-CFG-011 — Parámetros de generación configurables
El sistema debe permitir configurar los parámetros de generación de IA: nombre del modelo, endpoint personalizado (para proxies locales), máximo de tokens (default 1000), temperatura (default 0.3, rango 0.0–1.0), timeout en segundos (default 30) y habilitación del módulo.

---

## Funcionalidad 4: Umbrales de alertas (CU-T05)

Grupo `alertas` con 4 umbrales para alertas del dashboard y ranking de rutas.

### RF-CFG-012 — Cuatro umbrales configurables
El sistema debe permitir configurar cuatro umbrales de alerta: OTP mínimo aceptable (default 0.80), tasa máxima de cancelaciones (default 0.05), minutos de retraso para alerta (default 15) y desviación porcentual de ruta ineficiente (default 0.15).

### RF-CFG-013 — Invalidación de caché al guardar alertas
Al guardar el grupo de alertas, el sistema debe invalidar las cachés del dashboard y del ranking de eficiencia de rutas, de modo que los nuevos umbrales apliquen inmediatamente sin reiniciar servicios.

---

## Funcionalidad 5: Configuración del pipeline ELT (CU-T06)

Grupo `pipeline` con 4 parámetros de ejecución del pipeline.

### RF-CFG-014 — Parámetros del pipeline en UI
El sistema debe mostrar cuatro parámetros configurables del pipeline: tamaño de lote (default 5000), hilos concurrentes para extracción (default 10), reintentos por fallo (default 3) y expresión de horario.

### RF-CFG-015 — Selector de horario con presets + cron personalizado
El sistema debe ofrecer un selector de horario con presets predefinidos (Manual, Diario, Cada hora, Semanal, Mensual) más una opción de expresión cron personalizada con campo de texto libre.

### RF-CFG-016 — Validación de expresión cron
Al guardar, el sistema debe validar la expresión de programación. Si es inválida, debe retornar un error descriptivo y no persistir el cambio.

### RF-CFG-017 — Sincronización con el orquestador vía API REST
Al guardar el horario, el sistema debe persistirlo en el repositorio de configuración y sincronizarlo con el orquestador. Si el orquestador no responde, el repositorio queda actualizado y el sistema muestra advertencia al usuario.

---

## Funcionalidad 6: Monitoreo de salud de servicios y métricas de almacenamiento (CU-T07, CU-T08)

Panel de monitoreo en tiempo real del estado de los servicios de infraestructura.

### RF-CFG-018 — Mostrar estado de servicios en tiempo real
El sistema debe verificar la disponibilidad y latencia de los 3 servicios críticos (repositorio de datos, almacenamiento de objetos y orquestador), retornando el estado (online, degradado u offline) con latencia en milisegundos para cada uno.

### RF-CFG-019 — Métricas de almacenamiento por bucket (CU-T07)
El sistema debe calcular y mostrar métricas de almacenamiento por bucket: número de objetos y tamaño total en MB. Las métricas se incluyen tanto en la vista HTML como en el endpoint JSON.

### RF-CFG-020 — Auto-refresh JSON cada 30 segundos (CU-T08)
El sistema debe exponer el estado del monitoreo en formato JSON para actualización automática cada 30 segundos, permitiendo actualizar los indicadores sin recargar la página.

### RNF-CFG-004 — Monitoreo no bloquea al usuario
El sistema debe verificar cada servicio de forma independiente. Si un servicio falla con excepción, retorna estado offline con latencia indicada como -1, sin interrumpir la verificación de los demás servicios.

---

### RNF-CFG-001 — Invalidación de caché por grupo
El sistema debe invalidar únicamente las cachés correspondientes al grupo guardado: alertas → KPIs y rutas; IA → narrativa y cliente LLM; pipeline → variable del orquestador; email → sin caché (lectura directa del repositorio).

### RNF-CFG-002 — Sin reinicio de servicios
Los cambios de configuración deben aplicar sin reiniciar ningún servicio. Las cachés se invalidan en memoria.

### RNF-CFG-003 — Timeout de sincronización con el orquestador
La sincronización de la variable de horario con el orquestador debe tener timeout de 15s. Si se excede, el repositorio queda actualizado pero el orquestador no, y se muestra mensaje al usuario.

---

### RN-CFG-001 — Los valores sensibles no se sobrescriben con el placeholder
Al guardar un grupo, si el valor enviado corresponde al placeholder de campo sensible, el sistema omite la actualización de ese campo. Esto evita que el placeholder sobrescriba el valor real almacenado.

### RN-CFG-002 — Grupo "sistema" con 1 configuración
El grupo `sistema` contiene actualmente solo el parámetro de horizonte máximo de predicción (meses de proyección predictiva). Este grupo no tiene datos semilla en el setup inicial; se crea el primer registro cuando el Administrador guarda el parámetro desde el panel. Es un grupo de extensión futura.

### RN-CFG-003 — pipeline_schedule sincronizado pero no inmediato
El cambio de horario puede tardar hasta 300 segundos en tomar efecto, debido al ciclo de evaluación periódica del orquestador.

---

## Entradas y salidas

| CU | Entrada | Salida |
|----|---------|--------|
| CU-T03 | GET /configuracion (Cookie JWT) | HTML con panel de 5 grupos y navegación lateral |
| CU-T03 | POST /configuracion/{grupo} con pares clave=valor del grupo | Redirección a /configuracion?msg=... con resultados |
| CU-T04 | POST /configuracion/email/test (sin body, lee de repositorio) | JSON {ok: bool, mensaje: str} |
| CU-T05 | POST /configuracion/alertas con 4 umbrales | Redirección + invalidación de cachés |
| CU-T06 | POST /configuracion/pipeline con 4 parámetros | Redirección + sincronización con orquestador |
| CU-T07 | GET /configuracion/monitoreo (Cookie JWT) | HTML con estado de los 3 servicios críticos |
| CU-T07 | GET /configuracion/monitoreo/json (Cookie JWT) | JSON {servicios, todos_ok} para auto-refresh |
| CU-T09 | POST /configuracion/ia con 10 parámetros | Redirección a /configuracion con mensaje |

---

## Escenarios

### Camino feliz — Guardar configuración SMTP
1. El Admin navega al panel de configuración, grupo "Email / SMTP".
2. Completa los campos: host, puerto, remitente, contraseña, TLS activado.
3. Hace clic en "Guardar Email / SMTP".
4. El sistema persiste los 7 valores en el repositorio de configuración.
5. El sistema dispara automáticamente la prueba de conexión SMTP y muestra el resultado inline.

### Camino feliz — Configurar horario del pipeline
1. El Admin navega al grupo "Pipeline ELT".
2. Selecciona el preset "Diario" en el selector de horario.
3. Ajusta el tamaño de lote y hace clic en "Guardar Pipeline ELT".
4. El sistema valida la expresión de programación, persiste en el repositorio.
5. El sistema sincroniza con el orquestador y redirige con mensaje de éxito.

### Manejo de errores
- **Expresión cron inválida:** El sistema no persiste y redirige con error descriptivo.
- **Fallo de sincronización con el orquestador:** El repositorio queda actualizado y se muestra advertencia: "Repositorio actualizado, pero el orquestador no: {error}".
- **SMTP incompleto:** Si falta host o remitente, el test retorna "Configuración SMTP incompleta." sin intentar la conexión.
- **Error SMTP:** Si el servidor rechaza la conexión o credenciales, el test retorna el error recibido.

---

## Criterios de aceptación

- **CU-T03:** Dado que el Administrador navega al panel de configuración, cuando selecciona un grupo, edita sus valores y guarda, entonces el sistema persiste solo los registros de ese grupo en el repositorio y registra la acción en auditoría.
- **CU-T04:** Dado que el Administrador configura los parámetros SMTP, cuando guarda y ejecuta la prueba de conexión, entonces el sistema envía un email real de verificación y muestra el resultado inline.
- **CU-T05:** Dado que el Administrador modifica los umbrales de alertas, cuando guarda, entonces el sistema invalida las cachés del dashboard y ranking de rutas para que los nuevos umbrales se reflejen inmediatamente.
- **CU-T06:** Dado que el Administrador configura el horario del pipeline, cuando el valor es una expresión válida, entonces el sistema persiste en el repositorio y sincroniza con el orquestador vía API, informando del resultado de cada paso.
- **CU-T07:** Dado que el Administrador accede al monitoreo, entonces el sistema muestra el estado (online/offline/degradado) y latencia de los 3 servicios críticos, incluyendo métricas de almacenamiento por bucket (objetos y tamaño en MB).
- **CU-T08:** Dado que el Administrador accede al monitoreo, cuando un servicio no responde, entonces su estado muestra "offline" con el mensaje de error; los servicios restantes se muestran correctamente (degradación parcial, no total).
- **CU-T09:** Dado que el Administrador configura los parámetros de IA, cuando guarda, entonces el sistema persiste los valores, invalida las cachés de narrativa y cliente LLM, y los nuevos valores se usan en la siguiente llamada.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permisos `configuracion:ver` y `configuracion:configurar`.
- **Persistencia:** Colección de configuración del sistema para persistencia de todos los parámetros.
- **Orquestador:** API REST del orquestador para sincronización del horario del pipeline.
- **Validación cron:** Biblioteca para validación de expresiones de programación cron.
- **Correo electrónico:** Biblioteca estándar del entorno para prueba de conexión SMTP.

---

## Casos de uso relacionados

- CU-T03 (Ver panel de configuración general)
- CU-T04 (Configurar y probar servicio de correo electrónico)
- CU-T05 (Configurar umbrales de alertas analíticas)
- CU-T06 (Configurar y programar ejecución del pipeline)
- CU-T07 (Monitorear métricas de almacenamiento MinIO)
- CU-T08 (Ver estado de salud de servicios del sistema)
- CU-T09 (Configurar parámetros del asistente IA)

---

## Historias de usuario

- Como Administrador, quiero configurar el servidor SMTP desde la UI con prueba de conexión, para que el sistema pueda enviar notificaciones y correos transaccionales sin editar archivos de configuración.
- Como Administrador, quiero seleccionar el proveedor de IA y configurar sus API keys y parámetros, para adaptar el módulo de asistencia analítica al backend disponible.
- Como Administrador, quiero ajustar los umbrales de alertas del dashboard, para que las alertas reflejen los criterios operacionales del momento sin modificar código.
- Como Administrador, quiero configurar el horario y parámetros del pipeline ELT desde la UI, para controlar la frecuencia y recursos de las extracciones automáticas.

---

## Fuera de alcance

- Configuración de red, proxies o certificados TLS del servidor.
- Gestión de usuarios y roles del sistema (cubierto en especificación de seguridad).
- Configuración de bases de datos externas o conexiones ODBC.
- Personalización de la UI de configuración por rol de usuario.
- Historial de cambios por parámetro individual (solo auditoría por grupo).
- Rollback automático de configuraciones.
- Variables de entorno del sistema operativo.
