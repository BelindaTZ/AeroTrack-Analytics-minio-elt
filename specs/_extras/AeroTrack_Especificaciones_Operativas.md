# AeroTrack_Especificaciones_Operativas.pdf



AEROTRACK ANALYTICS: SISTEMA DE BUSINESS INTELLIGENCE AERONÁUTICO
Documento de Especificaciones Operativas
Belinda Toaquiza1

1 Facultad de Ciencias de la Computación, 
Universidad Técnica Estatal de Quevedo, Ecuador

1 Ingeniería en software, Sexto semestre, Paralelo B

1{btoaquizaz@uteq.edu.ec}

Repositorio del sistema en GitHub 

Repositorio de documentación (Empresarial/sistema)  3 Docs [Entrega anterior corregida, Especificaciones y Diagramas UML]

Asignatura: Construcción De Software
Fecha de entrega: 21/06/2026




Resumen: AeroTrack.


Palabras clave: Business.

 Índice
1. Introducción y Alcance	3
2. Especificación General del Sistema	3
2.1 Nombre del sistema y objetivo general	3
2.2 Actores principales	3
2.3 Módulos del sistema	3
2.4 Reglas generales	4
2.5 Restricciones generales	5
3. Especificaciones por Módulo	6
3.1 Módulo: Seguridad	7
3.1.1 Objetivo	7
3.1.2 Actores	7
3.1.3 Requisitos funcionales	7
3.1.4 Requisitos no funcionales	7
3.1.5 Reglas de negocio	7
3.1.6 Entradas y salidas	7
3.1.7 Escenarios	7
3.1.8 Criterios de aceptación	7
3.1.9 Dependencias	7
3.1.10 Casos de uso relacionados	7
3.1.11 Fuera de alcance	7
3.2 Módulo: Pipeline ELT	8
3.2.1 Objetivo	8
3.2.2 Actores	8
3.2.3 Requisitos funcionales	8
3.2.4 Requisitos no funcionales	8
3.2.5 Reglas de negocio	8
3.2.6 Entradas y salidas	8
3.2.7 Escenarios	8
3.2.8 Criterios de aceptación	8
3.2.9 Dependencias	8
3.2.10 Casos de uso relacionados	8
3.2.11 Fuera de alcance	8
3.3 Módulo: Modelo Dimensional	9
3.3.1 Objetivo	9
3.3.2 Actores	9
3.3.3 Requisitos funcionales	9
3.3.4 Requisitos no funcionales	9
3.3.5 Reglas de negocio	9
3.3.6 Entradas y salidas	9
3.3.7 Escenarios	9
3.3.8 Criterios de aceptación	9
3.3.9 Dependencias	9
3.3.10 Casos de uso relacionados	9
3.3.11 Fuera de alcance	9
3.4 Módulo: Dashboard	10
3.4.1 Objetivo	10
3.4.2 Actores	10
3.4.3 Requisitos funcionales	10
3.4.4 Requisitos no funcionales	10
3.4.5 Reglas de negocio	10
3.4.6 Entradas y salidas	10
3.4.7 Escenarios	10
3.4.8 Criterios de aceptación	10
3.4.9 Dependencias	10
3.4.10 Casos de uso relacionados	10
3.4.11 Fuera de alcance	10
3.5 Módulo: Puntualidad	11
3.5.1 Objetivo	11
3.5.2 Actores	11
3.5.3 Requisitos funcionales	11
3.5.4 Requisitos no funcionales	11
3.5.5 Reglas de negocio	11
3.5.6 Entradas y salidas	11
3.5.7 Escenarios	11
3.5.8 Criterios de aceptación	11
3.5.9 Dependencias	11
3.5.10 Casos de uso relacionados	11
3.5.11 Fuera de alcance	11
3.6 Módulo: Rutas	12
3.6.1 Objetivo	12
3.6.2 Actores	12
3.6.3 Requisitos funcionales	12
3.6.4 Requisitos no funcionales	12
3.6.5 Reglas de negocio	12
3.6.6 Entradas y salidas	12
3.6.7 Escenarios	12
3.6.8 Criterios de aceptación	12
3.6.9 Dependencias	12
3.6.10 Casos de uso relacionados	12
3.6.11 Fuera de alcance	12
3.7 Módulo: Cancelaciones	13
3.7.1 Objetivo	13
3.7.2 Actores	13
3.7.3 Requisitos funcionales	13
3.7.4 Requisitos no funcionales	13
3.7.5 Reglas de negocio	13
3.7.6 Entradas y salidas	13
3.7.7 Escenarios	13
3.7.8 Criterios de aceptación	13
3.7.9 Dependencias	13
3.7.10 Casos de uso relacionados	13
3.7.11 Fuera de alcance	13
3.8 Módulo: Reportes	14
3.8.1 Objetivo	14
3.8.2 Actores	14
3.8.3 Requisitos funcionales	14
3.8.4 Requisitos no funcionales	14
3.8.5 Reglas de negocio	14
3.8.6 Entradas y salidas	14
3.8.7 Escenarios	14
3.8.8 Criterios de aceptación	14
3.8.9 Dependencias	14
3.8.10 Casos de uso relacionados	14
3.8.11 Fuera de alcance	14
3.9 Módulo: Configuración	15
3.9.1 Objetivo	15
3.9.2 Actores	15
3.9.3 Requisitos funcionales	15
3.9.4 Requisitos no funcionales	15
3.9.5 Reglas de negocio	15
3.9.6 Entradas y salidas	15
3.9.7 Escenarios	15
3.9.8 Criterios de aceptación	15
3.9.9 Dependencias	15
3.9.10 Casos de uso relacionados	15
3.9.11 Fuera de alcance	15
3.10 Módulo: Auditoría	16
3.10.1 Objetivo	16
3.10.2 Actores	16
3.10.3 Requisitos funcionales	16
3.10.4 Requisitos no funcionales	16
3.10.5 Reglas de negocio	16
3.10.6 Entradas y salidas	16
3.10.7 Escenarios	16
3.10.8 Criterios de aceptación	16
3.10.9 Dependencias	16
3.10.10 Casos de uso relacionados	16
3.10.11 Fuera de alcance	16
3.11 Módulo: Predictivo	17
3.11.1 Objetivo	17
3.11.2 Actores	17
3.11.3 Requisitos funcionales	17
3.11.4 Requisitos no funcionales	17
3.11.5 Reglas de negocio	17
3.11.6 Entradas y salidas	17
3.11.7 Escenarios	17
3.11.8 Criterios de aceptación	17
3.11.9 Dependencias	17
3.11.10 Casos de uso relacionados	17
3.11.11 Fuera de alcance	17
3.12 Módulo: Asistente IA	18
3.12.1 Objetivo	18
3.12.2 Actores	18
3.12.3 Requisitos funcionales	18
3.12.4 Requisitos no funcionales	18
3.12.5 Reglas de negocio	18
3.12.6 Entradas y salidas	18
3.12.7 Escenarios	18
3.12.8 Criterios de aceptación	18
3.12.9 Dependencias	18
3.12.10 Casos de uso relacionados	18
3.12.11 Fuera de alcance	18
3.13 Módulo: Clientes (Entrega 4)	19
3.13.1 Objetivo	19
3.13.2 Actores	19
3.13.3 Requisitos funcionales	19
3.13.4 Requisitos no funcionales	19
3.13.5 Reglas de negocio	19
3.13.6 Entradas y salidas	19
3.13.7 Escenarios	19
3.13.8 Criterios de aceptación	19
3.13.9 Dependencias	19
3.13.10 Casos de uso relacionados	19
3.13.11 Fuera de alcance	19
3.14 Módulo: Socios API (Entrega 4)	20
3.14.1 Objetivo	20
3.14.2 Actores	20
3.14.3 Requisitos funcionales	20
3.14.4 Requisitos no funcionales	20
3.14.5 Reglas de negocio	20
3.14.6 Entradas y salidas	20
3.14.7 Escenarios	20
3.14.8 Criterios de aceptación	20
3.14.9 Dependencias	20
3.14.10 Casos de uso relacionados	20
3.14.11 Fuera de alcance	20
4. Trazabilidad: Módulo → Casos de Uso	21
5. Anexos	22
5.1 Glosario	22
5.2 Resumen de la constitución del proyecto (v2.1.0)	22


 1. Introducción y Alcance
Este documento contiene la especificación operativa de AeroTrack Analytics, organizada por módulos funcionales según la metodología de desarrollo guiada por especificaciones (Spec Driven Development) implementada con Spec Kit. Es complementario a la «Documentación Empresarial v3», que analiza el sistema desde el modelo de negocio y los objetivos estratégicos, tácticos y operativos; y a la constitución del proyecto («constitution.md» v2.1.0), que define las reglas no negociables de arquitectura, calidad y stack tecnológico que toda especificación de módulo debe respetar.
Las especificaciones no se concentran en un solo archivo: cada módulo tiene su propia especificación con objetivo, actores, requisitos funcionales y no funcionales, reglas de negocio, entradas y salidas, escenarios, criterios de aceptación, dependencias y alcance delimitado. Las secciones marcadas como [Pendiente] se completarán de forma incremental, módulo por módulo, con el skill speckit-specify.
2. Especificación General del Sistema
2.1 Nombre del sistema y objetivo general
AeroTrack Analytics: sistema de inteligencia de negocios aeronáutico que transforma los datos operacionales de vuelo del Bureau of Transportation Statistics (BTS) y la Administración Federal de Aviación (FAA) en inteligencia estratégica para aerolíneas, operadores aeroportuarios e instituciones financieras del sector, bajo un modelo de negocio empresa a empresa (B2B).
2.2 Actores principales
ACTOR	RESPONSABILIDAD
Administrador	Configuración, operación y mantenimiento del sistema. Gestiona usuarios, roles, parámetros operativos y el pipeline de actualización de datos.
Analista De Datos	Empleado de AeroTrack que utiliza los módulos analíticos para producir la inteligencia entregada a los clientes aerolínea.
Socio Tecnológico	Actor externo que consume los resultados analíticos mediante la interfaz de programación del sistema (Entrega 4). No accede a la interfaz web.
Tabla 1. Actores del sistema.
2.3 Módulos del sistema
Nº	MÓDULO	PAQUETE TÉCNICO	ENTREGA
1	Seguridad	app/seguridad/	Entrega 1
2	Pipeline ELT	dags/ (Apache Airflow)	Entrega 1
3	Modelo Dimensional	app/modelo_dimensional/	Entrega 1
4	Dashboard	app/dashboard/	Entrega 2
5	Puntualidad	app/puntualidad/	Entrega 2
6	Rutas	app/rutas/	Entrega 2
7	Cancelaciones	app/cancelaciones/	Entrega 2
8	Reportes	app/reportes/ (transversal)	Entrega 2
9	Configuración	app/configuracion/	Entrega 2
10	Auditoría	app/auditoria/	Entrega 2
11	Predictivo	app/predictivo/	Entrega 3
12	Asistente IA	app/asistente_ia/ + app/utils/ia_narrativa.py	Entrega 3
13	Clientes (Entrega 4)	Planificado — app/clientes/	Entrega 4 
14	Socios API (Entrega 4)	Planificado — app/socios_api/	Entrega 4 
Tabla 2. Catálogo de módulos del sistema.
2.4 Reglas generales
Aplicables a todos los módulos, derivadas de la constitución del proyecto v2.1.0:
REGLA	PRINCIPIO DE LA CONSTITUCIÓN
Toda Autorización Se Valida En La Capa De Aplicación (Fastapi), Nunca En La Base De Datos.	III — RBAC en la capa de aplicación
Ningún Módulo Analítico Lee Directamente De Las Capas De Staging.	I — Separación de capas de almacenamiento
Ningún Secreto (Contraseñas, Claves, Tokens) Puede Tener Un Valor Por Defecto En Código.	IV — Configuración sin secretos hardcodeados
Toda Acción Administrativa Relevante Se Registra En El Log De Auditoría Inmutable.	V — Auditoría inmutable
Los Subsistemas No Críticos Degradan Sin Propagar Errores Al Usuario.	VI — Degradación de servicios no críticos
Todo Prompt Enviado A Un Modelo De Ia Contiene Solo Kpis Agregados, Nunca Filas Individuales.	X — Contexto de IA limitado a KPIs
Todo Valor Visual Se Declara Como Token Css, Nunca Hardcodeado En Un Template.	XII — Design tokens centralizados
Tabla 3. Reglas generales del sistema.

2.5 Restricciones generales
Python 3.12 unificado en todo el stack (FastAPI y Airflow). Stack fijo: FastAPI + Jinja2 + Bootstrap 5.3.3, PocketBase 0.22.4, MinIO, Apache Airflow 2.9.3, PostgreSQL 15 (uso exclusivo: metadatos de Airflow), Docker/docker-compose. Frontend exclusivamente en Vanilla JS, sin frameworks de runtime. El sistema se evalúa conforme al modelo de calidad ISO/IEC 25010:2023 (ver constitución, Principio XVIII).
 3. Especificaciones por Módulo
Cada módulo sigue la misma plantilla, alineada a una estructura fija y con los archivos spec.md de Spec Kit.
3.1 Módulo: Seguridad
Paquete técnico: app/seguridad/ | Entrega: Entrega 1
3.1.1 Objetivo
Gestionar la autenticación de usuarios y el control de acceso basado en roles (RBAC) para todo el sistema.
3.1.2 Actores
Administrador (gestión de usuarios, roles y permisos); Administrador y Analista de Datos (inicio de sesión, perfil propio).
3.1.3 Contexto del problema
AeroTrack maneja datos operacionales de clientes aerolínea bajo un modelo B2B donde cada cliente espera confidencialidad sobre su propia información competitiva. Sin un mecanismo de autenticación y control de acceso granular, cualquier usuario interno con acceso al sistema podría consultar, modificar o eliminar configuraciones y datos críticos sin que quede registro de quién lo hizo, exponiendo a la empresa a riesgo de incumplimiento contractual y pérdida de confianza de sus clientes.
3.1.4 Requisitos funcionales
Funcionalidad 1: Gestionar usuarios del sistema (CU-T01)
•	RF-SEG-001: El sistema debe permitir al Administrador crear usuarios con nombre, email y rol, generando una contraseña temporal y enviándola por correo electrónico.
•	RF-SEG-002: El sistema debe permitir editar nombre, email y rol de un usuario existente.
•	RF-SEG-003: El sistema debe permitir activar o desactivar usuarios.
•	RF-SEG-004: El sistema debe permitir restablecer la contraseña de un usuario generando una nueva contraseña temporal.
•	RF-SEG-005: El sistema debe listar usuarios de forma paginada (20 por página), con filtros por nombre/email, rol y estado.
Funcionalidad 2: Administrar roles y asignar permisos (CU-T02)
•	RF-SEG-006: El sistema debe permitir crear, editar y eliminar roles, salvo los marcados como de sistema (es_sistema=True).
•	RF-SEG-007: El sistema debe permitir configurar la matriz de permisos de un rol (módulo × acción), reemplazando por completo los permisos anteriores al guardar.
•	RF-SEG-008: El sistema debe mostrar el número de usuarios asignados a cada rol en el listado.
Funcionalidad 3: Iniciar sesión (CU-O01) y Cerrar sesión (CU-O02)
•	RF-SEG-009: El sistema debe autenticar al usuario mediante email y contraseña contra PocketBase, generando un JWT almacenado en cookie httponly con SameSite=Lax.
•	RF-SEG-010: El sistema debe impedir el inicio de sesión de cuentas inactivas, aun con credenciales válidas.
•	RF-SEG-011: El sistema debe cerrar sesión únicamente mediante solicitud POST, eliminando la cookie.
Funcionalidad 4: Ver y editar perfil propio (CU-O03)
•	RF-SEG-012: El sistema debe permitir a cualquier usuario autenticado consultar los datos de su propio perfil.
•	RF-SEG-013: El sistema debe permitir editar el nombre y el email propios, validando el formato del email y verificando que no esté en uso por otro usuario.
•	RF-SEG-014: El sistema debe permitir cambiar la contraseña propia, verificando primero la contraseña actual.
Funcionalidad 5: Ver matriz de permisos del sistema (CU-O04)
•	RF-SEG-015: El sistema debe mostrar, en modo de solo lectura, todos los roles y módulos con sus acciones habilitadas por combinación.
3.1.5 Requisitos no funcionales
•	RNF-SEG-001: El JWT debe usar algoritmo HS256 con tiempo de vida configurable por variable de entorno, sin valor por defecto en código (Principio IV de la constitución).
•	RNF-SEG-002: Toda autorización se valida en la capa de aplicación (FastAPI), nunca en la base de datos (Principio III).
•	RNF-SEG-003: La caché de permisos por rol debe expirar en un máximo de 5 minutos.
•	RNF-SEG-004: Toda acción administrativa relevante (login, login fallido, logout, CRUD de usuarios/roles, cambios de permisos, cambios de perfil) debe registrarse en el log de auditoría inmutable (Principio V).
3.1.6 Reglas de negocio
•	RN-SEG-001: Un usuario no puede desactivar su propia cuenta.
•	RN-SEG-002: Una cuenta inactiva no puede iniciar sesión aunque sus credenciales sean correctas.
•	RN-SEG-003: Los roles marcados como es_sistema=True no pueden editarse ni eliminarse.
•	RN-SEG-004: No se puede eliminar un rol con al menos un usuario asignado.
•	RN-SEG-005: Guardar los permisos de un rol reemplaza la totalidad de sus permisos previos; no es una operación incremental.
•	RN-SEG-006: El cambio de email en el perfil propio no invalida la sesión activa, porque el JWT usa el id de PocketBase, no el email, como subject.
3.1.7 Entradas y salidas
FUNCIÓN / ENDPOINT	ENTRADAS	SALIDAS
Post /Auth/Login	email, password	Cookie access_token + redirect a /pipeline, o error en pantalla
Post /Auth/Logout	Cookie JWT	Cookie eliminada + redirect a login
Get /Auth/Perfil	Cookie JWT	Datos del usuario y su rol
Post /Auth/Perfil/Datos	nombre, email	Perfil actualizado o error de validación/duplicado
Post /Auth/Perfil/Password	password_actual, password_nuevo, password_confirm	Contraseña actualizada o error
Post /Auth/Usuarios	nombre, email, rol_id	Usuario creado + email de bienvenida
Post /Auth/Roles/{Rid}/Permisos	Checkboxes por módulo×acción	Permisos guardados, caché invalidada
Get /Auth/Roles/Matriz	—	Tabla roles × módulos × acciones
3.1.8 Escenarios
Camino feliz: login exitoso con redirección al panel; edición de perfil (nombre/email/contraseña) con confirmación; gestión completa de usuarios, roles y permisos; consulta de matriz de permisos actualizada tras cada cambio.
Manejo de errores: credenciales incorrectas (mensaje en pantalla, login fallido auditado); cuenta desactivada (mismo flujo de error); contraseña nueva distinta de la confirmación; contraseña actual incorrecta al cambiarla; email duplicado al editar perfil o crear usuario; intento de editar/eliminar un rol de sistema; intento de eliminar un rol con usuarios asignados; JWT inválido o expirado (redirección automática a login).
3.1.9 Criterios de aceptación
•	Dado un usuario con credenciales válidas y cuenta activa, cuando inicia sesión, entonces accede al sistema y la acción queda auditada.
•	Dado un usuario con cuenta inactiva, cuando intenta iniciar sesión con credenciales correctas, entonces el sistema rechaza el acceso.
•	Dado un Administrador editando un rol con es_sistema=True, cuando intenta guardar cambios, entonces el sistema rechaza la operación.
•	Dado un usuario autenticado, cuando cambia su email a uno ya registrado por otro usuario, entonces el sistema rechaza el cambio con mensaje de duplicado.
•	Dado un usuario autenticado, cuando cambia su email exitosamente, entonces su sesión activa permanece válida.
3.1.10 Dependencias
Ninguna. Es el módulo base del que dependen todos los demás para autorización.
3.1.11 Casos de uso relacionados
CU-T01 · CU-T02 · CU-O01 · CU-O02 · CU-O03 · CU-O04
3.1.12 Fuera de alcance
Recuperación de contraseña autoservicio (sin intervención de un Administrador); autenticación multifactor (MFA); inicio de sesión mediante proveedores externos (SSO/OAuth); auto-asignación o cambio del propio rol desde el perfil.
3.2 Módulo: Pipeline ELT
Paquete técnico: dags/ (Apache Airflow) | Entrega: Entrega 1
3.2.1 Objetivo
Orquestar la extracción, carga y transformación automatizada de los datos de vuelo desde la fuente operacional hacia el modelo dimensional analítico.
3.2.2 Actores
Administrador.
3.2.3 Contexto del problema
Los datos de origen (BTS/FAA) ingresan en bruto a la capa de staging y pierden valor analítico si no se transforman periódicamente al modelo dimensional. Sin un proceso automatizable y supervisable, la actualización dependería de que un técnico la ejecutara manualmente cada vez, con riesgo de que los analistas trabajen sobre datos desactualizados y sin forma de diagnosticar ni recuperar fallos sin reiniciar todo el ciclo.
3.2.4 Requisitos funcionales
Funcionalidad 1: Configurar y programar ejecución del pipeline (CU-T06)
•	RF-PEL-001: El sistema debe permitir al Administrador definir el horario de ejecución del pipeline mediante presets (Manual, Diario, Cada hora, Semanal, Mensual) o una expresión cron personalizada, validada antes de guardar.
•	RF-PEL-002: El sistema debe sincronizar el horario configurado con una Variable de Airflow (pipeline_schedule), sin modificar el archivo del DAG.
•	RF-PEL-003: El sistema debe permitir configurar el tamaño de lote, número de procesos paralelos y reintentos de extracción.
•	RF-PEL-004: El sistema debe informar al Administrador que el cambio de horario puede tardar hasta el siguiente ciclo de refresco del scheduler de Airflow (~300 s).
Funcionalidad 2: Ejecutar pipeline ELT manualmente (CU-O05)
•	RF-PEL-005: El sistema debe permitir disparar manualmente la ejecución completa del pipeline desde la interfaz web.
Funcionalidad 3: Monitorear estado del DAG en ejecución (CU-O06)
•	RF-PEL-006: El sistema debe mostrar en tiempo real el estado de cada etapa del pipeline en ejecución, actualizando automáticamente cada 10 segundos.
Funcionalidad 4: Consultar historial de ejecuciones (CU-O07)
•	RF-PEL-007: El sistema debe mostrar el historial de las últimas 50 ejecuciones, con fecha, duración y estado final.
Funcionalidad 5: Ver logs de error y reintentar ejecución (CU-O08)
•	RF-PEL-008: El sistema debe mostrar el log detallado de una tarea específica de un run.
•	RF-PEL-009: El sistema debe permitir reintentar una tarea fallida sin reiniciar el pipeline completo, mostrando el botón de reintento solo cuando el estado de la tarea sea "failed" o "up_for_retry".
3.2.5 Requisitos no funcionales
•	RNF-PEL-001: Las llamadas a la API de Airflow deben tener timeout de 15 segundos para operaciones generales y 30 segundos para consulta de logs.
•	RNF-PEL-002: El pipeline no debe permitir ejecuciones concurrentes (max_active_runs=1).
•	RNF-PEL-003: Toda ejecución manual, cambio de horario y reintento de tarea debe registrarse en el log de auditoría inmutable.
•	RNF-PEL-004: Ningún secreto ni URL de Airflow puede tener valor por defecto en código.
3.2.6 Reglas de negocio
•	RN-PEL-001: El DAG nunca se reescribe para cambiar el horario; el horario se lee desde una Variable de Airflow al momento de definirse el DAG.
•	RN-PEL-002: Si la sincronización del horario con Airflow falla, el sistema debe informarlo explícitamente en vez de fallar en silencio, indicando que PocketBase quedó actualizado pero Airflow no.
•	RN-PEL-003: Una ejecución del pipeline tiene un tiempo máximo de 4 horas (dagrun_timeout), tras el cual se marca como fallida.
•	RN-PEL-004: Cada tarea individual reintenta automáticamente hasta 2 veces de forma interna (retries=2), independientemente del reintento manual desde la UI.
3.2.7 Entradas y salidas
FUNCIÓN / ENDPOINT	ENTRADAS	SALIDAS
Post /Pipeline/Trigger	Cookie JWT (permiso ejecutar)	Redirect con mensaje de inicio o error
Get /Pipeline/Estado	Cookie JWT	JSON: estado, dag_run_id, tareas
Get /Pipeline/Historial	Cookie JWT	Lista de últimas 50 ejecuciones
Get /Pipeline/Logs/{Run_Id}/{Task_Id}	run_id, task_id	Texto del log + estado de la tarea
Post /Pipeline/Logs/{Run_Id}/{Task_Id}/Reintentar	run_id, task_id	Tarea reencolada en Airflow, o error
Post /Configuracion (Grupo Pipeline)	pipeline_schedule, batch_size, max_workers, reintentos	Configuración guardada en PocketBase + Variable de Airflow sincronizada
3.2.8 Escenarios
Camino feliz: trigger manual con seguimiento en tiempo real hasta finalizar con éxito; configuración de horario aplicada y reflejada en el panel; consulta de historial y logs de cualquier ejecución; reintento exitoso de una tarea fallida sin reiniciar el pipeline completo.
Manejo de errores: error de conexión con Airflow al consultar estado; expresión cron inválida al configurar el horario (rechazada antes de guardar); fallo al sincronizar el horario con Airflow (PocketBase actualizado, error mostrado al usuario); ausencia de registros en la fuente de staging al extraer; archivo fuente no disponible en MinIO al transformar.
3.2.9 Criterios de aceptación
•	Dado un Administrador con permiso de ejecución, cuando dispara el pipeline manualmente, entonces el estado cambia a "en ejecución" y la acción queda auditada.
•	Dado un horario configurado como "Diario", cuando transcurre el ciclo de refresco del scheduler, entonces el pipeline se ejecuta automáticamente sin intervención manual.
•	Dado una tarea en estado "failed", cuando el Administrador hace clic en reintentar, entonces solo esa tarea se reencola, sin reiniciar las demás.
•	Dado un valor de cron inválido, cuando el Administrador intenta guardarlo, entonces el sistema rechaza el cambio antes de tocar PocketBase o Airflow.
3.2.10 Dependencias
Seguridad (autorización de ejecución manual). Es la fuente del Módulo Modelo Dimensional.
3.2.11 Casos de uso relacionados
CU-T06 · CU-O05 · CU-O06 · CU-O07 · CU-O08
3.2.12 Fuera de alcance
Notificaciones push o por chat (solo correo); edición o cancelación de una ejecución ya en curso; versionado histórico de los archivos Parquet intermedios; reintento automático sin intervención del Administrador (los reintentos automáticos de Airflow son internos por tarea, no sustituyen al reintento manual desde la UI).

3.3 Módulo: Modelo Dimensional
Paquete técnico: app/modelo_dimensional/ | Entrega: Entrega 1
3.3.1 Objetivo
Exponer y mantener la integridad del modelo estrella de Kimball que sustenta todos los módulos analíticos.
3.3.2 Actores
Administrador.
3.3.3 Contexto del problema
Las transformaciones del pipeline pueden introducir inconsistencias (referencias rotas entre hechos y dimensiones, dimensiones faltantes) que, sin un mecanismo de validación, pasarían desapercibidas hasta manifestarse como cifras incorrectas en los reportes entregados a las aerolíneas clientes — el peor lugar posible para descubrir un error de datos en un producto B2B de inteligencia de negocio.
3.3.4 Requisitos funcionales
Funcionalidad 1: Ver resumen del modelo dimensional (CU-O09)
•	RF-MOD-001: El sistema debe mostrar las 12 tablas del modelo con su número de filas, tamaño en MB y fecha de última modificación.
Funcionalidad 2: Explorar y gestionar registros del modelo (CU-O10)
•	RF-MOD-002: El sistema debe permitir explorar cualquiera de las 12 tablas con paginación de 50 registros por página.
•	RF-MOD-003: El sistema debe permitir búsqueda textual sobre todas las columnas de la tabla seleccionada.
•	RF-MOD-004: El sistema debe permitir crear, editar y eliminar registros, con casting automático de tipos según la columna.
Funcionalidad 3: Validar integridad del modelo dimensional (CU-O11)
•	RF-MOD-005: El sistema debe validar las 12 claves foráneas de fact_vuelo contra sus dimensiones correspondientes.
•	RF-MOD-006: El sistema debe clasificar cada error de validación en uno de cuatro tipos: FK nula obligatoria, FK huérfana, tabla faltante, o fila sentinel (pk=0) faltante en una dimensión opcional.
•	RF-MOD-007: El sistema debe permitir exportar el resultado de la validación a un archivo CSV.
3.3.5 Requisitos no funcionales
•	RNF-MOD-001: Toda lectura y escritura del modelo se realiza sobre archivos Parquet en MinIO, sin updates parciales (se reescribe el archivo completo).
•	RNF-MOD-002: Toda creación, edición, eliminación y validación debe registrarse en el log de auditoría inmutable.
3.3.6 Reglas de negocio
•	RN-MOD-001: El registro con pk=0 en las dimensiones opcionales (dim_cancelacion, dim_retraso_causa, dim_desvio) es inmutable y no puede eliminarse.
•	RN-MOD-002: El PK de un registro nuevo se autogenera como el máximo PK existente más uno.
•	RN-MOD-003: Si una tabla solicitada no existe en el catálogo de tablas del modelo, el sistema responde con error 404.
•	RN-MOD-004: Si el archivo Parquet de una tabla aún no existe en MinIO, el sistema lo indica como "no disponible aún" en vez de fallar de forma genérica.
3.3.7 Entradas y salidas
Función / Endpoint	Entradas	Salidas
GET /modelo	Cookie JWT	Resumen de las 12 tablas con métricas
GET /modelo/{tabla}	tabla, page, q (búsqueda)	Listado paginado con resultados de búsqueda
POST /modelo/{tabla}/nuevo	Columnas de la tabla (Form)	Registro creado o error
POST /modelo/{tabla}/{pk}/editar	Columnas modificadas	Registro actualizado o error
POST /modelo/{tabla}/{pk}/eliminar	pk	Registro eliminado, o rechazo si pk=0
POST /modelo/validar	Cookie JWT (permiso ejecutar)	Resultado de validación con errores detallados
GET /modelo/validar/export	Cookie JWT (permiso exportar)	Archivo CSV de errores
3.3.8 Escenarios
Camino feliz: consulta del resumen del modelo con métricas actualizadas; exploración y búsqueda dentro de cualquier tabla; creación, edición y eliminación de registros en dimensiones; validación de integridad completa con exportación de errores a CSV.
Manejo de errores: tabla inexistente en el catálogo (404); archivo Parquet no disponible aún en MinIO (404 con mensaje descriptivo); registro no encontrado por PK; intento de eliminar el registro sentinel pk=0 (rechazado); fact_vuelo no disponible al ejecutar la validación; dimensión faltante durante la validación (se reporta el error y continúa validando las demás).
3.3.9 Criterios de aceptación
•	Dado el modelo recién actualizado por el pipeline, cuando el Administrador consulta el resumen, entonces ve el número de filas y tamaño actualizados de las 12 tablas.
•	Dado un registro con pk=0 en una dimensión opcional, cuando el Administrador intenta eliminarlo, entonces el sistema rechaza la operación.
•	Dado un error de FK huérfana en fact_vuelo, cuando se ejecuta la validación, entonces el sistema lo reporta clasificado correctamente y permite exportarlo a CSV.
3.3.10 Dependencias
Pipeline ELT (consume su salida en MinIO/Parquet). Seguridad.
3.3.11 Casos de uso relacionados
CU-O09 · CU-O10 · CU-O11
3.3.12 Fuera de alcance
Edición masiva o por lote de registros (solo registro por registro); versionado o historial de cambios sobre el modelo (la auditoría registra la acción, no el valor anterior); reconstrucción automática del modelo ante errores de integridad (la validación detecta, no corrige).

3.4 Módulo: Dashboard
PAQUETE TÉCNICO	APP/DASHBOARD/
ENTREGA	Entrega 2

3.4.1 Objetivo
Presentar una vista consolidada de los indicadores clave de desempeño (KPIs) con alertas automáticas por cruce de umbral.
3.4.2 Actores
Analista de Datos.
3.4.3 Requisitos funcionales
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.4.4 Requisitos no funcionales
[Pendiente] Se derivarán de la constitución del proyecto (v2.1.0) aplicada a este módulo.
3.4.5 Reglas de negocio
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.4.6 Entradas y salidas
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.4.7 Escenarios
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.4.8 Criterios de aceptación
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.4.9 Dependencias
Modelo Dimensional, Seguridad, Configuración (umbrales de alerta).
3.4.10 Casos de uso relacionados
CU-E01 · CU-E02
3.4.11 Fuera de alcance
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
 3.5 Módulo: Puntualidad
PAQUETE TÉCNICO	APP/PUNTUALIDAD/
Entrega	Entrega 2

3.5.1 Objetivo
Analizar el índice de puntualidad operacional (OTP) por aerolínea, ruta y período, incluyendo comparación entre operadores.
3.5.2 Actores
Analista de Datos.
3.5.3 Requisitos funcionales
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.5.4 Requisitos no funcionales
[Pendiente] Se derivarán de la constitución del proyecto (v2.1.0) aplicada a este módulo.
3.5.5 Reglas de negocio
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.5.6 Entradas y salidas
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.5.7 Escenarios
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.5.8 Criterios de aceptación
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.5.9 Dependencias
Modelo Dimensional, Seguridad.
3.5.10 Casos de uso relacionados
CU-E03 · CU-E04 · CU-E05
3.5.11 Fuera de alcance
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
 3.6 Módulo: Rutas
PAQUETE TÉCNICO	APP/RUTAS/
Entrega	Entrega 2

3.6.1 Objetivo
Evaluar el rendimiento operacional de rutas específicas, comparando tiempos reales contra programados.
3.6.2 Actores
Analista de Datos.
3.6.3 Requisitos funcionales
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.6.4 Requisitos no funcionales
[Pendiente] Se derivarán de la constitución del proyecto (v2.1.0) aplicada a este módulo.
3.6.5 Reglas de negocio
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.6.6 Entradas y salidas
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.6.7 Escenarios
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.6.8 Criterios de aceptación
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.6.9 Dependencias
Modelo Dimensional, Seguridad.
3.6.10 Casos de uso relacionados
CU-E06 · CU-E07
3.6.11 Fuera de alcance
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
 3.7 Módulo: Cancelaciones
PAQUETE TÉCNICO	APP/CANCELACIONES/
Entrega	Entrega 2

3.7.1 Objetivo
Analizar cancelaciones y desvíos de vuelo clasificados por causa oficial FAA.
3.7.2 Actores
Analista de Datos.
3.7.3 Requisitos funcionales
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.7.4 Requisitos no funcionales
[Pendiente] Se derivarán de la constitución del proyecto (v2.1.0) aplicada a este módulo.
3.7.5 Reglas de negocio
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.7.6 Entradas y salidas
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.7.7 Escenarios
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.7.8 Criterios de aceptación
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.7.9 Dependencias
Modelo Dimensional, Seguridad.
3.7.10 Casos de uso relacionados
CU-E08 · CU-E09 · CU-E10
3.7.11 Fuera de alcance
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
 3.8 Módulo: Reportes
PAQUETE TÉCNICO	APP/REPORTES/ (TRANSVERSAL)
Entrega	Entrega 2

3.8.1 Objetivo
Generar y exportar informes ejecutivos en PDF, Excel y CSV a partir de cualquier módulo analítico.
3.8.2 Actores
Analista de Datos.
3.8.3 Requisitos funcionales
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.8.4 Requisitos no funcionales
[Pendiente] Se derivarán de la constitución del proyecto (v2.1.0) aplicada a este módulo.
3.8.5 Reglas de negocio
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.8.6 Entradas y salidas
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.8.7 Escenarios
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.8.8 Criterios de aceptación
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.8.9 Dependencias
Dashboard, Puntualidad, Rutas, Cancelaciones, Predictivo (provee el dato a exportar).
3.8.10 Casos de uso relacionados
CU-E11 · CU-E12 · CU-E13
3.8.11 Fuera de alcance
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
 3.9 Módulo: Configuración
PAQUETE TÉCNICO	APP/CONFIGURACION/
Entrega	Entrega 2

3.9.1 Objetivo
Administrar los parámetros operativos del sistema (alertas, correo, pipeline, monitoreo, IA) sin necesidad de reiniciar servicios.
3.9.2 Actores
Administrador.
3.9.3 Requisitos funcionales
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.9.4 Requisitos no funcionales
[Pendiente] Se derivarán de la constitución del proyecto (v2.1.0) aplicada a este módulo.
3.9.5 Reglas de negocio
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.9.6 Entradas y salidas
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.9.7 Escenarios
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.9.8 Criterios de aceptación
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.9.9 Dependencias
Seguridad. Sus parámetros son consumidos por Pipeline ELT, Dashboard y Asistente IA.
3.9.10 Casos de uso relacionados
CU-T03 · CU-T04 · CU-T05 · CU-T07 · CU-T08
3.9.11 Fuera de alcance
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
 3.10 Módulo: Auditoría
PAQUETE TÉCNICO	APP/AUDITORIA/
Entrega	Entrega 2

3.10.1 Objetivo
Registrar de forma inmutable las acciones administrativas relevantes del sistema y exponerlas para consulta y exportación filtrada.
3.10.2 Actores
Administrador.
3.10.3 Requisitos funcionales
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.10.4 Requisitos no funcionales
[Pendiente] Se derivarán de la constitución del proyecto (v2.1.0) aplicada a este módulo.
3.10.5 Reglas de negocio
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.10.6 Entradas y salidas
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.10.7 Escenarios
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.10.8 Criterios de aceptación
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.10.9 Dependencias
Seguridad. Recibe eventos de todos los módulos administrativos.
3.10.10 Casos de uso relacionados
CU-O12 · CU-O13
3.10.11 Fuera de alcance
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
 3.11 Módulo: Predictivo
PAQUETE TÉCNICO	APP/PREDICTIVO/
Entrega	Entrega 3

3.11.1 Objetivo
Proyectar el comportamiento futuro de puntualidad y cancelaciones mediante series de tiempo, detectar anomalías históricas, calcular un índice de riesgo por aerolínea y simular escenarios operacionales “qué pasaría si”.
3.11.2 Actores
Analista de Datos.
3.11.3 Requisitos funcionales
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.11.4 Requisitos no funcionales
[Pendiente] Se derivarán de la constitución del proyecto (v2.1.0) aplicada a este módulo.
3.11.5 Reglas de negocio
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.11.6 Entradas y salidas
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.11.7 Escenarios
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.11.8 Criterios de aceptación
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.11.9 Dependencias
Modelo Dimensional, Seguridad, Reportes (informe ejecutivo).
3.11.10 Casos de uso relacionados
CU-E14 · CU-E15 · CU-E16 · CU-E17 · CU-E20 · CU-E21 · CU-E22
3.11.11 Fuera de alcance
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
 3.12 Módulo: Asistente IA
PAQUETE TÉCNICO	APP/ASISTENTE_IA/ + APP/UTILS/IA_NARRATIVA.PY
Entrega	Entrega 3

3.12.1 Objetivo
Generar narrativas ejecutivas automáticas por gráfico o KPI y responder consultas en lenguaje natural sobre los datos del sistema mediante generación aumentada por recuperación (RAG).
3.12.2 Actores
Analista de Datos (consulta); Administrador (configuración del proveedor de IA).
3.12.3 Requisitos funcionales
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.12.4 Requisitos no funcionales
[Pendiente] Se derivarán de la constitución del proyecto (v2.1.0) aplicada a este módulo.
3.12.5 Reglas de negocio
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.12.6 Entradas y salidas
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.12.7 Escenarios
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.12.8 Criterios de aceptación
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.12.9 Dependencias
Modelo Dimensional (contexto RAG), Configuración (parámetros del proveedor), Seguridad.
3.12.10 Casos de uso relacionados
CU-E18 · CU-T09 · CU-O14
3.12.11 Fuera de alcance
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
 3.13 Módulo: Clientes (Entrega 4)
PAQUETE TÉCNICO	PLANIFICADO — APP/CLIENTES/
Entrega	Entrega 4 (planificada)

3.13.1 Objetivo
Administrar la cartera de clientes aerolínea de AeroTrack y la entrega automática de reportes por suscripción.
3.13.2 Actores
Administrador.
3.13.3 Requisitos funcionales
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.13.4 Requisitos no funcionales
[Pendiente] Se derivarán de la constitución del proyecto (v2.1.0) aplicada a este módulo.
3.13.5 Reglas de negocio
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.13.6 Entradas y salidas
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.13.7 Escenarios
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.13.8 Criterios de aceptación
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.13.9 Dependencias
Seguridad, Reportes.
3.13.10 Casos de uso relacionados
CU-E19 · CU-T10 · CU-T11 · CU-O15 · CU-O16
3.13.11 Fuera de alcance
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
 3.14 Módulo: Socios API (Entrega 4)
PAQUETE TÉCNICO	PLANIFICADO — APP/SOCIOS_API/
Entrega	Entrega 4 (planificada)

3.14.1 Objetivo
Exponer los resultados analíticos de AeroTrack como servicio de programación documentado y seguro para socios tecnológicos externos.
3.14.2 Actores
Administrador (gestión de claves y webhooks); Socio tecnológico (consumo programático).
3.14.3 Requisitos funcionales
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.14.4 Requisitos no funcionales
[Pendiente] Se derivarán de la constitución del proyecto (v2.1.0) aplicada a este módulo.
3.14.5 Reglas de negocio
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.14.6 Entradas y salidas
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.14.7 Escenarios
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.14.8 Criterios de aceptación
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
3.14.9 Dependencias
Seguridad, Modelo Dimensional.
3.14.10 Casos de uso relacionados
CU-T12 · CU-T13 · CU-O17 · CU-O18
3.14.11 Fuera de alcance
[Pendiente] Se completará en una siguiente entrega con speckit-specify, a partir de esta plantilla.
 4. Trazabilidad: Módulo → Casos de Uso
La siguiente tabla confirma la cobertura completa del catálogo de 53 casos de uso de la Documentación Empresarial v3 a través de los 14 módulos del sistema, sin solapamientos.
MÓDULO	ENTREGA	CASOS DE USO CUBIERTOS	Nº CU
Seguridad	Entrega 1	CU-T01, CU-T02, CU-O01, CU-O02, CU-O03, CU-O04	6
Pipeline Elt	Entrega 1	CU-T06, CU-O05, CU-O06, CU-O07, CU-O08	5
Modelo Dimensional	Entrega 1	CU-O09, CU-O10, CU-O11	3
Dashboard	Entrega 2	CU-E01, CU-E02	2
Puntualidad	Entrega 2	CU-E03, CU-E04, CU-E05	3
Rutas	Entrega 2	CU-E06, CU-E07	2
Cancelaciones	Entrega 2	CU-E08, CU-E09, CU-E10	3
Reportes	Entrega 2	CU-E11, CU-E12, CU-E13	3
Configuración	Entrega 2	CU-T03, CU-T04, CU-T05, CU-T07, CU-T08	5
Auditoría	Entrega 2	CU-O12, CU-O13	2
Predictivo	Entrega 3	CU-E14, CU-E15, CU-E16, CU-E17, CU-E20, CU-E21, CU-E22	7
Asistente Ia	Entrega 3	CU-E18, CU-T09, CU-O14	3
Clientes (Entrega 4)	Entrega 4 (planificada)	CU-E19, CU-T10, CU-T11, CU-O15, CU-O16	5
Socios Api (Entrega 4)	Entrega 4 (planificada)	CU-T12, CU-T13, CU-O17, CU-O18	4
Total			53
Tabla 4. Trazabilidad entre módulos y casos de uso (cobertura total: 53).
 5. Anexos
5.1 Glosario
TÉRMINO	DEFINICIÓN
Otp	On-Time Performance: índice de puntualidad operacional de un vuelo o aerolínea.
Elt	Extract-Load-Transform: la transformación ocurre después de cargar los datos crudos, a diferencia de ETL.
Rbac	Role-Based Access Control: control de acceso basado en roles.
Kimball / Modelo Estrella	Patrón de modelado dimensional con una tabla de hechos central y dimensiones desnormalizadas.
Rag	Retrieval-Augmented Generation: generación de texto por IA fundamentada en datos recuperados del sistema.
Cu	Caso de uso.
Oe / Ot / Oo	Objetivo Estratégico / Táctico / Operativo (jerarquía del Cuadro de Mando Integral).
Tabla 5. Glosario de términos.
5.2 Resumen de la constitución del proyecto (v2.1.0)
La constitución completa vive en «.specify/memory/constitution.md». Resumen de sus 18 principios agrupados por área: (A) Arquitectura de Datos — separación de capas, modelo dimensional Kimball; (B) Seguridad y Configuración — RBAC, secretos no hardcodeados, auditoría inmutable; (C) Resiliencia y Rendimiento — degradación de servicios, caché con TTL, paginación, timeouts del pipeline; (D) Inteligencia Artificial Responsable — contexto limitado a KPIs, asistente IA con verificación de permiso; (E) Frontend y Sistema de Diseño — design tokens, Vanilla JS, versión única de librerías de gráficos, serialización segura, gestión de dependencias externas; (F) Stack Tecnológico — Python 3.12 unificado; (G) Conformidad con Normas de Calidad — adherencia a ISO/IEC 25010:2023.
