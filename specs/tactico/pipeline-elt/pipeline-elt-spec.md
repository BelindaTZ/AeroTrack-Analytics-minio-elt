# Especificación Táctica — Pipeline ELT

**Módulo:** Pipeline ELT
**Prefijo:** PEL
**Código fuente:** `app/configuracion/panel.py` (configuración), `dags/aerotrack_elt_dag.py` (programación), `dags/config.py` (constantes)
**Casos de uso cubiertos:** CU-T06 (Configurar y programar ejecución del pipeline)
**Actor:** Administrador

---

## Funcionalidad 1: Configurar y programar ejecución del pipeline (CU-T06)

Configuración del horario y parámetros del pipeline ELT desde el panel de configuración. El cronograma se sincroniza entre el repositorio de configuración y el orquestador vía API REST.

### RF-PEL-001 — Seleccionar tipo de programación
El sistema debe ofrecer un selector de programación con opciones: Manual, Cada día, Cada hora, Semanal, Mensual, Anual y expresión cron personalizada.

### RF-PEL-002 — Validar expresión cron
El sistema debe validar la expresión de programación al guardar, verificando que sea un preset conocido o una expresión cron válida. Si el valor es inválido, debe retornar un mensaje de error descriptivo y no persistir el cambio.

### RF-PEL-003 — Persistir programación en repositorio de configuración
El sistema debe guardar el valor de programación validado en la colección de configuración del sistema con clave `pipeline_schedule`.

### RF-PEL-004 — Sincronizar con el orquestador vía API REST
Tras guardar en el repositorio, el sistema debe sincronizar el valor con el orquestador mediante su API REST. Si la sincronización falla, el sistema debe informarlo explícitamente al usuario.

### RF-PEL-005 — Lectura de programación desde variable del orquestador
El sistema debe configurar el pipeline para leer el valor de programación desde una variable del orquestador al momento de su evaluación periódica. Si el valor es "manual" o está vacío, el pipeline solo se ejecuta mediante disparo manual. Si es un preset o expresión cron válida, se usa directamente como horario.

### RF-PEL-006 — Cambio reflejado en el siguiente ciclo de evaluación
El sistema debe informar al usuario que el nuevo horario tomará efecto en el siguiente ciclo de evaluación del orquestador (aproximadamente 300 segundos). No requiere reinicio de servicios ni modificación de archivos.

### RF-PEL-007 — Configurar parámetros del pipeline
El sistema debe exponer los siguientes parámetros de ejecución configurables desde el panel:
- Tamaño de lote para carga desde el repositorio de datos
- Hilos concurrentes para extracción
- Reintentos por fallo en tareas

> **Nota:** Los valores por defecto de estos parámetros están definidos en la semilla de configuración del sistema.

### RNF-PEL-001 — Gestión de horario sin modificar configuración del pipeline
El sistema debe gestionar el cambio de horario exclusivamente mediante variables del orquestador, sin modificar los archivos de definición del pipeline. Esto evita errores de sintaxis y permite cambios sin despliegue.

### RNF-PEL-002 — Validación de programación
El sistema debe validar toda expresión cron personalizada antes de persistirla. Los valores inválidos son rechazados con mensaje de error.

### RNF-PEL-003 — Timeouts en llamadas al orquestador
El sistema debe aplicar timeout de 15 segundos para operaciones generales con el orquestador y 30 segundos para consulta de logs.

### RNF-PEL-004 — Credenciales del orquestador por entorno
Las credenciales y URL del orquestador deben configurarse exclusivamente mediante variables de entorno, sin valores por defecto en código — Principio IV de la constitución.

---

## Reglas de negocio

### RN-PEL-001 — Horario "manual" no ejecuta pipeline automáticamente
Si la programación es "manual" o está vacía, el pipeline no tiene horario definido y solo se ejecuta mediante disparo manual.

### RN-PEL-002 — Una sola ejecución activa a la vez
El orquestador admite como máximo una ejecución simultánea del pipeline. Si ya hay una activa, no se inicia una nueva hasta que la actual termine o falle.

### RN-PEL-003 — Tiempo máximo de ejecución: 4 horas
Si una ejecución excede las 4 horas, el orquestador la marca como fallida automáticamente.

### RN-PEL-004 — Reintentos automáticos por tarea
Cada tarea del pipeline tiene reintentos automáticos con espera entre intentos, gestionados por el orquestador sin intervención del usuario.

### RN-PEL-005 — Pipeline secuencial: extracción → carga → transformación
Las 3 tareas se ejecutan en orden estricto. Cada tarea espera la finalización exitosa de la anterior para comenzar.

### RN-PEL-006 — Fallo de sincronización informado explícitamente
Si la sincronización del horario con el orquestador falla, el sistema debe informarlo explícitamente al usuario, indicando que el repositorio de configuración quedó actualizado pero el orquestador no.

---

## Historias de usuario

- Como Administrador, quiero configurar el horario de ejecución del pipeline desde la interfaz web, para automatizar la actualización de datos sin editar archivos de código ni reiniciar servicios.

---

## Objetivo

Configurar la programación horaria y los parámetros de ejecución del pipeline ELT, sincronizando la configuración entre el repositorio y el orquestador mediante su API REST.

---

## Escenarios

### Camino feliz
1. El Administrador accede al panel de configuración del pipeline y visualiza los valores actuales: horario, tamaño de lote, hilos concurrentes y reintentos.
2. Selecciona el preset "Diario" en el selector de horario y ajusta el tamaño de lote.
3. El sistema valida la expresión de programación.
4. El sistema persiste los valores en el repositorio de configuración y sincroniza con el orquestador mediante su API.
5. En el siguiente ciclo de evaluación del orquestador (aproximadamente 300 segundos), el pipeline adopta el nuevo horario.

### Manejo de errores
- **Expresión cron inválida:** Si la expresión no puede validarse, el sistema retorna un mensaje descriptivo y no persiste el cambio.
- **Fallo de sincronización con el orquestador:** Si el repositorio se actualiza correctamente pero la llamada al orquestador falla, el sistema muestra un mensaje explícito con el error recibido.
- **Timeout en API del orquestador:** Si la llamada excede los 15s, se retorna un error de conexión y la sincronización queda pendiente para el próximo intento.

---

## Criterios de aceptación

- **CU-T06:** Dado que el Administrador configura un horario o parámetro en el panel del pipeline, cuando el valor es válido, entonces el sistema lo persiste en el repositorio de configuración, lo sincroniza con el orquestador vía API REST e informa al usuario del resultado de cada paso.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permiso `pipeline_elt:configurar`.
- **Orquestador:** API REST del orquestador y ciclo de evaluación periódica de aproximadamente 300 segundos.
- **Persistencia:** Colección de configuración del sistema para persistencia de parámetros del pipeline.

---

## Casos de uso relacionados

- CU-T06 (Configurar programación y parámetros del pipeline)

---

## Fuera de alcance

- Modificación directa del archivo DAG desde la interfaz web.
- Configuración de múltiples pipelines independientes.
- Notificaciones por email cuando el pipeline falla.
- Monitoreo en tiempo real de la ejecución (cubierto en la especificación operativa).
- Gestión de conexiones a bases de datos externas.
