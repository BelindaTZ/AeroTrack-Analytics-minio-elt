# AeroTrack_Documentacion_Empresarial_v3.pdf


AEROTRACK ANALYTICS: SISTEMA DE BUSINESS INTELLIGENCE AERONÁUTICO
Documentación Empresarial y del Sistema
Belinda Toaquiza1

1 Facultad de Ciencias de la Computación, 
Universidad Técnica Estatal de Quevedo, Ecuador

1 Ingeniería en software, Sexto semestre, Paralelo B

1{btoaquizaz@uteq.edu.ec}

Repositorio del sistema en GitHub 

Asignatura: Construcción De Software
Fecha de entrega: 21/06/2026




Resumen: AeroTrack Analytics es un sistema de inteligencia de negocios aeronáutico desarrollado bajo un modelo de negocio empresa a empresa (B2B), cuya misión es transformar los datos operacionales de vuelo del Bureau of Transportation Statistics (BTS) y la Administración Federal de Aviación (FAA) en inteligencia estratégica para aerolíneas, operadores aeroportuarios e instituciones financieras del sector. El sistema procesa dos millones de registros de vuelo de treinta y tres aerolíneas mediante un proceso automatizado de extracción, transformación y carga, que genera un modelo dimensional estrella de Kimball con una tabla de hechos y once dimensiones, complementado por siete tablas de indicadores precalculados almacenados en formato columnar. La plataforma web expone los resultados a través de módulos de análisis de puntualidad, evaluación de rutas, análisis de cancelaciones, generación de reportes ejecutivos y módulos de inteligencia artificial predictiva y conversacional. El presente documento abarca el análisis empresarial completo del sistema: el modelo de negocio B2B, los cuatro objetivos estratégicos y su despliegue en el Cuadro de Mando Integral, el mapa jerárquico de objetivos en tres niveles organizacionales, el catálogo de cincuenta casos de uso clasificados por nivel, la visión arquitectónica del sistema, las técnicas de inteligencia artificial aplicadas y la trazabilidad completa entre objetivos, funcionalidades, indicadores y casos de uso.


Palabras clave: Business Intelligence aeronáutico, modelo dimensional de Kimball, pipeline ELT, puntualidad OTP, análisis de cancelaciones FAA, Cuadro de Mando Integral, casos de uso organizacionales, inteligencia artificial predictiva, generación aumentada por recuperación, series de tiempo.



Índice

1. Introducción	5
2. Descripción de la Empresa	6
2.1 Historia y Contexto Empresarial	6
2.2 Misión	6
2.3 Visión	6
2.4 Objetivo Estratégico General	6
2.5 Propuesta de Valor	7
2.6 Modelo de Ingresos	8
3. Análisis Estratégico Organizacional	9
3.1 Niveles Organizacionales	9
3.2 Cuadro de Mando Integral — Balanced Scorecard	9
3.2.1 Cuadro resumen del Balanced Scorecard	11
3.2.2 Plan de acción estratégico	13
3.3 Mapa de Objetivos Estratégicos, Tácticos y Operativos	14
4. Descripción del Sistema AeroTrack Analytics	21
4.1 Resumen del Sistema	21
4.2 Arquitectura Tecnológica	21
4.3 Infraestructura y Despliegue	21
4.4 Flujo de Procesamiento de Datos	22
4.5 Modelo de Datos Analítico	23
4.6 Módulos principales del sistema	24
5. Descripción del Sistema y su Aporte a los Niveles Organizacionales	26
6. Casos de Uso del Sistema	40
6.1 Actores del Sistema	40
6.2 Catálogo general de casos de uso	40
A. Casos de uso estratégicos	40
B. Casos de uso tácticos	42
C. Casos de uso operativos	42
6.3 Diagrama textual de casos de uso	44
7. Visión Arquitectónica del Sistema	46
7.1 Enfoque general por nivel organizacional	46
7.2 Modelo analítico general del sistema	47
7.3 Tablas de hechos principales	48
7.4 Dimensiones principales	49
7.5 Técnicas usadas por nivel organizacional	50
A. Nivel estratégico	50
B. Nivel táctico	50
C. Nivel operativo	51
7.6 Matriz por casos de uso estratégicos	51
7.7 Matriz por casos de uso tácticos	54
7.8 Matriz por casos de uso operativos	56
7.9 Agregaciones usadas en el sistema	58
7.10 Técnicas de IA y Machine Learning aplicables	60
A. Predicción de puntualidad y cancelaciones (series de tiempo)	60
B. Detección de anomalías en indicadores clave	60
C. Narrativa analítica automatizada con modelos de lenguaje	61
D. Asistente analítico conversacional (recuperación aumentada con IA)	61
E. Scoring de riesgo compuesto y simulación de escenarios	62
7.11 Relación entre registros operativos y reportes gerenciales	62
7.12 Trazabilidad completa del sistema AeroTrack Analytics	63
7.13 Resumen final por nivel	71
8. Técnicas de Inteligencia Artificial y Aprendizaje Automático	73
8.1 Narrativa Analítica Automatizada por Gráfico e Indicador	73
8.2 Módulo de Predicción con Series de Tiempo	73
8.3 Asistente Analítico Conversacional	73
9. Calidad del Sistema	74
10. Conclusiones	74
11. Referencias Bibliográficas	74



1. Introducción
La industria del transporte aéreo comercial en los Estados Unidos genera, de forma cotidiana, una de las bases de datos operacionales más completas de cualquier sector económico. El Bureau of Transportation Statistics (BTS), dependiente del Departamento de Transporte de los Estados Unidos, publica mensualmente los registros de desempeño de todas las aerolíneas certificadas bajo la supervisión de la Administración Federal de Aviación (FAA), con más de cien variables por vuelo que documentan tiempos programados y reales, causas de retrasos por categoría oficial, cancelaciones, desvíos y distancias recorridas, entre otros atributos [1][2]. En su forma cruda, este repositorio de millones de registros resulta técnicamente inaccesible para la mayoría de las organizaciones del sector sin los medios adecuados para su procesamiento. AeroTrack Analytics surge como respuesta directa a esta brecha, operando como socio estratégico de datos para aerolíneas, operadores aeroportuarios e instituciones financieras, con el propósito de convertir ese volumen masivo de información en análisis concretos, visualizaciones interactivas y proyecciones predictivas orientadas a la toma de decisiones de alto impacto.
El sistema desarrollado procesa activamente dos millones de registros de vuelo de treinta y tres aerolíneas estadounidenses. Mediante un proceso automatizado de transformación organizado según el modelo dimensional de Kimball [3], la información cruda se estructura en un repositorio analítico que permite responder en tiempo real preguntas estratégicas como: ¿cuál aerolínea presenta el mejor desempeño en las rutas que comparte con sus competidores? ¿Cuál será el comportamiento estimado de la puntualidad en los próximos meses? La capacidad de responder estas preguntas con datos objetivos y actualizados constituye, en la aviación comercial moderna, una ventaja competitiva de alto valor [4].
La plataforma se estructura en cuatro entregas de desarrollo progresivo. La primera establece la gestión de seguridad con control de acceso por roles diferenciados, el proceso automatizado de actualización de datos y el modelo dimensional analítico. La segunda incorpora todos los módulos de análisis: indicadores clave con alertas automáticas, puntualidad por aerolínea, eficiencia de rutas, cancelaciones por categoría oficial, informes exportables y administración integral del sistema. La tercera añade un módulo de proyección basado en series de tiempo y un asistente analítico conversacional con inteligencia artificial. La cuarta completa el ecosistema comercial con gestión de clientes aerolínea, entrega automática de reportes y exposición del sistema como servicio de programación para socios tecnológicos.
El presente documento describe AeroTrack Analytics desde sus fundamentos estratégicos hasta sus capacidades funcionales y técnicas, siguiendo la estructura del análisis empresarial de sistemas de información de la asignatura de Construcción de Software. Abarca la misión, visión y modelo de negocio; el Cuadro de Mando Integral con objetivos en tres niveles organizacionales; la descripción técnica del sistema; los cuarenta y dos casos de uso clasificados por nivel; la tabla de aporte a los niveles organizacionales; y las técnicas de inteligencia artificial y aprendizaje automático incorporadas.



2. Descripción de la Empresa
2.1 Historia y Contexto Empresarial
AeroTrack Analytics es una empresa de consultoría e inteligencia de negocios especializada en el análisis operacional de la industria aérea de los Estados Unidos, con sede en Miami, Florida. La empresa opera bajo un modelo de negocio empresa-a-empresa: las aerolíneas, operadores aeroportuarios e instituciones financieras del sector son los clientes que contratan y pagan por el servicio, mientras que los analistas de datos son empleados propios de AeroTrack que utilizan la plataforma interna para producir y entregar los resultados. El cliente final no accede directamente al sistema — recibe la inteligencia que el sistema produce, materializada en informes ejecutivos, análisis comparativos y proyecciones estratégicas.
La empresa fue fundada reconociendo que el sector aéreo estadounidense enfrenta una paradoja de información: existe una abundancia sin precedentes de datos operacionales públicos, pero la capacidad para convertirlos en inteligencia accionable está concentrada en muy pocas organizaciones con equipos técnicos especializados y de alto costo. AeroTrack cierra esta brecha actuando como el socio estratégico de datos que las aerolíneas medianas y operadores regionales no pueden costear de forma interna, entregando inteligencia de calidad institucional a una fracción del costo de mantener un equipo analítico propio.
2.2 Misión
Proveer a aerolíneas, operadores aeroportuarios e instituciones del sector aerocomercial inteligencia de negocios de alto valor, derivada del análisis riguroso de los datos operacionales del Bureau of Transportation Statistics y la Administración Federal de Aviación, permitiéndoles optimizar su puntualidad, reducir el impacto económico de cancelaciones y desvíos, y fortalecer su posición competitiva frente a las aerolíneas que operan en las mismas rutas.
2.3 Visión
Ser reconocida al año 2030 como la firma de referencia en inteligencia de negocios aeronáutica para América, distinguiéndose por convertir los datos operacionales de vuelo en ventajas competitivas sostenibles para sus clientes, mediante el análisis avanzado, la predicción inteligente y la automatización de la entrega de inteligencia a cada organización del sector que confíe en AeroTrack Analytics como su socio estratégico de datos.
2.4 Objetivo Estratégico General
Consolidar AeroTrack Analytics como el socio estratégico de datos de referencia para el sector aéreo de los Estados Unidos, mediante la captura eficiente de clientes aerolínea a través de canales digitales, la entrega continua de inteligencia operacional de alto valor y la expansión del servicio a través de una plataforma tecnológica escalable y disponible globalmente.

APRENDIZAJE Y CRECIMIENTO
Desarrollar capacidades de inteligencia artificial predictiva y conversacional
Adoptar infraestructura en la nube con escalado automático según la demanda
Ampliar el ecosistema de socios tecnológicos integrados mediante interfaz de programación
Mejorar continuamente la precisión del modelo de proyección de puntualidad

↓
PROCESOS INTERNOS
Automatizar la actualización y transformación de datos operacionales de vuelo
Garantizar la disponibilidad continua del servicio en cualquier región
Optimizar el tiempo de generación y entrega de informes ejecutivos a clientes
Estandarizar el proceso de captación digital de nuevas aerolíneas cliente
↓
CLIENTES
Aumentar la captación de aerolíneas mediante demostraciones digitales sin intervención presencial
Fidelizar a los clientes suscritos mediante inteligencia predictiva de alto valor diferenciado
Ampliar el acceso al servicio mediante la exposición de la plataforma como interfaz de programación
Mejorar la satisfacción del cliente con informes ejecutivos precisos y entregados puntualmente
↓
FINANCIERA
Incrementar los ingresos por suscripciones analíticas recurrentes mensuales y trimestrales
Generar una nueva línea de ingresos por licencias de acceso programático para socios
Reducir el costo de adquisición de clientes mediante estrategias de captación 100% digitales
Aumentar la rentabilidad por cliente incorporando el módulo de inteligencia predictivo

2.5 Propuesta de Valor
AeroTrack Analytics comercializa tres productos claramente diferenciados que responden a las necesidades de información de sus clientes en distintos horizontes temporales:
Informes ejecutivos de desempeño. El director de operaciones de una aerolínea cliente recibe, de forma automática y periódica, un documento ejecutivo estructurado que le indica si su índice de puntualidad supera o no el umbral de referencia del sector, cuáles son las tres rutas con mayor incidencia de cancelaciones o retrasos en el período, y si el origen de los problemas operacionales es atribuible a la propia aerolínea o a factores externos como condiciones climáticas o el sistema nacional de tráfico aéreo. Este producto elimina semanas de trabajo analítico interno y lo reemplaza con inteligencia lista para la toma de decisiones.
Análisis comparativo entre operadores. Una aerolínea que opera la ruta Miami-Dallas necesita saber si su índice de puntualidad del setenta y ocho por ciento es bueno o malo en el contexto de sus competidores en esa misma ruta. Si sus competidores promedian ochenta y cinco por ciento, tiene un problema estratégico. Si promedian setenta y dos por ciento, está liderando el mercado. Este análisis comparativo objetivo es imposible de realizar sin acceso simultáneo a los datos de todas las aerolíneas, acceso que AeroTrack provee de manera centralizada.
Inteligencia predictiva. El cliente no solo comprende lo que ocurrió en el pasado, sino que puede planificar lo que ocurrirá en los próximos meses. Una aerolínea que sabe con anticipación que julio presenta históricamente un veintitrés por ciento más de cancelaciones en sus rutas del noreste puede preparar tripulaciones adicionales, ajustar sus políticas operacionales y renegociar disponibilidad de instalaciones aeroportuarias. Este tercer producto, disponible a partir de la tercera entrega del sistema, es el de mayor valor y diferenciación competitiva.
2.6 Modelo de Ingresos
AeroTrack Analytics opera con tres fuentes de ingreso complementarias que generan flujos de caja tanto recurrentes como puntuales:
Suscripción analítica mensual o trimestral. El cliente aerolínea paga una tarifa periódica para recibir informes de desempeño actualizados sobre su operación. Este modelo es predecible, recurrente y escalable.
Consultoría estratégica puntual. Para proyectos específicos de decisión de alto impacto, como la evaluación de la conveniencia de abrir una nueva ruta, elegir un socio para vuelos con código compartido o diagnosticar el origen de un deterioro en la puntualidad, el cliente contrata un análisis a medida que la empresa entrega en un plazo acordado.
Licencia de interfaz de programación para socios. Disponible a partir de la cuarta entrega del sistema, permite a aerolíneas con capacidades tecnológicas propias o a integradores de software del sector acceder directamente a los resultados analíticos de AeroTrack mediante programación, integrándolos en sus propios sistemas de gestión operacional.



3. Análisis Estratégico Organizacional
3.1 Niveles Organizacionales
El sistema AeroTrack Analytics cubre los tres niveles de la pirámide de decisiones organizacionales, desde las metas institucionales de largo plazo hasta la ejecución de tareas operativas cotidianas. En la Tabla 1 se describe la naturaleza de cada nivel y su correspondencia con las funcionalidades del sistema.
NIVEL DE OBJETIVO	QUÉ DEFINE	CÓMO SE REFLEJA EN AEROTRACK ANALYTICS
Estratégico	Metas generales de la organización; define qué quiere lograr AeroTrack como empresa en términos de mercado, posicionamiento y sostenibilidad a largo plazo.	Módulos de análisis ejecutivo, generación de informes para clientes, benchmarking competitivo entre aerolíneas, proyecciones predictivas y ecosistema de socios.
Táctico	Necesidades de las áreas funcionales de la empresa: qué analizar, cómo medir, con qué periodicidad y mediante qué herramientas.	Configuración de parámetros operativos, gestión de usuarios y roles, administración de clientes y socios, configuración del proveedor de inteligencia artificial.
Operativo	Acciones diarias de los analistas y administradores del sistema: consultas específicas, exportaciones, actualizaciones y registro de actividad.	Ejecución del proceso de actualización de datos, consulta de módulos analíticos, exportación de reportes, monitoreo de servicios y registro de auditoría.
Tabla 1. Niveles organizacionales y su reflejo en el sistema AeroTrack Analytics.
3.2 Cuadro de Mando Integral — Balanced Scorecard
El Cuadro de Mando Integral (Balanced Scorecard) de AeroTrack Analytics organiza los objetivos estratégicos de la empresa en cuatro perspectivas interdependientes, definiendo para cada uno los indicadores de medición, las fórmulas de cálculo, las metas cuantificables y las iniciativas estratégicas que el sistema informático apoya. La Tabla 2 presenta el cuadro completo.
OBJETIVO ESTRATÉGICO	INDICADOR	FÓRMULA DE CÁLCULO	META	INICIATIVA ESTRATÉGICA
A. Perspectiva Financiera
Oe-1: Penetración Digital Y Adquisición De Clientes Aeronáuticos	Costo de Adquisición de Cliente (CAC)	Gasto total de captación en el período / Número de nuevos contratos firmados	USD 2.000 por nuevo cliente	Entrega automática de reportes de demostración a prospectos seleccionados
Oe-2: Escalabilidad Por Apis Y Ecosistema De Socios	Porcentaje de ingresos generados por licencias de API	Ingresos por licencias API / Ingresos totales del período × 100	30% al tercer año de operación	Desarrollo del módulo de gestión de socios con claves de acceso diferenciadas
Oe-1: Penetración Digital Y Adquisición De Clientes Aeronáuticos	Tiempo del ciclo de venta digital	Días transcurridos desde el envío del acceso de demostración hasta la firma del contrato	30 días en promedio	Sistema de acceso temporal al panel de análisis para prospectos sin necesidad de cuenta
B. Perspectiva Del Cliente
Oe-4: Inteligencia De Negocio Centralizada Para Ventaja Competitiva	Tasa de retención de clientes aerolínea	Contratos renovados en el período / Total de contratos vigentes × 100	85% de retención anual	Módulo predictivo que anticipa necesidades del cliente y genera valor diferenciado por período
Oe-1: Penetración Digital Y Adquisición De Clientes Aeronáuticos	Tasa de conversión de demostración a contrato	Contratos firmados tras demostración / Total de demostraciones enviadas × 100	25% de conversión	Personalización del reporte de demostración con datos reales de la aerolínea prospecto
Oe-4: Inteligencia De Negocio Centralizada Para Ventaja Competitiva	Tiempo de respuesta para obtención de insight	Segundos desde la solicitud del analista hasta la visualización del resultado en pantalla	3 segundos para cualquier módulo	Tablas de indicadores precalculadas actualizadas tras cada ciclo de actualización de datos
C. Perspectiva De Procesos Internos
Oe-4: Inteligencia De Negocio Centralizada Para Ventaja Competitiva	Tasa de éxito del proceso de actualización de datos	Ejecuciones completadas sin error / Total de ejecuciones iniciadas × 100	99% de ejecuciones exitosas	Reintentos automáticos configurables y notificaciones por correo ante fallo de cualquier etapa
Oe-3: Infraestructura En La Nube De Alta Disponibilidad	Disponibilidad global del servicio (Uptime)	Tiempo con servicio disponible / Tiempo total del período × 100	99,9% mensual	Monitoreo automático de todos los componentes del sistema con refresco cada 30 segundos
Oe-2: Escalabilidad Por Apis Y Ecosistema De Socios	Disponibilidad de los puntos de acceso de la API	Tiempo de API activa / Tiempo total del período × 100	99,5% mensual	Puntos de acceso versionados con autenticación por clave y manejo estructurado de errores
Oe-4: Inteligencia De Negocio Centralizada Para Ventaja Competitiva	Duración del ciclo de actualización de datos	Minutos desde el inicio de la extracción hasta que los datos están disponibles en el panel	30 minutos por ejecución completa	Procesamiento paralelo de la extracción de datos con número de procesos configurables
D. Perspectiva De Aprendizaje Y Crecimiento
Oe-3: Infraestructura En La Nube De Alta Disponibilidad	Grado de adopción de infraestructura en nube	Porcentaje de servicios desplegados en nube pública / Total de servicios del sistema × 100	100% al segundo año de operación comercial	Migración progresiva de la arquitectura de contenedores local hacia proveedor de nube pública
Oe-4: Inteligencia De Negocio Centralizada Para Ventaja Competitiva	Precisión del modelo de predicción	Error Absoluto Medio (MAE) del modelo de series de tiempo en proyecciones de puntualidad	MAE menor a 5 puntos porcentuales a 3 meses	Reentrenamiento mensual del modelo incorporando datos del período más reciente disponible
Oe-2: Escalabilidad Por Apis Y Ecosistema De Socios	Crecimiento del ecosistema de socios tecnológicos	Número de integraciones de interfaz de programación activas con socios externos por trimestre	5 socios activos al segundo año	Publicación de documentación técnica pública y establecimiento de programa formal de socios
Tabla 2. Cuadro de Mando Integral de AeroTrack Analytics organizado por perspectiva.

3.2.1 Cuadro resumen del Balanced Scorecard
La siguiente tabla consolida de forma ejecutiva los objetivos principales de AeroTrack Analytics por perspectiva del Cuadro de Mando Integral, acompañados del indicador clave de medición y la meta estratégica que el sistema debe contribuir a alcanzar en cada dimensión organizacional.

PERSPECTIVA	OBJETIVO PRINCIPAL	INDICADOR CLAVE	META ESTRATÉGICA
Financiera	Incrementar ingresos por suscripciones analíticas	Ingresos recurrentes mensuales (MRR)	Crecimiento del 20% anual
Financiera	Reducir el costo de adquisición de clientes digitalmente	Costo de Adquisición de Cliente (CAC)	≤ USD 2.000 por cliente
Financiera	Generar ingresos por licencias de API para socios	% ingresos por API / ingresos totales	≥ 30% al tercer año
Cliente	Fidelizar a las aerolíneas cliente por valor entregado	Tasa de retención de contratos	≥ 85% anual
Cliente	Convertir prospectos en clientes mediante demos digitales	Tasa de conversión demo-contrato	≥ 25%
Cliente	Satisfacer necesidades analíticas con rapidez	Tiempo de respuesta para obtención de insight	≤ 3 segundos
Procesos Internos	Garantizar la disponibilidad continua del servicio	Uptime global del sistema	≥ 99,9% mensual
Procesos Internos	Automatizar y mantener actualizado el modelo de datos	Tasa de éxito del proceso de actualización	≥ 99% de ejecuciones
Procesos Internos	Exponer capacidades como servicio de API disponible	Disponibilidad de la interfaz de programación	≥ 99,5% mensual
Aprendizaje Y Crecimiento	Adoptar infraestructura en la nube escalable	% servicios desplegados en nube pública	100% al segundo año
Aprendizaje Y Crecimiento	Mejorar la precisión del modelo predictivo	Error Absoluto Medio (MAE) del modelo Prophet	≤ 5 puntos porcentuales
Aprendizaje Y Crecimiento	Ampliar el ecosistema de socios tecnológicos	Número de integraciones de API activas	≥ 5 socios al segundo año
Tabla 3. Cuadro resumen del Balanced Scorecard — AeroTrack Analytics


3.2.2 Plan de acción estratégico
El plan de acción estratégico traduce los objetivos del Cuadro de Mando Integral en iniciativas concretas con plazo definido, responsable asignado y resultado esperado. Cada acción corresponde directamente a una capacidad del sistema AeroTrack Analytics y constituye la hoja de ruta que permite materializar la estrategia de la empresa en tareas específicas y medibles.
ACCIÓN	PLAZO	RESPONSABLE	RECURSO NECESARIO	RESULTADO ESPERADO
Implementar Módulo De Entrega Automática De Reportes A Clientes Suscritos	2 meses	Administrador	Sistema de correo electrónico configurado + proceso de datos activo	Clientes reciben inteligencia periódica sin intervención manual
Publicar Interfaz De Programación Documentada Para Socios Tecnológicos	3 meses	Administrador	Gestión de claves de acceso + documentación técnica pública	Nueva línea de ingresos por licencias de API
Habilitar Sistema De Acceso Temporal Al Panel Para Prospectos Aerolínea	1 mes	Administrador	Módulo de gestión de clientes + enlace de demostración	Reducción del ciclo de venta digital
Migrar La Infraestructura De Contenedores Docker A Proveedor Cloud	6 meses	Administrador	Proveedor cloud (AWS/Azure) + configuración de Kubernetes	Disponibilidad global ≥ 99,9% para clientes en múltiples regiones
Activar Módulo De Predicción Con Series De Tiempo (Prophet)	2 meses	Analista de Datos	Datos históricos de al menos 12 meses procesados en el modelo	Clientes disponen de proyecciones de puntualidad a 3–6 meses
Reentrenar El Modelo Predictivo Mensualmente Con Datos Recientes	Permanente	Analista de Datos	Ejecución mensual del proceso de datos + reentrenamiento automático	Precisión del modelo MAE ≤ 5 puntos porcentuales
Registrar Y Gestionar Catálogo De Clientes Aerolínea Activos	1 mes	Administrador	Módulo de gestión de clientes	Control centralizado de contratos y suscripciones activas
Medir Satisfacción Del Cliente Con Los Informes Entregados	Trimestral	Administrador	Encuesta de evaluación post-entrega	Indicador de satisfacción para ajustar el contenido de los reportes
Tabla 4. Plan de acción estratégico — AeroTrack Analytics
3.3 Mapa de Objetivos Estratégicos, Tácticos y Operativos
La Tabla 5 presenta la jerarquía completa de objetivos de AeroTrack Analytics siguiendo el principio de que cada objetivo estratégico contiene uno o más objetivos tácticos, cada objetivo táctico agrupa uno o más objetivos operativos, y cada objetivo operativo tiene asociada una meta concreta y verificable que el sistema permite alcanzar.
OBJETIVO ESTRATÉGICO (OE)	OBJETIVO TÁCTICO (OT)	OBJETIVO OPERATIVO (OO)	META
Oe-1: Penetración Digital Y Adquisición Automatizada De Clientes Aeronáuticos	OT-1.1: Captar aerolíneas y operadores mediante demostraciones y reportes digitales.	OO-1.1.1: Registrar y gestionar los clientes aerolínea activos y prospectos del sistema.	El administrador dispone de un catálogo centralizado de clientes con estado de contrato y datos de contacto para la gestión comercial.
		OO-1.1.2: Generar un enlace de acceso temporal al panel de análisis para un prospecto aerolínea.	El prospecto accede al sistema con datos reales durante 48 horas sin necesidad de cuenta, lo que acelera el proceso de decisión comercial.
	OT-1.2: Automatizar la configuración y seguimiento de entregas periódicas a los clientes suscritos.	OO-1.2.1: Configurar suscripciones de entrega automática de reportes por cliente.	El administrador define qué tipo de reporte recibe cada cliente, con qué frecuencia y con qué filtros, sin intervención adicional.
		OO-1.2.2: Consultar el historial de entregas automáticas de reportes realizadas por cliente.	El administrador verifica qué reportes fueron enviados, cuándo y con qué resultado, para asegurar la continuidad del servicio.
	OT-1.3: Generar y poner a disposición informes ejecutivos en múltiples formatos de salida.	OO-1.3.1: Exportar análisis a PDF con narrativa ejecutiva integrada.	El cliente recibe un informe ejecutivo listo para presentación, con secciones configurables, gráficos y narrativa generada por IA.
		OO-1.3.2: Exportar análisis a Excel con hojas por módulo analítico.	El cliente recibe un archivo editable con múltiples hojas, gráficos nativos y formato condicional en los indicadores.
		OO-1.3.3: Exportar datos filtrados a CSV.	El cliente obtiene los registros crudos del período seleccionado para análisis externo propio.
	OT-1.4: Medir y evaluar la efectividad de la estrategia de captación digital.	OO-1.4.1: Ver el panel de captación con métricas de demos, conversión y clientes activos.	La dirección de AeroTrack evalúa la efectividad de las acciones de captación digital y ajusta la estrategia comercial según los resultados observados.
Oe-2: Escalabilidad Comercial Por Plataformas De Ecosistemas Y Apis	OT-2.1: Exponer la inteligencia analítica como servicio de programación documentado y seguro.	OO-2.1.1: Gestionar claves de acceso programático para socios tecnológicos (generar, revocar, limitar).	El administrador controla qué socios tienen acceso a la interfaz de programación, con qué permisos y límite de consultas.
		OO-2.1.2: Acceder a los indicadores analíticos mediante clave programática.	El sistema socio consume los indicadores analíticos de AeroTrack directamente en sus propias plataformas, sin intervención manual.
	OT-2.2: Notificar de forma proactiva al ecosistema de socios sobre la disponibilidad de datos nuevos.	OO-2.2.1: Configurar notificaciones automáticas (webhooks) a socios cuando se disponen datos nuevos.	Los sistemas socios reciben una señal automática al completarse el ciclo de actualización, eliminando consultas periódicas de verificación.
	OT-2.3: Supervisar el consumo del servicio de programación por parte de los socios.	OO-2.3.1: Ver el panel de uso y métricas de la interfaz de programación por socio.	El administrador monitorea el consumo por socio, detecta usos inusuales y fundamenta decisiones de precios y capacidad.
Oe-3: Expansión Continua Sobre Infraestructura En La Nube De Alta Disponibilidad	OT-3.1: Gestionar identidades y el control de acceso seguro al sistema.	OO-3.1.1: Gestionar usuarios del sistema con credenciales generadas automáticamente.	El administrador crea, edita y desactiva usuarios sin ver nunca la contraseña temporal generada por el sistema.
		OO-3.1.2: Administrar roles y matrices de permisos por módulo y tipo de acción.	El administrador define con precisión qué acciones puede ejecutar cada rol en cada módulo del sistema.
		OO-3.1.3: Iniciar y cerrar sesión, y consultar o editar el perfil propio.	Cada usuario accede al sistema según su rol asignado y mantiene actualizados sus datos personales.
		OO-3.1.4: Ver la matriz de permisos vigente del sistema.	El administrador verifica de forma centralizada los permisos activos por rol y módulo para auditoría rápida.
	OT-3.2: Automatizar y supervisar el ciclo de actualización del modelo analítico.	OO-3.2.1: Configurar y programar la ejecución automática del proceso de actualización de datos.	El administrador define la frecuencia y horario de actualización desde el panel de configuración, sin intervención técnica.
		OO-3.2.2: Ejecutar el proceso de actualización de datos de forma manual desde la interfaz web.	El administrador inicia el ciclo completo de actualización bajo demanda, sin herramientas técnicas especializadas.
		OO-3.2.3: Monitorear el estado del proceso (DAG) en ejecución.	El administrador supervisa el avance de cada etapa del proceso de actualización en tiempo real.
		OO-3.2.4: Consultar el historial de ejecuciones del proceso de datos.	El administrador verifica la completitud de cada actualización pasada y su duración.
		OO-3.2.5: Ver los logs de error y reintentar ejecuciones fallidas.	El administrador diagnostica la causa exacta de cualquier fallo y corrige la etapa afectada sin reiniciar todo el proceso.
	OT-3.3: Garantizar la continuidad operativa mediante monitoreo proactivo de la infraestructura.	OO-3.3.1: Ver el panel de configuración general del sistema.	El administrador consulta y ajusta los parámetros operativos del sistema sin intervención técnica sobre el código.
		OO-3.3.2: Configurar y probar el servicio de correo electrónico.	El administrador valida la conexión SMTP en tiempo real antes de habilitar notificaciones reales a clientes y socios.
		OO-3.3.3: Monitorear las métricas de almacenamiento del sistema.	El administrador anticipa problemas de capacidad de almacenamiento antes de que afecten el servicio.
		OO-3.3.4: Ver el estado de salud de todos los servicios del sistema.	El administrador detecta y atiende fallos de cualquier componente antes de que afecten al servicio prestado a los clientes.
	OT-3.4: Mantener trazabilidad y evidencia documental de todas las acciones del sistema.	OO-3.4.1: Ver el log de auditoría del sistema.	El área de cumplimiento y la dirección disponen de evidencia documental permanente de toda actividad relevante.
		OO-3.4.2: Filtrar y exportar el log de auditoría.	La dirección obtiene evidencia documental exportable para auditorías internas, externas y revisiones regulatorias.
Oe-4: Inteligencia De Negocio Centralizada Para La Ventaja Competitiva Aeronáutica	OT-4.1: Garantizar la integridad y disponibilidad del modelo analítico estructurado.	OO-4.1.1: Ver el resumen del modelo dimensional con el volumen de registros por tabla.	El administrador confirma que el modelo está completo y con el volumen esperado antes de que los analistas inicien su trabajo.
		OO-4.1.2: Explorar y gestionar registros del modelo analítico.	El administrador inspecciona registros puntuales del modelo dimensional para diagnóstico o corrección.
		OO-4.1.3: Validar la integridad referencial del modelo dimensional.	El sistema confirma que no existan inconsistencias entre la tabla de hechos y sus dimensiones tras cada actualización.
	OT-4.2: Proveer visibilidad ejecutiva de los indicadores clave de desempeño con alertas automáticas.	OO-4.2.1: Ver el dashboard de KPIs con filtros por período, aerolínea y ruta.	El analista obtiene una vista consolidada del desempeño global del sistema en tiempo real.
		OO-4.2.2: Detectar y visualizar alertas en KPIs fuera de los umbrales configurados.	El analista identifica de inmediato las aerolíneas con desempeño inferior al umbral mínimo aceptable.
		OO-4.2.3: Configurar los umbrales de alertas analíticas.	El administrador ajusta los límites que determinan cuándo se dispara una alerta en el dashboard.
	OT-4.3: Analizar la puntualidad operacional (OTP) de las aerolíneas con perspectiva comparativa.	OO-4.3.1: Analizar la puntualidad OTP por aerolínea.	El analista construye el perfil de desempeño completo de cada aerolínea monitoreada.
		OO-4.3.2: Comparar aerolíneas en rutas compartidas (benchmarking).	El cliente aerolínea conoce su posición competitiva real en cada ruta que opera frente a sus competidores.
		OO-4.3.3: Ver tendencias de puntualidad por período.	El analista identifica mejoras o deterioros sostenidos en el tiempo para fundamentar informes ejecutivos.
	OT-4.4: Evaluar el rendimiento y la eficiencia de las rutas operadas.	OO-4.4.1: Evaluar el rendimiento de rutas.	El analista identifica las rutas más y menos eficientes del sistema según tiempo real vs. programado.
		OO-4.4.2: Comparar el tiempo real vs. el tiempo programado por ruta.	El analista cuantifica la brecha entre lo planificado y lo realmente operado por ruta.
	OT-4.5: Analizar cancelaciones y desvíos operacionales por causa oficial FAA.	OO-4.5.1: Analizar cancelaciones por causa oficial FAA.	El analista identifica las causas dominantes de cancelación por aerolínea y período.
		OO-4.5.2: Analizar el impacto operacional de los desvíos.	El analista cuantifica el tiempo adicional y la distancia extra generados por desvíos a aeropuertos alternativos.
		OO-4.5.3: Ver la tendencia de cancelaciones mensual por categoría.	El analista visualiza la evolución de cancelaciones por categoría FAA a lo largo del tiempo.
	OT-4.6: Generar interpretaciones automáticas en lenguaje natural de los indicadores visualizados.	OO-4.6.1: Consultar la narrativa IA de un gráfico o KPI.	El analista obtiene un párrafo ejecutivo interpretando cualquier indicador, sin esfuerzo manual de redacción.
		OO-4.6.2: Configurar el proveedor de inteligencia artificial.	El administrador define el proveedor, modelo y parámetros del servicio de narrativa y asistente conversacional.
	OT-4.7: Proveer proyecciones predictivas de puntualidad y cancelaciones mediante series de tiempo.	OO-4.7.1: Generar proyección de riesgo operacional a 3-6 meses.	El cliente aerolínea anticipa el comportamiento futuro de sus indicadores clave con intervalos de confianza cuantificados.
		OO-4.7.2: Analizar patrones estacionales en el histórico de puntualidad y cancelaciones.	El analista identifica variaciones recurrentes para fundamentar la planificación operacional.
		OO-4.7.3: Exportar informe ejecutivo con los resultados del módulo predictivo.	El cliente recibe un documento con proyecciones, patrones estacionales y recomendaciones, listo para decisión.
	OT-4.8: Permitir consultas analíticas en lenguaje natural sin conocimiento técnico del analista.	OO-4.8.1: Consultar el asistente analítico conversacional con inteligencia artificial.	El analista obtiene respuestas fundamentadas en datos reales del sistema sin necesidad de escribir consultas técnicas.
	OT-4.9: Detectar comportamientos atípicos y simular escenarios de riesgo operacional.	OO-4.9.1: Ver recomendaciones automáticas priorizadas según el riesgo proyectado.	El analista recibe una lista accionable de recomendaciones operacionales ordenadas por severidad.
		OO-4.9.2: Detectar anomalías históricas en los indicadores de puntualidad y cancelación.	El analista identifica automáticamente los períodos con desviaciones estadísticamente significativas respecto al comportamiento histórico, distinguiendo anomalías favorables y desfavorables.
		OO-4.9.3: Ver el índice de riesgo predictivo por aerolínea.	El analista dispone de un ranking de aerolíneas ordenado por un score compuesto de riesgo operacional, que combina volatilidad, tendencia reciente y desempeño promedio.
		OO-4.9.4: Simular escenarios "qué pasaría si" sobre la proyección de riesgo.	El analista ajusta parámetros operacionales hipotéticos y visualiza en tiempo real el impacto proyectado, sin afectar los datos reales del sistema.
Tabla 5. Mapa de objetivos estratégicos, tácticos, operativos y metas de AeroTrack Analytics.


4. Descripción del Sistema AeroTrack Analytics
4.1 Resumen del Sistema
AeroTrack Analytics es un sistema de inteligencia de negocios aeronáutico que procesa dos millones de registros de vuelo del dataset Carrier On-Time Performance del Bureau of Transportation Statistics (BTS), correspondientes a treinta y tres aerolíneas que operan en los Estados Unidos. El sistema implementa una arquitectura de tres capas: una capa de ingesta y almacenamiento temporal donde los datos crudos son recibidos y validados; una capa analítica donde los datos se transforman en un modelo estrella de Kimball con una tabla de hechos y once dimensiones, complementado por siete tablas de indicadores precalculados; y una capa de presentación donde los resultados se exponen mediante una interfaz web con módulos de análisis interactivos, generación de informes y administración del sistema.
El sistema está concebido para operar de forma completamente contenida en infraestructura de contenedores, permitiendo su despliegue reproducible en cualquier entorno de computación compatible. Todos los parámetros operativos son configurables desde la interfaz web sin necesidad de intervención técnica directa sobre el código o la infraestructura.
4.2 Arquitectura Tecnológica
El sistema se compone de cinco servicios integrados que operan en red interna aislada:
Servicio de aplicación web. Desarrollado con el marco de trabajo FastAPI y el motor de plantillas Jinja2, expone la interfaz web en el puerto 8000 y gestiona toda la lógica de negocio, autenticación, control de acceso y generación de informes.
Servicio de datos operacional y de autenticación. PocketBase versión 0.22.4 actúa como base de datos operacional para usuarios, roles, permisos, configuración del sistema, registro de auditoría y datos de ingesta temporal. Disponible en el puerto 8090.
Servicio de almacenamiento analítico. MinIO proporciona almacenamiento de objetos compatible con el protocolo S3 para los archivos del modelo dimensional analítico en formato columnar Parquet. El servidor está disponible en el puerto 9000 y su consola de administración en el puerto 9001.
Servicio de orquestación de procesos. Apache Airflow versión 2.9.3 gestiona la ejecución del proceso automatizado de actualización de datos, incluyendo las etapas de extracción, transformación, carga y generación de indicadores precalculados. Disponible en el puerto 8080.
Base de datos de metadatos. PostgreSQL versión 15 almacena exclusivamente los metadatos internos de Apache Airflow, sin intervenir en la lógica de negocio del sistema.
4.3 Infraestructura y Despliegue
El sistema completo se despliega mediante un único archivo de composición de servicios (docker-compose.yml) que define la configuración, las dependencias, los volúmenes de persistencia y la red interna de todos los servicios. Esta arquitectura garantiza la reproducibilidad total del entorno en cualquier máquina con Docker Desktop instalado mediante un único comando de inicio.
 
Figura 1. Diagrama de despliegue de AeroTrack Analytics
Las credenciales de infraestructura (contraseñas, URLs de servicio interno) se gestionan mediante variables de entorno en un archivo de configuración (.env) que no forma parte del repositorio de código. Los parámetros operativos de negocio (umbrales de alerta, parámetros del proceso de datos, configuración de correo electrónico, parámetros del módulo de inteligencia artificial) se almacenan en la base de datos operacional y son modificables desde la interfaz web sin reiniciar ningún servicio.
4.4 Flujo de Procesamiento de Datos
El procesamiento de datos sigue un flujo de cuatro etapas organizadas y orquestadas por el servicio de automatización de procesos:
Extracción. Los registros de vuelo se extraen de la colección de ingesta temporal mediante acceso concurrente a la interfaz de programación del servicio de datos, con un número configurable de procesos paralelos para optimizar el rendimiento.
Carga. Los datos extraídos se materializan en el almacenamiento analítico en formato columnar optimizado para consultas analíticas.
Transformación. Se construye el modelo estrella de Kimball con una tabla de hechos central y once tablas de dimensión que representan las distintas perspectivas de análisis del vuelo.
•	Generación de indicadores. Se calculan y almacenan siete tablas de indicadores precalculados que alimentan directamente los módulos analíticos con tiempos de respuesta inferiores a tres segundos.
4.5 Modelo de Datos Analítico
El modelo analítico sigue el patrón estrella de Kimball, con una tabla de hechos central que almacena un registro por cada vuelo operado, rodeada de once tablas de dimensión que permiten analizar los datos desde distintas perspectivas: temporal, por aerolínea, por aeropuerto de origen y destino, por aeronave, por causa de retraso, por cancelación, por distancia, por desvío, por horario, por clasificación del retraso y por ruta.
 
Figura 2. Modelo de datos analítico de AeroTrack Analytics siguiendo el patrón estrella de Kimball.
Adicionalmente, el sistema mantiene siete tablas de indicadores precalculados que concentran los cálculos más frecuentes por aerolínea y período, por causa de retraso, por indicadores globales diarios, por eficiencia de rutas, por causas de retraso mensual, por día de la semana y por desvíos de ruta. Estas tablas eliminan la necesidad de procesar el conjunto completo de datos en cada consulta del analista.
4.6 Módulos principales del sistema
Los módulos de AeroTrack Analytics se organizan según las cuatro entregas de desarrollo del sistema (los módulos resaltados en amarillo son aquellos ya implementados):
Seguridad y control de acceso	Pipeline ELT y actualización de datos	Modelo dimensional y datos analíticos	Panel de indicadores (Dashboard)
Análisis de puntualidad OTP	Evaluación de eficiencia de rutas	Análisis de cancelaciones y desvíos	Generación de informes y reportes
Configuración del sistema	Auditoría y trazabilidad	Predicción con inteligencia artificial	Asistente analítico conversacional
Gestión de clientes aerolínea	Ecosistema de socios y API pública		
Tabla 6. Módulos principales del sistema AeroTrack Analytics.


5. Descripción del Sistema y su Aporte a los Niveles Organizacionales
La siguiente tabla presenta el detalle pormenorizado de cómo el sistema AeroTrack Analytics encaja en los objetivos de la organización, especificando para cada objetivo operativo el proceso de negocio que apoya, la funcionalidad concreta que ofrece el sistema, el indicador de desempeño asociado y el caso de uso correspondiente. La tabla se organiza por objetivo estratégico y abarca los cuatro objetivos estratégicos definidos.
OBJETIVO ESTRATÉGICO	OBJETIVO TÁCTICO	OBJETIVO OPERATIVO	PROCESO QUE APOYA	FUNCIONALIDAD DEL SISTEMA	INDICADOR KPI	CASO DE USO
Oe-4: Inteligencia De Negocio Centralizada Para La Ventaja Competitiva Aeronáutica.	OT-4.1: Garantizar la integridad y disponibilidad del modelo analítico estructurado.	OO-4.1.1: Ver el resumen del modelo dimensional con volumen por tabla.	Verificación del modelo analítico	El administrador confirma que el modelo dimensional está completo y con el volumen esperado de registros por tabla antes de que los analistas inicien su trabajo.	Registros por tabla · Última actualización · Tablas completas (%)	CU-O09
		OO-4.1.2: Explorar y gestionar registros del modelo analítico.	Gestión de registros del modelo	El administrador inspecciona y, de ser necesario, corrige registros puntuales del modelo dimensional para diagnóstico de inconsistencias.	Registros inspeccionados por período · Correcciones aplicadas	CU-O10
		OO-4.1.3: Validar la integridad referencial del modelo dimensional.	Validación de integridad referencial	El sistema confirma que no existan claves foráneas huérfanas ni inconsistencias entre la tabla de hechos y sus dimensiones tras cada actualización.	Validaciones exitosas (%) · Inconsistencias detectadas por ejecución	CU-O11
	OT-4.2: Proveer visibilidad ejecutiva de los indicadores clave con alertas automáticas.	OO-4.2.1: Ver dashboard de KPIs con filtros por período, aerolínea y ruta.	Visualización ejecutiva de indicadores	El sistema presenta un dashboard consolidado con los KPIs principales (vuelos, OTP, cancelaciones, retraso promedio), con filtros aplicables a toda la vista.	Tiempo de carga del dashboard (seg) · Consultas por sesión	CU-E01
		OO-4.2.2: Detectar y visualizar alertas en KPIs fuera de umbral.	Detección de desviaciones críticas	El sistema compara automáticamente los indicadores activos contra los umbrales configurados y visualiza alertas cuando el desempeño cae por debajo del mínimo aceptable.	Alertas generadas por período · Tiempo de respuesta a la alerta	CU-E02
		OO-4.2.3: Configurar los umbrales de alertas analíticas.	Configuración de criterios de alerta	El administrador ajusta los valores límite que determinan cuándo se dispara una alerta, adaptando la sensibilidad del sistema a la realidad operativa del cliente.	Umbrales configurados · Cambios de umbral por período	CU-T05
	OT-4.3: Analizar la puntualidad operacional (OTP) con perspectiva comparativa.	OO-4.3.1: Analizar puntualidad OTP por aerolínea.	Análisis de puntualidad por aerolínea	El analista construye el perfil de desempeño completo de cada aerolínea, incluyendo tendencia mensual, causas de retraso y variación por día de la semana.	OTP por aerolínea (%) · Retraso promedio (min)	CU-E03
		OO-4.3.2: Comparar aerolíneas en rutas compartidas (benchmarking).	Benchmarking competitivo	El cliente aerolínea conoce su posición competitiva real en cada ruta que opera frente a sus competidores directos.	Posición relativa en la ruta · Brecha de OTP vs líder (pp)	CU-E04
		OO-4.3.3: Ver tendencias de puntualidad por período.	Análisis de tendencias temporales	El analista identifica mejoras o deterioros sostenidos en el tiempo del índice de puntualidad, fundamentando los informes ejecutivos.	Variación OTP período actual vs anterior (pp)	CU-E05
	OT-4.4: Evaluar el rendimiento y eficiencia de las rutas operadas.	OO-4.4.1: Evaluar el rendimiento de rutas.	Evaluación de eficiencia de rutas	El analista identifica las rutas más y menos eficientes mediante un ranking y gráfico de dispersión basado en la diferencia entre tiempo real y programado.	Índice de eficiencia de ruta (%) · Rutas en el percentil inferior	CU-E06
		OO-4.4.2: Comparar tiempo real vs. programado por ruta.	Comparación de tiempos operacionales	El analista cuantifica la brecha entre el tiempo programado y el operado por ruta, identificando patrones sistemáticos de retraso o adelanto.	Brecha promedio tiempo real vs programado (min)	CU-E07
	OT-4.5: Analizar cancelaciones y desvíos operacionales por causa oficial.	OO-4.5.1: Analizar cancelaciones por causa FAA.	Análisis de cancelaciones por causa	El analista identifica las causas dominantes de cancelación (clima, aerolínea, NAS, seguridad) por aerolínea y período, según clasificación oficial FAA.	Tasa de cancelación (%) · Causa dominante por aerolínea	CU-E08
		OO-4.5.2: Analizar el impacto operacional de desvíos.	Análisis de impacto de desvíos	El analista cuantifica el tiempo adicional y la distancia extra generados por desvíos a aeropuertos alternativos, identificando las rutas con mayor incidencia.	Desvíos por ruta · Demora promedio por desvío (min)	CU-E09
		OO-4.5.3: Ver tendencia de cancelaciones mensual.	Análisis de tendencia de cancelaciones	El analista visualiza la evolución mensual de cancelaciones desagregadas por categoría FAA, identificando estacionalidad y picos atípicos.	Cancelaciones mensuales por categoría · Total acumulado del período	CU-E10
	OT-4.6: Generar interpretaciones automáticas en lenguaje natural de los indicadores.	OO-4.6.1: Consultar narrativa IA por gráfico o KPI.	Narrativa analítica automatizada	Al hacer clic en el botón de narrativa, el sistema envía al modelo de lenguaje los indicadores del elemento seleccionado y recibe un párrafo ejecutivo (hallazgo, causa probable, impacto, recomendación) en ventana emergente.	Tiempo de generación de narrativa (seg) · Disponibilidad del servicio IA (%)	CU-O14
		OO-4.6.2: Configurar el proveedor de inteligencia artificial.	Configuración del proveedor de IA	El administrador define el proveedor de lenguaje principal y de respaldo, así como los parámetros del servicio (temperatura, modelo, caché), desde el panel de administración.	Conmutaciones a proveedor de respaldo · Tiempo de respuesta promedio	CU-T09
	OT-4.7: Proveer proyecciones predictivas de puntualidad y cancelaciones mediante series de tiempo.	OO-4.7.1: Generar proyección de riesgo operacional a 3-6 meses.	Predicción operacional de puntualidad	El sistema aplica modelos de series de tiempo (Prophet) sobre el histórico para proyectar el comportamiento futuro, con intervalos de confianza del 90-95%.	Error Absoluto Medio del modelo (pp) · Cobertura del intervalo de confianza	CU-E14
		OO-4.7.2: Analizar patrones estacionales en el histórico.	Análisis de estacionalidad	El sistema descompone la serie histórica en sus componentes estacionales, identificando patrones cíclicos recurrentes por mes y día de la semana.	Patrones estacionales identificados · Varianza explicada por estacionalidad (%)	CU-E15
		OO-4.7.3: Exportar informe ejecutivo con resultados del módulo predictivo.	Generación de informe predictivo	El sistema genera un informe PDF con proyecciones, patrones estacionales y recomendaciones priorizadas, listo para entrega al cliente.	Informes generados por período · Tiempo de generación (seg)	CU-E17
	OT-4.8: Permitir consultas analíticas en lenguaje natural sin conocimiento técnico.	OO-4.8.1: Consultar el asistente analítico conversacional con IA.	Asistente conversacional con IA	El asistente emplea generación aumentada por recuperación (RAG), combinando capacidad generativa con datos reales recuperados de las tablas de agregación.	Consultas atendidas por período · Tiempo de respuesta (seg) · Tasa de respuestas fundamentadas	CU-E18
	OT-4.9: Detectar comportamientos atípicos y simular escenarios de riesgo operacional.	OO-4.9.1: Ver recomendaciones priorizadas según riesgo proyectado.	Priorización de recomendaciones	El sistema genera recomendaciones operacionales accionables a partir de las proyecciones de riesgo, ordenadas por severidad e impacto cuantificado, con enlaces directos al módulo correspondiente.	Recomendaciones generadas · Recomendaciones con seguimiento	CU-E16
		OO-4.9.2: Detectar anomalías históricas en puntualidad y cancelación.	Detección estadística de anomalías	El sistema identifica automáticamente, mediante análisis de desviación (z-score) sobre el histórico, los períodos con comportamiento estadísticamente atípico, distinguiendo anomalías favorables y desfavorables.	Anomalías detectadas por período · Z-score promedio de los eventos	CU-E20
		OO-4.9.3: Ver el índice de riesgo predictivo por aerolínea.	Ranking de riesgo operacional	El sistema calcula un score compuesto de riesgo por aerolínea, combinando volatilidad histórica, tendencia reciente y desempeño promedio, presentado como ranking ordenado.	Score de riesgo por aerolínea · Aerolíneas en categoría crítica	CU-E21
		OO-4.9.4: Simular escenarios "qué pasaría si" sobre la proyección.	Simulación de escenarios operacionales	El analista ajusta parámetros hipotéticos (buffer de conexión, reducción de carga) mediante controles interactivos y visualiza en tiempo real el impacto proyectado, sin alterar los datos reales.	Simulaciones ejecutadas por sesión · Variación de riesgo proyectada por escenario	CU-E22
Oe-1: Penetración Digital Y Adquisición Automatizada De Clientes Aeronáuticos.	OT-1.1: Captar aerolíneas y operadores mediante demostraciones y reportes digitales.	OO-1.1.1: Registrar y gestionar clientes aerolínea activos y prospectos.	Gestión de cartera de clientes	El sistema permite al administrador registrar, editar y dar seguimiento a cada cliente aerolínea (activo o prospecto), con datos de contacto, estado de contrato y plan contratado, centralizando la información comercial en un único catálogo.	Clientes activos · Prospectos en seguimiento · Tasa de renovación de contrato	CU-T10
		OO-1.1.2: Generar enlace de acceso temporal al panel para un prospecto.	Generación de acceso demo	El sistema genera un enlace único de acceso temporal de 48 horas al panel de análisis con datos reales, sin requerir creación de cuenta, permitiendo al prospecto evaluar el valor del servicio antes de contratar.	Enlaces generados por período · Tasa de conversión post-demo · Tiempo promedio hasta conversión	CU-O15
	OT-1.2: Automatizar la configuración y seguimiento de entregas periódicas a clientes suscritos.	OO-1.2.1: Configurar suscripciones de entrega automática por cliente.	Configuración de entregas automáticas	El administrador define, por cliente, el tipo de reporte, la frecuencia de envío y los filtros aplicados; el sistema genera y entrega el reporte sin intervención adicional una vez configurado.	Suscripciones activas · Reportes entregados por período · Tasa de error en entrega	CU-T11
		OO-1.2.2: Consultar el historial de entregas automáticas por cliente.	Seguimiento de entregas automáticas	El administrador consulta el historial completo de entregas realizadas por cliente, con fecha, tipo de reporte y resultado, para verificar la continuidad del servicio contratado.	Entregas exitosas / total (%) · Tiempo promedio de generación · Reclamos por entrega fallida	CU-O16
	OT-1.3: Generar y poner a disposición informes ejecutivos en múltiples formatos de salida.	OO-1.3.1: Exportar análisis a PDF con narrativa ejecutiva integrada.	Generación de informes ejecutivos	El sistema genera un informe PDF con secciones configurables, gráficos integrados y narrativa ejecutiva generada por IA, listo para presentación al cliente.	Tiempo de generación (seg) · Secciones incluidas · Descargas por período	CU-E11
		OO-1.3.2: Exportar análisis a Excel con hojas por módulo.	Generación de informes ejecutivos	El sistema genera un archivo Excel con múltiples hojas por módulo analítico, gráficos nativos y formato condicional aplicado automáticamente sobre los indicadores de puntualidad.	Tiempo de generación (seg) · Hojas generadas · Descargas por período	CU-E12
		OO-1.3.3: Exportar datos filtrados a CSV.	Exportación de datos crudos	El sistema exporta los registros de vuelo del período y filtros activos en formato CSV, permitiendo al cliente realizar análisis externo con sus propias herramientas.	Registros exportados · Tiempo de generación (seg) · Descargas por período	CU-E13
	OT-1.4: Medir y evaluar la efectividad de la estrategia de captación digital.	OO-1.4.1: Ver el panel de captación con métricas de demos, conversión y clientes activos.	Evaluación de efectividad comercial	El sistema consolida en un panel las métricas de demos enviados, tasa de conversión a contrato y clientes activos, permitiendo a la dirección ajustar la estrategia de captación digital con datos objetivos.	Demos generados · Tasa de conversión (%) · CAC (USD) · Clientes activos	CU-E19
Oe-2: Escalabilidad Comercial Por Plataformas De Ecosistemas Y Apis.	OT-2.1: Exponer la inteligencia analítica como servicio de programación documentado y seguro.	OO-2.1.1: Gestionar claves de acceso programático para socios tecnológicos.	Gestión del ecosistema de socios	El administrador genera claves de acceso únicas por socio tecnológico, con permisos diferenciados, límite de consultas por período y fecha de expiración configurable.	Claves activas · Consultas por clave / período · Claves revocadas	CU-T12
		OO-2.1.2: Acceder a los indicadores analíticos mediante clave programática.	Consumo del servicio de programación	El sistema socio consume los indicadores analíticos de AeroTrack mediante solicitudes programáticas autenticadas por clave, sin intervención manual ni acceso a la interfaz web.	Llamadas por endpoint · Latencia promedio (ms) · Disponibilidad de la API (%)	CU-O17
	OT-2.2: Notificar de forma proactiva al ecosistema de socios sobre la disponibilidad de datos nuevos.	OO-2.2.1: Configurar webhooks de notificación automática a socios.	Notificación proactiva a socios	El administrador configura webhooks que notifican automáticamente a los sistemas socios cuando se completa un ciclo de actualización, eliminando consultas periódicas de verificación.	Webhooks configurados · Notificaciones enviadas · Tasa de entrega exitosa (%)	CU-T13
	OT-2.3: Supervisar el consumo del servicio de programación por parte de los socios.	OO-2.3.1: Ver el panel de uso y métricas de la API por socio.	Supervisión del consumo de la API	El administrador monitorea el consumo por socio, identifica usos inusuales y obtiene métricas de adopción que fundamentan decisiones de precio y capacidad.	Llamadas totales por socio · Endpoint más consultado · Errores por socio	CU-O18
Oe-3: Expansión Continua Sobre Infraestructura En La Nube De Alta Disponibilidad.	OT-3.1: Gestionar identidades y el control de acceso seguro al sistema.	OO-3.1.1: Gestionar usuarios con credenciales generadas automáticamente.	Gestión de identidades de usuario	El sistema gestiona el ciclo de vida completo de los usuarios (creación, edición, activación/desactivación), con generación automática de credenciales temporales enviadas por correo sin que el administrador las vea en ningún momento.	Usuarios activos · Intentos de acceso fallidos · Usuarios desactivados por período	CU-T01
		OO-3.1.2: Administrar roles y matrices de permisos por módulo.	Control de acceso basado en roles	El administrador define roles con matrices de permisos configurables por módulo y tipo de acción (ver, crear, editar, eliminar, ejecutar, exportar, configurar), aplicadas automáticamente a cada solicitud del sistema.	Roles activos · Permisos configurados por módulo · Cambios de permisos por período	CU-T02
		OO-3.1.3: Iniciar/cerrar sesión y gestionar el perfil propio.	Autenticación y gestión de sesión	El sistema autentica al usuario mediante JWT, mantiene la sesión activa según su rol asignado y permite consultar o editar los datos personales del perfil propio en cualquier momento.	Sesiones activas · Tiempo promedio de sesión · Cambios de perfil por período	CU-O01, CU-O02, CU-O03
		OO-3.1.4: Ver la matriz de permisos vigente del sistema.	Auditoría de control de acceso	El administrador consulta una vista de solo lectura con módulos en filas y roles en columnas, mostrando las acciones habilitadas por combinación, útil para auditoría rápida sin navegar módulo por módulo.	Roles auditados por período · Inconsistencias detectadas	CU-O04
	OT-3.2: Automatizar y supervisar el ciclo de actualización del modelo analítico.	OO-3.2.1: Configurar y programar la ejecución automática del pipeline.	Programación de la actualización de datos	El administrador define la frecuencia y horario de ejecución del proceso de actualización, así como parámetros operativos (tamaño de lote, procesos paralelos, reintentos), ajustables sin reiniciar servicios.	Ejecuciones programadas cumplidas (%) · Parámetros modificados por período	CU-T06
		OO-3.2.2: Ejecutar el pipeline ELT manualmente desde la interfaz web.	Orquestación del proceso de actualización	El sistema permite al administrador iniciar el proceso bajo demanda, extrayendo los registros del staging, transformándolos al modelo dimensional y generando los indicadores precalculados.	Registros procesados por ejecución · Duración del ciclo (min) · Tasa de éxito (%)	CU-O05
		OO-3.2.3: Monitorear el estado del DAG en ejecución.	Supervisión del proceso en ejecución	El administrador supervisa en tiempo real el avance de cada etapa (extracción, transformación, carga, indicadores), recibiendo notificación automática al completarse.	Etapas completadas en tiempo real · Tiempo restante estimado	CU-O06
		OO-3.2.4: Consultar el historial de ejecuciones del pipeline.	Gestión del historial del proceso	El sistema registra cada ejecución con fecha, duración, estado final y detalle de errores por etapa; el administrador consulta el historial para verificar completitud.	Ejecuciones exitosas / total (%) · Duración promedio (min) · Errores por etapa	CU-O07
		OO-3.2.5: Ver logs de error y reintentar ejecuciones fallidas.	Diagnóstico y recuperación de fallos	El administrador consulta los logs detallados de error por etapa y reintenta la ejecución fallida sin reiniciar el proceso completo.	Reintentos exitosos (%) · Tiempo promedio de recuperación	CU-O08
	OT-3.3: Garantizar la continuidad operativa mediante monitoreo proactivo de la infraestructura.	OO-3.3.1: Ver el panel de configuración general del sistema.	Gestión de parámetros operativos	El administrador consulta y ajusta dinámicamente los parámetros del sistema (umbrales, IA, correo, pipeline) agrupados por categoría, sin reiniciar ningún servicio.	Parámetros configurables · Cambios de configuración por período	CU-T03
		OO-3.3.2: Configurar y probar el servicio de correo electrónico.	Configuración de notificaciones del sistema	El administrador configura los parámetros SMTP y valida la conexión en tiempo real mediante una prueba de envío, antes de habilitar notificaciones reales.	Pruebas de conexión exitosas (%) · Notificaciones enviadas por período	CU-T04
		OO-3.3.3: Monitorear las métricas de almacenamiento.	Monitoreo de capacidad de almacenamiento	El administrador supervisa el uso del almacenamiento analítico (MinIO), anticipando problemas de capacidad antes de que afecten la disponibilidad del servicio.	Almacenamiento utilizado (%) · Crecimiento mensual (GB)	CU-T07
		OO-3.3.4: Ver el estado de salud de todos los servicios del sistema.	Monitoreo de disponibilidad de servicios	El sistema verifica cada 30 segundos el estado de todos los componentes de la plataforma, reflejándolo en tiempo real en la barra de navegación principal.	Disponibilidad de componentes (%) · Latencia de respuesta (ms)	CU-T08
	OT-3.4: Mantener trazabilidad y evidencia documental de todas las acciones del sistema.	OO-3.4.1: Ver el log de auditoría del sistema.	Registro de auditoría	El sistema registra de forma inmutable cada acción relevante (creación, edición, eliminación, ejecución de procesos), disponible para consulta por el área de cumplimiento.	Eventos registrados por período · Cobertura de módulos auditados (%)	CU-O12
		OO-3.4.2: Filtrar y exportar el log de auditoría.	Exportación de evidencia de auditoría	El administrador filtra el log por usuario, módulo, acción o rango de fechas, y lo exporta en formato adecuado para auditorías internas, externas o regulatorias.	Exportaciones realizadas por período · Tiempo de respuesta a solicitudes	CU-O13
Tabla 7. Descripción del sistema AeroTrack Analytics y su aporte a los niveles organizacionales.

6. Casos de Uso del Sistema
6.1 Actores del Sistema
El sistema AeroTrack Analytics contempla tres actores con responsabilidades y permisos diferenciados:
Administrador. Responsable de la configuración, operación y mantenimiento del sistema. Gestiona usuarios, roles, parámetros operativos y el proceso de actualización de datos. No realiza análisis de los datos aeronáuticos.
Analista de Datos. Empleado de AeroTrack que utiliza los módulos analíticos del sistema para producir la inteligencia que se entrega a los clientes aerolínea. No tiene acceso a las funciones de administración del sistema.
Socio tecnológico. Actor externo a AeroTrack que consume los resultados analíticos mediante la interfaz de programación del sistema, disponible a partir de la cuarta entrega. No accede a la interfaz web del sistema.
6.2 Catálogo general de casos de uso
El sistema cuenta con 53 casos de uso organizados en tres niveles. Los estratégicos generan inteligencia para la toma de decisiones; los tácticos configuran y administran el sistema; los operativos ejecutan acciones cotidianas. La columna "Objetivo relacionado" referencia el nivel jerárquico correspondiente: OE para estratégicos, OT para tácticos y OO para operativos.
A. Casos de uso estratégicos
CÓDIGO	CASO DE USO	ACTOR PRINCIPAL	OBJETIVO RELACIONADO
CU-E01	Ver dashboard de KPIs con filtros	Analista de Datos	OE-4
CU-E02	Detectar y visualizar alertas en KPIs	Sistema / Analista	OE-4
CU-E03	Analizar puntualidad OTP por aerolínea	Analista de Datos	OE-4
CU-E04	Comparar aerolíneas en rutas compartidas	Analista de Datos	OE-4
CU-E05	Ver tendencias de puntualidad por período	Analista de Datos	OE-4
CU-E06	Evaluar rendimiento de rutas	Analista de Datos	OE-4
CU-E07	Comparar tiempo real vs programado por ruta	Analista de Datos	OE-4
CU-E08	Analizar cancelaciones por causa FAA	Analista de Datos	OE-4
CU-E09	Analizar impacto operacional de desvíos	Analista de Datos	OE-4
CU-E10	Ver tendencia de cancelaciones mensual	Analista de Datos	OE-4
CU-E11	Exportar análisis a PDF	Analista de Datos	OE-1, OE-4
CU-E12	Exportar análisis a Excel	Analista de Datos	OE-1, OE-4
CU-E13	Exportar datos filtrados a CSV	Analista de Datos	OE-1, OE-4
CU-E14	Generar proyección de riesgo operacional	Analista de Datos	OE-4
CU-E15	Analizar patrones estacionales	Analista de Datos	OE-4
CU-E16	Ver recomendaciones automáticas priorizadas	Analista de Datos	OE-4
CU-E17	Exportar informe ejecutivo IA	Analista de Datos	OE-4
CU-E18	Consultar asistente analítico IA	Analista de Datos	OE-4
CU-E19	Ver panel de captación y conversión de clientes	Administrador	OE-1
CU-E20	Detectar anomalías históricas en indicadores de puntualidad y cancelación	Analista de Datos	OE-4
CU-E21	Ver índice de riesgo predictivo por aerolínea	Analista de Datos	OE-4
CU-E22	Simular escenarios "qué pasaría si" sobre la proyección de riesgo operacional	Analista de Datos	OE-4
Tabla 8. Catálogo de casos de uso estratégicos.




B. Casos de uso tácticos
CÓDIGO	CASO DE USO	ACTOR PRINCIPAL	OBJETIVO RELACIONADO
CU-T01	Gestionar usuarios del sistema	Administrador	OT-3.1
CU-T02	Administrar roles y asignar permisos	Administrador	OT-3.1
CU-T03	Ver panel de configuración general	Administrador	OT-3.3
CU-T04	Configurar y probar servicio de correo electrónico	Administrador	OT-3.3
CU-T05	Configurar umbrales de alertas analíticas	Administrador	OT-4.2
CU-T06	Configurar y programar ejecución del pipeline	Administrador	OT-3.2
CU-T07	Monitorear métricas de almacenamiento (MinIO)	Administrador	OT-3.3
CU-T08	Ver estado de salud de servicios del sistema	Administrador	OT-3.3
CU-T09	Configurar parámetros del asistente IA	Administrador	OT-4.6
CU-T10	Gestionar clientes aerolínea	Administrador	OT-1.1
CU-T11	Configurar suscripciones de reporte por cliente	Administrador	OT-1.2
CU-T12	Gestionar claves de acceso programático para socios	Administrador	OT-2.1
CU-T13	Configurar webhooks de notificación a socios	Administrador	OT-2.2
Tabla 9. Catálogo de casos de uso tácticos.
C. Casos de uso operativos
CÓDIGO	CASO DE USO	ACTOR PRINCIPAL	OBJETIVO RELACIONADO
CU-O01	Iniciar sesión	Admin / Analista	OO-3.1.3
CU-O02	Cerrar sesión	Admin / Analista	OO-3.1.3
CU-O03	Ver y editar perfil propio	Admin / Analista	OO-3.1.3
CU-O04	Ver matriz de permisos del sistema	Administrador	OO-3.1.4
CU-O05	Ejecutar pipeline ELT manualmente	Administrador	OO-3.2.2
CU-O06	Monitorear estado del DAG en ejecución	Administrador	OO-3.2.3
CU-O07	Consultar historial de ejecuciones	Administrador	OO-3.2.4
CU-O08	Ver logs de error y reintentar ejecución	Administrador	OO-3.2.5
CU-O09	Ver resumen del modelo dimensional	Administrador	OO-4.1.1
CU-O10	Explorar y gestionar registros del modelo	Administrador	OO-4.1.2
CU-O11	Validar integridad del modelo dimensional	Administrador	OO-4.1.3
CU-O12	Ver log de auditoría del sistema	Administrador	OO-3.4.1
CU-O13	Filtrar y exportar log de auditoría	Administrador	OO-3.4.2
CU-O14	Consultar narrativa IA de un gráfico o KPI	Analista de Datos	OO-4.6.1
CU-O15	Generar enlace de acceso demo para prospecto	Administrador	OO-1.1.2
CU-O16	Ver historial de entregas automáticas por cliente	Administrador	OO-1.2.2
CU-O17	Acceder a análisis mediante clave API	Socio tecnológico	OO-2.1.2
CU-O18	Ver métricas de uso de la API por socio	Administrador	OO-2.3.1
Tabla 10. Catálogo de casos de uso operativos.


6.3 Diagrama textual de casos de uso
La siguiente representación muestra, de forma esquemática, la relación directa entre cada actor del sistema y los casos de uso que le corresponden.
SISTEMA AEROTRACK ANALYTICS

Analista de Datos  ──────>  Ver dashboard de KPIs con filtros [CU-E01]
Analista de Datos  ──────>  Analizar puntualidad OTP por aerolínea [CU-E03]
Analista de Datos  ──────>  Comparar aerolíneas en rutas compartidas [CU-E04]
Analista de Datos  ──────>  Ver tendencias de puntualidad por período [CU-E05]
Analista de Datos  ──────>  Evaluar rendimiento de rutas [CU-E06]
Analista de Datos  ──────>  Comparar tiempo real vs programado por ruta [CU-E07]
Analista de Datos  ──────>  Analizar cancelaciones por causa FAA [CU-E08]
Analista de Datos  ──────>  Analizar impacto operacional de desvíos [CU-E09]
Analista de Datos  ──────>  Ver tendencia de cancelaciones mensual [CU-E10]
Analista de Datos  ──────>  Exportar análisis a PDF [CU-E11]
Analista de Datos  ──────>  Exportar análisis a Excel [CU-E12]
Analista de Datos  ──────>  Exportar datos filtrados a CSV [CU-E13]
Analista de Datos  ──────>  Generar proyección de riesgo operacional [CU-E14]
Analista de Datos  ──────>  Analizar patrones estacionales [CU-E15]
Analista de Datos  ──────>  Ver recomendaciones automáticas priorizadas [CU-E16]
Analista de Datos  ──────>  Exportar informe ejecutivo IA [CU-E17]
Analista de Datos  ──────>  Consultar asistente analítico IA [CU-E18]
Analista de Datos  ──────>  Detectar anomalías históricas en puntualidad y cancelación [CU-E20]
Analista de Datos  ──────>  Ver índice de riesgo predictivo por aerolínea [CU-E21]
Analista de Datos  ──────>  Simular escenarios “qué pasaría si” sobre la proyección [CU-E22]
Analista de Datos  ──────>  Consultar narrativa IA de un gráfico o KPI [CU-O14]


7. Visión Arquitectónica del Sistema
La visión arquitectónica relaciona los niveles organizacionales de AeroTrack Analytics con los casos de uso del sistema, describiendo qué técnicas analíticas o de inteligencia artificial se aplican, qué modelo de datos se utiliza y qué tipo de registros alimentan cada proceso.
7.1 Enfoque general por nivel organizacional
La siguiente tabla presenta cómo cada nivel organizacional se relaciona con el tipo de decisión que soporta el sistema, las técnicas principales que aplica y el tipo de datos que utiliza.
NIVEL ORGANIZACIONAL	TIPO DE DECISIÓN	TÉCNICAS PRINCIPALES	TIPO DE DATOS USADOS
Estratégico	Decisiones de largo plazo orientadas a la competitividad de las aerolíneas cliente	Inteligencia de negocios, agregaciones, predicción de series de tiempo, benchmarking competitivo, detección de tendencias, modelos de lenguaje natural	Datos históricos consolidados de puntualidad, cancelaciones, eficiencia de rutas y comparativas por aerolínea y período
Táctico	Planeación operativa y control mensual de los indicadores del servicio analítico	Configuración de alertas inteligentes, pronósticos de disponibilidad, gestión de suscripciones y socios tecnológicos, monitoreo de infraestructura	Datos agrupados por aerolínea, ruta, período, cliente y componente del sistema
Operativo	Ejecución diaria de tareas de análisis, administración del sistema y actualización de datos	Reglas de negocio, validaciones automáticas, alertas operativas, narrativa analítica con inteligencia artificial, registros transaccionales de auditoría	Datos en tiempo real del proceso de actualización, el modelo dimensional, los módulos analíticos y el registro inmutable de auditoría
Tabla 11. Enfoque general del sistema AeroTrack Analytics por nivel organizacional.






7.2 Modelo analítico general del sistema
El sistema AeroTrack Analytics opera en cinco capas progresivas que transforman los datos crudos en inteligencia accionable para las aerolíneas cliente:
Sistema operacional — Fuente de datos
Dataset BTS/FAA: 2.000.000 registros de vuelo · 109 variables · 33 aerolíneas
(Colección de ingesta: PocketBase — vuelos_raw)
↓
Pipeline ELT automatizado (Apache Airflow)
Extracción concurrente → Carga en staging → Transformación dimensional
→ Generación de indicadores precalculados
↓
Modelo dimensional analítico (MinIO — formato Parquet)
fact_vuelo + 11 dimensiones + 7 tablas de indicadores precalculados
↓
Capa de presentación e inteligencia
Módulos analíticos (dashboard, puntualidad, rutas, cancelaciones)
Reportes PDF · Excel · CSV
Narrativa analítica automática con IA (Grok / Gemini)
Módulo predictivo Prophet
Asistente analítico conversacional RAG
↓
Decisión
Informe ejecutivo para aerolínea cliente · Benchmarking competitivo · Proyección operacional





7.3 Tablas de hechos principales
Las tablas de hechos almacenan los eventos medibles del sistema. AeroTrack Analytics cuenta con una tabla de hechos atómica y siete tablas de hechos de agregación precalculadas que alimentan los módulos analíticos.
TABLA DE HECHOS	GRANULARIDAD	QUÉ MIDE	MÉTRICAS PRINCIPALES
TABLA ATÓMICA			
Fact_Vuelo	1 registro por vuelo	Cada operación de vuelo en la red aérea	Retraso llegada/salida (min), tiempo real de vuelo, distancia, cancelación, desvío
TABLAS DE AGREGACIÓN PRECALCULADAS			
Agg_Otp_Aerolinea_Mes	Aerolínea × mes	Índice de puntualidad consolidado	OTP%, vuelos a tiempo, retraso promedio
Agg_Kpi_Global_Dia	Día	Indicadores operacionales diarios	OTP diario, retraso promedio, cancelados, desviados
Agg_Rutas_Eficiencia	Ruta × aerolínea	Eficiencia de cada trayecto	Índice eficiencia, tiempo real promedio, tiempo programado promedio
Agg_Cancelaciones_Causa	Causa FAA × mes	Cancelaciones por categoría oficial	Total cancelados por causa, porcentaje del período
Agg_Causas_Retraso_Mes	Aerolínea × mes	Minutos de retraso por categoría	Minutos  erolín, clima, tráfico aéreo, seguridad, avión tardío
Agg_Otp_Dia_Semana	Día de la semana	Puntualidad histórica semanal	OTP% por día, vuelos a tiempo
Agg_Desvios_Ruta	Ruta × aeropuerto alternativo	Impacto de desvíos	Total desvíos, retraso promedio, distancia adicional

Tabla 12. Tablas de hechos principales del modelo analítico de AeroTrack Analytics.
7.4 Dimensiones principales
Las dimensiones describen el contexto de los hechos registrados. El modelo de AeroTrack Analytics utiliza once dimensiones que permiten analizar los datos desde múltiples perspectivas.
DIMENSIÓN	USO EN EL SISTEMA
Dim_Tiempo	Fecha, año, trimestre, mes, día del mes y día de la semana del vuelo
Dim_Aerolinea	Aerolínea operadora: código IATA, código DOT, número de vuelo
Dim_Aeropuerto	Aeropuerto de origen y destino — dimensión de rol dual: una sola tabla referenciada dos veces
Dim_Avion	Aeronave física identificada por matrícula y número de vuelo de la aerolínea
Dim_Retraso_Causa	Minutos de retraso desglosados por causa: aerolínea, clima, tráfico aéreo nacional, seguridad y avión tardío
Dim_Cancelacion	Tipo de cancelación o desvío según código oficial FAA: A (aerolínea), B (clima), C (sistema), D (seguridad)
Dim_Distancia	Distancia del trayecto en millas y clasificación por grupo de distancia
Dim_Desvio	Detalle de vuelos redirigidos: aeropuerto alternativo, tiempo adicional y distancia extra recorrida
Dim_Horario	Tiempos programados y reales de salida y llegada en formato HHMM
Dim_Clasificacion_Retraso	Indicadores binarios y grupos de clasificación del retraso de salida y llegada
Dim_Ruta	Combinación origen-destino como entidad de negocio: códigos IATA y ciudades
Tabla 13. Dimensiones principales del modelo analítico de AeroTrack Analytics.



7.5 Técnicas usadas por nivel organizacional
A. Nivel estratégico
TÉCNICA	USO EN AEROTRACK ANALYTICS
Business Intelligence Y Agregaciones	Cálculo del índice de puntualidad global, ranking de aerolíneas, evolución mensual de cancelaciones y análisis de eficiencia de rutas
Benchmarking Competitivo	Comparativa del OTP y retraso promedio de todas las aerolíneas que operan una misma ruta, con visualización paralela de resultados
Detección De Anomalías Y Alertas	Evaluación automática de cada KPI contra el umbral configurado; generación de alertas visuales cuando un indicador cruza el límite aceptable
Predicción Con Series De Tiempo	Proyección del índice de puntualidad y tasa de cancelaciones para los próximos tres a seis meses mediante análisis de patrones históricos
Modelos De Lenguaje Natural (Ia Generativa)	Generación automática de narrativas analíticas ejecutivas en español al visualizar cada gráfico o KPI de los módulos de análisis
Recuperación Aumentada Con Ia (Rag)	Asistente analítico conversacional que responde preguntas en lenguaje natural sobre los datos del sistema
Tabla 14. Técnicas analíticas e IA aplicadas en el nivel estratégico.
B. Nivel táctico
TÉCNICA	USO EN AEROTRACK ANALYTICS
Configuración De Alertas Inteligentes	Umbrales dinámicos para OTP mínimo, tasa máxima de cancelaciones, retraso promedio y eficiencia de ruta, configurables desde la interfaz de administración
Monitoreo De Infraestructura En Tiempo Real	Verificación automática del estado de disponibilidad de todos los componentes del sistema con refresco cada treinta segundos
Control De Acceso Diferenciado (Rbac)	Gestión de permisos por módulo y tipo de acción para cada rol, sin código adicional al registrar nuevos módulos
Programación Automática De Procesos	Configuración de la frecuencia y horario de ejecución del proceso de actualización de datos directamente desde el panel de administración
Validación De Integridad Del Modelo	Verificación automática de la consistencia referencial entre la tabla de hechos y todas las dimensiones tras cada actualización
Tabla 15. Técnicas analíticas e IA aplicadas en el nivel táctico.
C. Nivel operativo
TÉCNICA	USO EN AEROTRACK ANALYTICS
Reglas De Negocio	Control de acceso por sesión activa, restricción de eliminación de filas especiales del modelo y validación de roles antes de ejecutar cada acción
Validaciones Automáticas	Verificación de integridad de claves foráneas, ausencia de valores nulos en campos obligatorios y unicidad de registros en colecciones operacionales
Alertas Operativas	Notificación automática por correo electrónico al completarse o fallar el proceso de actualización de datos
Registro Transaccional Inmutable	Log de auditoría con inserción única (sin posibilidad de modificar ni eliminar) de cada acción realizada en el sistema
Extracción Paralela De Datos	Proceso de extracción con múltiples trabajadores concurrentes configurables para superar el límite de registros por página de la fuente de datos
Tabla 16. Técnicas analíticas e inteligencia artificial aplicadas por nivel en AeroTrack Analytics.
7.6 Matriz por casos de uso estratégicos
Las siguientes matrices describen, para cada caso de uso, las técnicas analíticas o de inteligencia artificial aplicadas, las tablas del modelo de datos involucradas, los reportes o resultados generados y los registros que alimentan el proceso.
CASO DE USO	TÉCNICAS USADAS	MODELO FACT-DIM	REPORTES GENERADOS	REGISTROS USADOS
Cu-E01: Ver Dashboard De Kpis	BI, agregaciones por período, comparación contra umbrales configurados	agg_otp_aerolinea_mes, agg_kpi_global_dia, dim_tiempo, dim_aerolinea	Panel principal de indicadores con alertas visuales	Puntualidad, cancelaciones y volumen de vuelos por período
Cu-E02: Detectar Alertas En Kpis	Detección de anomalías, reglas de umbral dinámico, alertas automáticas	agg_otp_aerolinea_mes, agg_kpi_global_dia + configuración de umbrales	Alertas con indicador de severidad en el panel	KPIs calculados y umbrales de alerta configurados por el administrador
Cu-E03: Analizar Otp Por Aerolínea	Agregaciones, ranking comparativo, gráficos de estado por color	agg_otp_aerolinea_mes, agg_otp_dia_semana, dim_aerolinea, dim_tiempo	Ranking de puntualidad por aerolínea	Índice OTP, total vuelos y vuelos a tiempo por aerolínea y período
Cu-E04: Comparar Aerolíneas En Rutas	Benchmarking competitivo, gráfico de doble eje OTP/retraso	agg_rutas_eficiencia, dim_ruta, dim_aerolinea	Comparativa de OTP y retraso por aerolínea en la ruta	OTP%, retraso promedio y vuelos de cada aerolínea en la ruta seleccionada
Cu-E05: Ver Tendencias De Puntualidad	Análisis de series de tiempo, gráfico de línea, estacionalidad semanal	agg_otp_aerolinea_mes, agg_otp_dia_semana, dim_tiempo	Gráfico de tendencia OTP mensual y por día de semana	OTP mensual por aerolínea, OTP histórico por día de la semana
Cu-E06: Evaluar Rendimiento De Rutas	Índice de eficiencia, mapa geográfico de red, gráfico de dispersión	agg_rutas_eficiencia, dim_ruta, dim_aeropuerto	Mapa de red de rutas y ranking por eficiencia	Tiempo real promedio, tiempo programado e índice de eficiencia por ruta
Cu-E07: Tiempo Real Vs Programado	Distribución estadística, diagrama de caja, histograma de retrasos	fact_vuelo, agg_otp_aerolinea_mes, dim_ruta, dim_tiempo	Perfil operacional de la ruta con distribución y OTP mensual	Vuelos individuales de la ruta: tiempo real, tiempo programado, retraso
Cu-E08: Analizar Cancelaciones Faa	Agregaciones por categoría, gráfico de dona, análisis de distribución	agg_cancelaciones_causa, dim_cancelacion, dim_tiempo	Distribución de cancelaciones por código FAA	Total cancelados por causa A/B/C/D y porcentaje sobre el total del período
Cu-E09: Analizar Impacto De Desvíos	Agregaciones por ruta y aeropuerto alternativo, ranking de impacto	agg_desvios_ruta, dim_ruta, dim_aeropuerto	Tabla de desvíos con impacto en tiempo y distancia	Total desvíos, retraso promedio y distancia adicional por ruta
Cu-E10: Tendencia Cancelaciones Mensual	Series de tiempo, barras apiladas por categoría con línea de total	agg_cancelaciones_causa, dim_tiempo	Gráfico de tendencia mensual por categoría FAA	Cancelaciones mensuales por código y total acumulado del período
Cu-E11: Exportar Análisis A Pdf	BI, renderizado HTML/CSS a PDF, exportación de reportes configurables	agg_otp_aerolinea_mes, agg_cancelaciones_causa, agg_rutas_eficiencia, agg_kpi_global_dia	Informe ejecutivo PDF con las secciones seleccionadas	Todos los indicadores del período según las secciones elegidas por el analista
Cu-E12: Exportar Análisis A Excel	Exportación estructurada, gráficos nativos, formato condicional en OTP	agg_otp_aerolinea_mes, agg_cancelaciones_causa, agg_rutas_eficiencia, dim_tiempo	Archivo Excel con 5 hojas por módulo y gráficos integrados	Indicadores calculados por período para cada hoja de análisis
Cu-E13: Exportar Datos A Csv	Exportación de datos crudos filtrados para análisis externo	fact_vuelo, dim_tiempo, dim_aerolinea, dim_aeropuerto, dim_ruta	Archivo CSV con registros de vuelo filtrados	Registros de fact_vuelo aplicando los filtros de período y aerolínea activos
Cu-E14: Proyección De Riesgo Operacional	Predicción con series de tiempo (Prophet), intervalos de confianza del 90%	agg_otp_aerolinea_mes, agg_cancelaciones_causa, dim_tiempo	Proyección de OTP y cancelaciones para los próximos 3-6 meses	Histórico mensual de OTP y cancelaciones como serie de tiempo para entrenamiento
Cu-E15: Analizar Patrones Estacionales	Descomposición estacional de series de tiempo, análisis de componentes	agg_otp_aerolinea_mes, agg_otp_dia_semana, agg_cancelaciones_causa, dim_tiempo	Identificación de patrones estacionales de puntualidad y cancelaciones	Histórico de OTP y cancelaciones por mes y por día de semana
Cu-E16: Ver Recomendaciones Priorizadas	Análisis de riesgo basado en proyecciones, priorización por severidad	Resultados del modelo predictivo sobre agg_otp_aerolinea_mes	Lista de recomendaciones operacionales ordenadas por riesgo	Proyecciones de OTP y rutas e indicadores identificados como en riesgo
Cu-E17: Exportar Informe Ejecutivo Ia	Generación de documentos, exportación con modelos de lenguaje	Resultados del módulo predictivo sobre tablas de agregación	Informe PDF con proyecciones, patrones y recomendaciones generadas por IA	Proyecciones generadas, patrones estacionales, recomendaciones priorizadas
Cu-E18: Consultar Asistente Analítico Ia	Generación aumentada por recuperación (RAG), modelos de lenguaje natural	Todas las tablas de agregación según la consulta del analista	Respuesta en lenguaje natural con datos del modelo analítico	Datos recuperados de las tablas de agregación según la pregunta formulada
Cu-E19: Ver Panel De Captación (E4)	BI comercial, métricas de conversión, KPIs de captación digital	pb_clientes, pb_demo_tokens, pb_entregas_historial	Panel con demos enviados, conversiones, clientes activos y CAC	Accesos demo generados, conversiones registradas, clientes aerolínea activos
Cu-E20: Detectar Anomalías Históricas	Detección estadística de anomalías (z-score), desviación respecto a media móvil	agg_otp_aerolinea_mes, dim_tiempo, dim_aerolinea	Lista de eventos anómalos con fecha, z-score, desviación en pp y sparkline de contexto	Histórico mensual de OTP por aerolínea para cálculo de media y desviación estándar
Cu-E21: Ver Índice De Riesgo Por Aerolínea	Scoring compuesto ponderado (volatilidad, tendencia, desempeño promedio)	agg_otp_aerolinea_mes, agg_cancelaciones_causa, dim_aerolinea	Tabla ranking con score, badge de categoría de riesgo y tendencia reciente por aerolínea	Histórico de OTP y cancelaciones por aerolínea de los últimos períodos disponibles
Cu-E22: Simular Escenarios What-If	Simulación interactiva por ajuste de parámetros sobre el modelo Prophet ya entrenado	Resultados del modelo predictivo sobre agg_otp_aerolinea_mes	Proyección recalculada en tiempo real según los parámetros del simulador (buffer, reducción de carga)	Parámetros del simulador y proyección base del modelo
Tabla 17. Matriz de casos de uso estratégicos de AeroTrack Analytics.
7.7 Matriz por casos de uso tácticos
CASO DE USO	TÉCNICAS USADAS	MODELO FACT-DIM	REPORTES GENERADOS	REGISTROS USADOS
Cu-T01: Gestionar Usuarios	Gestión de identidades, autenticación JWT, RBAC por rol	pb_app_users, pb_roles	Listado de usuarios con estado y rol asignado	Nombre, email, rol, estado, fecha de creación
Cu-T02: Administrar Roles Y Permisos	Control de acceso basado en roles, matrices de permisos dinámicas	pb_roles, pb_permisos, pb_roles_permisos, pb_modulos	Matriz de permisos por rol y módulo	Roles activos, permisos por módulo, asignaciones vigentes
Cu-T03: Ver Panel De Configuración	Gestión dinámica de parámetros sin reinicio de servicios	pb_configuracion_sistema	Vista de parámetros configurables agrupados por categoría	Claves de configuración, valores, tipos y estado de sensibilidad
Cu-T04: Configurar Correo Electrónico	SMTP, prueba de conexión en tiempo real	pb_configuracion_sistema (parámetros de email)	Resultado de prueba de conexión exitoso o fallido	Host SMTP, puerto, credenciales, resultado de la prueba
Cu-T05: Configurar Umbrales De Alertas	Reglas de negocio configurables, evaluación dinámica de KPIs	pb_configuracion_sistema (parámetros de alerta)	Confirmación de umbrales guardados; el dashboard los aplica en la siguiente carga	OTP mínimo aceptable, tasa máxima de cancelación, retraso promedio máximo
Cu-T06: Configurar Y Programar Pipeline	Orquestación de procesos, programación de tareas automáticas	pb_configuracion_sistema (parámetros del pipeline)	Confirmación de parámetros guardados con próxima ejecución programada	Lote de extracción, trabajadores concurrentes, reintentos, frecuencia automática
Cu-T07: Monitorear Almacenamiento	Consulta de métricas de almacenamiento de objetos S3	MinIO API (buckets: aerotrack-dims, aerotrack-exports, aerotrack-raw)	Panel con buckets, objetos y tamaño en MB	Listado de buckets, conteo de objetos y volumen en almacenamiento
Cu-T08: Ver Estado De Servicios	Health check con latencia, monitoreo de disponibilidad	PocketBase API, MinIO API, Airflow API	Panel de estado en tiempo real con latencia de respuesta	Latencia en ms, estado online/offline, estado del scheduler de Airflow
Cu-T09: Configurar Asistente Ia	Gestión de proveedores de IA, configuración de modelos de lenguaje	pb_configuracion_sistema (parámetros de IA)	Confirmación de configuración guardada para el proveedor activo	Proveedor, modelo, endpoint, temperatura, tokens máximos, timeout
Cu-T10: Gestionar Clientes Aerolínea (E4)	Gestión de cartera B2B, seguimiento de contratos	pb_clientes	Catálogo de clientes con estado de contrato	Nombre aerolínea, código IATA, contacto, tipo de servicio, fecha de inicio
Cu-T11: Configurar Suscripciones (E4)	Programación de entregas automáticas, filtros por cliente	pb_suscripciones	Listado de suscripciones con próxima fecha de entrega	Cliente, tipo de reporte, frecuencia, filtros aplicados, estado
Cu-T12: Gestionar Claves Api (E4)	Autenticación por clave, control de límite de consultas	pb_api_claves	Listado de claves activas por socio con métricas de uso	Nombre del socio, permisos, límite de consultas, expiración
Cu-T13: Configurar Webhooks (E4)	Webhooks HTTP, notificaciones automáticas por eventos	pb_api_webhooks	Listado de webhooks configurados y estado	URL del socio, eventos suscritos, clave de autenticación, estado activo
Tabla 18. Matriz de casos de uso tácticos de AeroTrack Analytics.
7.8 Matriz por casos de uso operativos
CASO DE USO	TÉCNICAS USADAS	MODELO FACT-DIM	REPORTES GENERADOS	REGISTROS USADOS
Cu-O01: Iniciar Sesión	Autenticación JWT, validación de credenciales, menú adaptativo por rol	pb_app_users, pb_roles, pb_permisos, pb_modulos	—	Email, contraseña, token generado, permisos del rol
Cu-O02: Cerrar Sesión	Invalidación de token, limpieza de sesión activa	pb_app_users	—	Token de sesión activa
Cu-O03: Ver Y Editar Perfil	Gestión de identidad, cambio de contraseña con verificación previa	pb_app_users	—	Nombre, email, rol, fecha de creación, contraseña enmascarada
Cu-O04: Ver Matriz De Permisos	Presentación visual de control de acceso en modo lectura	pb_roles, pb_permisos, pb_roles_permisos, pb_modulos	Matriz de permisos por rol y módulo (solo consulta)	Roles activos, módulos del sistema, acciones habilitadas
Cu-O05: Ejecutar Pipeline Manual	Orquestación de procesos, disparador vía API de Airflow	pb_vuelos_raw (origen) → fact_vuelo + 11 dims + 7 agg (destino)	Confirmación de inicio con ID de ejecución	2.000.000 registros de vuelo transformados al modelo estrella
Cu-O06: Monitorear Estado Del Dag	Monitoreo en tiempo real, actualización automática cada 10 segundos	Airflow API (estado por tarea: extract, load, transform, agg)	Panel de progreso con estado de cada etapa del proceso	Estado de cada tarea, tiempo transcurrido, porcentaje completado
Cu-O07: Consultar Historial	Consulta de registros históricos de ejecución de procesos	Airflow API (historial de ejecuciones)	Tabla de ejecuciones con fecha, duración y resultado	ID de ejecución, fecha, duración en minutos, estado, registros procesados
Cu-O08: Logs De Error Y Reintentar	Análisis de trazas de error, reintentos configurables	Airflow API (logs de tarea fallida)	Traza del error con detalle técnico y opción de reintento	Mensaje de error, tarea fallida, timestamp, número de intentos previos
Cu-O09: Ver Resumen Modelo Dimensional	Lectura de metadatos sin cargar el contenido del archivo	fact_vuelo + 11 dimensiones + 7 tablas de agregación	Panel con 12+ tarjetas con nombre, registros y tamaño por tabla	Nombre de tabla, número de filas, tamaño en MB, fecha de actualización
Cu-O10: Explorar Y Gestionar Registros	Paginación, búsqueda por columna, operaciones CRUD sobre el modelo	Cualquier tabla del modelo seleccionada por el administrador	Vista paginada de registros con búsqueda	Contenido de la tabla seleccionada según filtros y paginación aplicados
Cu-O11: Validar Integridad Del Modelo	Validación referencial, reglas de integridad del modelo estrella	fact_vuelo verificado contra todas las dimensiones	Reporte de integridad con resultado por tabla y registros afectados	Claves foráneas de fact_vuelo verificadas contra cada dimensión
Cu-O12: Ver Log De Auditoría	Consulta de registro inmutable con filtros múltiples	pb_auditoria (INSERT-only)	Tabla de registros filtrados de auditoría	Fecha, usuario, email, módulo, acción, recurso, resultado, IP
Cu-O13: Filtrar Y Exportar Auditoría	Filtrado de historial, exportación para análisis externo o compliance	pb_auditoria	Archivo CSV con registros filtrados por módulo, acción, usuario y período	Registros de auditoría según los filtros aplicados
Cu-O14: Narrativa Ia De Gráfico O Kpi	Modelos de lenguaje natural con caché, proveedor primario y fallback	KPIs calculados del módulo activo en las tablas de agregación	Párrafo ejecutivo en español en ventana modal sobre el gráfico	Indicadores del período activo enviados como contexto al modelo de lenguaje
Cu-O15: Generar Enlace De Demo 	Generación de tokens de acceso temporal con expiración configurable	pb_demo_tokens	Enlace de acceso con vigencia de 48 horas para enviar al prospecto	Nombre del prospecto, aerolínea, token, fecha y hora de expiración
Cu-O16: Ver Historial De Entregas	Registro y seguimiento de entregas programadas por cliente	pb_entregas_historial	Tabla de entregas con fecha, tipo y resultado por cliente	Cliente, tipo de reporte, fecha de envío, destinatario, estado de la entrega
Cu-O17: Acceder A Api Con Clave 	Autenticación por clave API, control de límite, endpoints REST versionados	Tablas de agregación según el endpoint consultado	Respuesta JSON con los indicadores analíticos solicitados	Clave API, parámetros de filtro, datos de la tabla de agregación correspondiente
Cu-O18: Ver Métricas De Uso De Api 	Análisis de registros de uso, métricas de consumo por socio	pb_api_logs	Panel con llamadas totales, endpoint más consultado y errores por socio	Clave API, endpoint, timestamp, resultado, latencia de respuesta
Tabla 19. Matriz de casos de uso operativos de AeroTrack Analytics.
7.9 Agregaciones usadas en el sistema
Las agregaciones son cálculos que resumen los registros de vuelo del dataset BTS/FAA en indicadores accionables para los módulos analíticos del sistema.
AGREGACIÓN	FÓRMULA O CÁLCULO	USO EN EL SISTEMA
Índice De Puntualidad (Otp)	COUNT(arr_delay ≤ 15) / COUNT(total_vuelos) × 100	Dashboard de KPIs, módulo de puntualidad, exportaciones
Retraso Promedio De Llegada	AVG(arr_delay) en vuelos con retraso positivo	Panel de indicadores, análisis por aerolínea y ruta
Tasa De Cancelación	COUNT(Cancelled = 1) / COUNT(total_vuelos) × 100	Dashboard, módulo de cancelaciones, alertas automáticas
Total De Vuelos Por Período	COUNT(pk_vuelo) GROUP BY year, month	Todos los módulos analíticos con filtros de período
Índice De Eficiencia De Ruta	(AVG(tiempo_real) – AVG(tiempo_programado)) / AVG(tiempo_programado) × 100	Módulo de rutas: ranking y gráfico de dispersión
Minutos De Retraso Por Causa	SUM(CarrierDelay, WeatherDelay, NASDelay, SecurityDelay, LateAircraftDelay) GROUP BY  erolín, month	Módulo de puntualidad: gráfico de dona de causas
Vuelos A Tiempo Por Aerolínea Y Mes	COUNT(arr_delay ≤ 15) GROUP BY  erolín, year, month	Tabla agg_otp_aerolinea_mes
Cancelaciones Por Causa Faa	COUNT(Cancelled=1) GROUP BY CancellationCode, year, month	Tabla agg_cancelaciones_causa
Porcentaje De Cancelaciones Por Categoría	COUNT(causa) / COUNT(total_vuelos) × 100	Módulo de cancelaciones: distribución por código A/B/C/D
Desvíos Por Ruta	COUNT(Diverted=1) GROUP BY origin, dest, alt_airport	Tabla agg_desvios_ruta
Retraso Promedio Por Desvío	AVG(DivArrDelay) GROUP BY origin, dest	Tabla de impacto de desvíos en módulo de cancelaciones
Otp Por Día De La Semana	COUNT(a_tiempo) / COUNT(total) × 100 GROUP BY DayOfWeek	Tabla agg_otp_dia_semana: gráfico semanal en puntualidad
Tabla 20. Agregaciones utilizadas en AeroTrack Analytics.
7.10 Técnicas de IA y Machine Learning aplicables
A. Predicción de puntualidad y cancelaciones (series de tiempo)
Objetivo: proyectar el comportamiento de los indicadores operacionales 3 a 6 meses hacia adelante.
ENTRADA DEL MODELO	SALIDA
Histórico Mensual De Otp Por Aerolínea (Mínimo 12 Meses)	Proyección de OTP para los próximos 3-6 meses con intervalo de confianza del 90%
Histórico Mensual De Tasa De Cancelación Por Causa Faa	Proyección de cancelaciones por período y categoría
Indicador Del Mes (Estacionalidad)	Meses de mayor riesgo operacional identificados automáticamente
Patrones Cíclicos Anuales Detectados En El Histórico	Componente estacional extraída para anticipar variaciones recurrentes
Tabla 21. Técnica de IA: predicción de puntualidad y cancelaciones (series de tiempo).
Casos de uso relacionados: CU-E14, CU-E15, CU-E16, CU-E17, CU-E21, CU-E22.
B. Detección de anomalías en indicadores clave
Objetivo: identificar aerolíneas, rutas o períodos con comportamiento fuera del rango esperado.
ANOMALÍA DETECTADA	POSIBLE CAUSA
Otp De Una Aerolínea Cae Más De 10 Puntos En Un Mes	Problema operacional interno o evento climático puntual
Tasa De Cancelación Supera El Umbral Configurado	Conflicto laboral, condiciones climáticas extremas o fallo de flota
Índice De Eficiencia De Una Ruta Se Deteriora Sostenidamente	Congestión aeroportuaria, cambios en slots o aumento de tráfico
Incremento Atípico De Desvíos En Una Ruta Específica	Condiciones meteorológicas recurrentes o problemas en el aeropuerto destino
Tabla 22. Técnica de IA: detección de anomalías en indicadores clave.
Casos de uso relacionados: CU-E02, CU-T05, CU-E20.
Nota: Esta técnica opera en dos contextos distintos: como comparación en tiempo real contra un umbral fijo configurado por el administrador (CU-E02, CU-T05), y como análisis estadístico retrospectivo sobre el histórico completo dentro del módulo predictivo (CU-E20).
C. Narrativa analítica automatizada con modelos de lenguaje
Objetivo: generar interpretaciones ejecutivas en español de los indicadores visualizados, sin intervención del analista.
ENTRADA DEL MODELO	SALIDA
Conjunto De 10 A 20 Kpis Calculados Del Módulo Activo	Párrafo ejecutivo de 3-4 oraciones en español
Filtros Activos (Período, Aerolínea, Ruta)	Narrativa contextualizada al alcance del análisis seleccionado
Identificación Del Módulo Analítico	Enfoque del párrafo adaptado (puntualidad, rutas, cancelaciones, etc.)
Tabla 23. Técnica de IA: narrativa analítica automatizada con modelos de lenguaje.
Casos de uso relacionados: CU-O14.
D. Asistente analítico conversacional (recuperación aumentada con IA)
Objetivo: responder preguntas en lenguaje natural sobre los datos del sistema sin requerir conocimiento técnico del analista.
ENTRADA DEL MODELO	SALIDA
Pregunta Del Analista En Lenguaje Natural	Respuesta en español con datos reales recuperados del modelo analítico
Contexto Recuperado De Las Tablas De Agregación Según La Pregunta	Fundamentación de la respuesta con los registros relevantes encontrados
Historial De La Conversación Activa	Coherencia y continuidad en respuestas de seguimiento
Tabla 24. Técnica de IA: asistente analítico conversacional (recuperación aumentada con IA).
Casos de uso relacionados: CU-E18, CU-T09.
E. Scoring de riesgo compuesto y simulación de escenarios
Objetivo: cuantificar el riesgo operacional relativo entre aerolíneas y permitir la exploración de escenarios hipotéticos sin afectar los datos reales del sistema.
ENTRADA DEL MODELO	SALIDA
Volatilidad Histórica Del Otp (Desviación Estándar)	Score compuesto de riesgo (0–100) por aerolínea
Tendencia Reciente (Pendiente De Los Últimos Períodos)	Categoría de riesgo (bajo / medio / alto / crítico) y tendencia (↑ / ↓ / estable)
Desempeño Promedio Histórico	— (insumo del cálculo del score)
Parámetros Del Simulador (Buffer De Conexión, % Reducción De Carga)	Proyección recalculada en tiempo real sobre el horizonte seleccionado
Tabla 25. Técnica de IA: scoring de riesgo compuesto y simulación de escenarios.
Casos de uso relacionados: CU-E21, CU-E22.
7.11 Relación entre registros operativos y reportes gerenciales
La siguiente cadena ilustra cómo los datos operacionales crudos del sector aéreo se transforman en inteligencia gerencial para las aerolíneas cliente de AeroTrack Analytics:
Registro operativo — Fuente
Datos BTS/FAA: 2.000.000 registros de vuelo con tiempos, retrasos,
cancelaciones, desvíos y atributos operacionales por aerolínea y ruta
↓
Proceso de actualización automatizado (Pipeline ELT)
Extracción concurrente desde staging → Transformación en modelo estrella
→ Carga en repositorio analítico → Generación de 7 tablas de indicadores precalculados
↓
Modelo Fact-Dim
fact_vuelo + 11 dimensiones + agg_otp_aerolinea_mes + agg_kpi_global_dia
+ agg_rutas_eficiencia + agg_cancelaciones_causa + agg_causas_retraso_mes
+ agg_otp_dia_semana + agg_desvios_ruta
↓
Reporte táctico o estratégico
Dashboard de KPIs con alertas · Análisis de puntualidad OTP · Evaluación de rutas
· Análisis de cancelaciones FAA · Informe ejecutivo PDF/Excel · Proyección predictiva
↓
Decisión
Plan de mejora operacional para la aerolínea cliente · Decisión de apertura o cierre de ruta
· Benchmarking frente a competidores · Planificación de tripulaciones y recursos
· Proyección de indicadores para el siguiente trimestre
7.12 Trazabilidad completa del sistema AeroTrack Analytics
La siguiente sección presenta la cadena de trazabilidad completa del sistema, mostrando para cada objetivo estratégico cómo se conectan los objetivos tácticos y operativos con los casos de uso implementados, el modelo de datos utilizado, las agregaciones aplicadas y las técnicas de inteligencia artificial o análisis involucrados.
OE-1: Penetración Digital y Adquisición Automatizada de Clientes Aeronáuticos
NIVEL	OBJETIVOS RELACIONADOS
Estratégico	OE-1: Captar aerolíneas como clientes mediante canales 100% digitales y entrega automatizada de inteligencia.
Táctico	OT-1.1: Captar clientes mediante demostraciones y reportes digitales · OT-1.2: Automatizar la configuración y seguimiento de entregas periódicas · OT-1.3: Generar y poner a disposición informes ejecutivos en múltiples formatos · OT-1.4: Medir la efectividad de la estrategia de captación digital
Operativo	OO-1.1.1: Registrar y gestionar clientes · OO-1.1.2: Generar enlace de acceso demo · OO-1.2.1: Configurar suscripciones · OO-1.2.2: Ver historial de entregas · OO-1.3.1 a OO-1.3.3: Exportar informes (PDF/Excel/CSV) · OO-1.4.1: Ver panel de captación
Tabla 26. OE-1 Penetración Digital y Adquisición de Clientes Aeronáuticos — trazabilidad general.



Casos de uso relacionados:
NIVEL	CASO DE USO
Estratégico	CU-E11 Exportar análisis a PDF · CU-E12 Exportar análisis a Excel · CU-E13 Exportar datos a CSV · CU-E19 Ver panel de captación
Táctico	CU-T10 Gestionar clientes aerolínea · CU-T11 Configurar suscripciones de reporte
Operativo	CU-O15 Generar enlace de demo · CU-O16 Ver historial de entregas automáticas
Tabla 27. OE-1 — Casos de uso relacionados.
Modelo Fact-Dim usado:
TIPO	TABLA
Hechos Atómica	fact_vuelo
Hechos Agregación	agg_otp_aerolinea_mes · agg_kpi_global_dia · agg_rutas_eficiencia · agg_cancelaciones_causa
Dimensiones	dim_tiempo · dim_aerolinea · dim_ruta
Operacional	pb_clientes · pb_suscripciones · pb_demo_tokens · pb_entregas_historial
Tabla 28. OE-1 — Modelo Fact-Dim usado.
Agregaciones aplicadas:
INDICADOR	CÁLCULO
Otp Global Del Período	COUNT(arr_delay ≤ 15) / COUNT(total) × 100
Retraso Promedio Para El Informe	AVG(arr_delay) GROUP BY  erolín, year, month
Tasa De Cancelación Del Cliente	COUNT(Cancelled=1) / COUNT(total) × 100
Top Rutas Problemáticas	ORDER BY otp_pct ASC LIMIT 10
Tabla 29. OE-1 — Agregaciones aplicadas.
Técnicas de IA/ML:
TÉCNICA	APLICACIÓN
Modelos De Lenguaje Natural	Narrativa ejecutiva automática incluida en cada informe PDF entregado al cliente
Generación De Documentos	Renderizado de informe PDF con secciones configurables y gráficos integrados
Reglas De Negocio	Expiración automática de accesos demo a las 48 horas de su generación
Tabla 30. OE-1 — Técnicas de IA/ML.

OE-2: Escalabilidad Comercial por Plataformas de Ecosistemas y APIs
NIVEL	OBJETIVOS RELACIONADOS
Estratégico	OE-2: Multiplicar el acceso al servicio analítico mediante interfaz de programación documentada y ecosistema de socios.
Táctico	OT-2.1: Exponer capacidades analíticas como servicio de programación · OT-2.2: Notificar al ecosistema de socios sobre la disponibilidad de datos · OT-2.3: Supervisar el consumo del servicio de programación por socios
Operativo	OO-2.1.1: Gestionar claves de acceso · OO-2.1.2: Acceder vía clave API · OO-2.2.1: Configurar webhooks · OO-2.3.1: Ver métricas de uso
Tabla 31. OE-2 Escalabilidad por APIs y Ecosistema de Socios — trazabilidad general.
Casos de uso relacionados:
NIVEL	CASO DE USO
Estratégico	— (OE-2 no tiene CU-E propio; es un objetivo de escalabilidad puramente táctico-operativo)
Táctico	CU-T12 Gestionar claves de acceso API · CU-T13 Configurar webhooks de notificación
Operativo	CU-O17 Acceder a análisis mediante clave API · CU-O18 Ver métricas de uso de la API
Tabla 32. OE-2 — Casos de uso relacionados.
Modelo Fact-Dim usado:
TIPO	TABLA
Hechos Agregación	agg_otp_aerolinea_mes · agg_rutas_eficiencia · agg_cancelaciones_causa · agg_kpi_global_dia
Operacional	pb_api_claves · pb_api_webhooks · pb_api_logs
Tabla 33. OE-2 — Modelo Fact-Dim usado.
Agregaciones aplicadas:
INDICADOR	CÁLCULO
Consultas De Api Por Socio	COUNT(llamadas) GROUP BY api_key, endpoint, period
Tasa De Disponibilidad De La Api	COUNT(respuestas exitosas) / COUNT(total llamadas) × 100
Tiempo De Respuesta Promedio	AVG(latencia_ms) GROUP BY endpoint
Tabla 34. OE-2 — Agregaciones aplicadas.
Técnicas de IA/ML:
TÉCNICA	APLICACIÓN
Autenticación Por Clave Con Límite De Tasa	Control de acceso programático diferenciado por socio y volumen de consultas
Webhooks Automáticos	Notificación inmediata a sistemas socios al completarse cada ciclo de actualización de datos
Tabla 35. OE-2 — Técnicas de IA/ML.



OE-3: Expansión Continua sobre Infraestructura en la Nube de Alta Disponibilidad
NIVEL	OBJETIVOS RELACIONADOS
Estratégico	OE-3: Garantizar disponibilidad continua del servicio mediante infraestructura escalable, segura y con trazabilidad completa.
Táctico	OT-3.1: Gestionar identidades y control de acceso seguro · OT-3.2: Automatizar y supervisar el ciclo de actualización del modelo analítico · OT-3.3: Garantizar la continuidad operativa mediante monitoreo proactivo · OT-3.4: Mantener trazabilidad y evidencia documental
Operativo	OO-3.1.1 a OO-3.1.4: Identidades y permisos · OO-3.2.1 a OO-3.2.5: Pipeline de actualización · OO-3.3.1 a OO-3.3.4: Monitoreo de infraestructura · OO-3.4.1, OO-3.4.2: Auditoría
Tabla 36. OE-3 Expansión Continua sobre Infraestructura en la Nube de Alta Disponibilidad — trazabilidad general.
Casos de uso relacionados:
NIVEL	CASO DE USO
Estratégico	— (la infraestructura soporta de forma transversal a todos los CU-E del sistema)
Táctico	CU-T01 Gestionar usuarios · CU-T02 Administrar roles · CU-T03 Ver configuración · CU-T04 Configurar correo · CU-T06 Configurar pipeline · CU-T07 Monitorear almacenamiento · CU-T08 Ver estado de servicios
Operativo	CU-O01 Iniciar sesión · CU-O02 Cerrar sesión · CU-O03 Ver perfil · CU-O04 Ver matriz de permisos · CU-O05 Ejecutar pipeline · CU-O06 Monitorear DAG · CU-O07 Historial de ejecuciones · CU-O08 Logs de error · CU-O12 Ver log de auditoría · CU-O13 Exportar auditoría
Tabla 37. OE-3 — Casos de uso relacionados.
Modelo Fact-Dim usado:
TIPO	TABLA
Operacional	pb_app_users · pb_roles · pb_permisos · pb_modulos · pb_configuracion_sistema · pb_auditoria
Staging	pb_vuelos_raw (fuente de ingesta del pipeline ELT)
Infraestructura	Contenedores Docker (FastAPI, PocketBase, MinIO, Airflow, PostgreSQL)
Tabla 38. OE-3 — Modelo Fact-Dim usado.
Agregaciones aplicadas:
INDICADOR	CÁLCULO
Disponibilidad Del Sistema (Uptime)	Tiempo disponible / Tiempo total × 100
Duración Promedio Del Pipeline	AVG(duracion_ejecucion_minutos)
Acciones Auditadas Por Período	COUNT(registros) GROUP BY modulo, mes
Tasa De Éxito Del Pipeline	COUNT(estado='exitoso') / COUNT(total_ejecuciones) × 100
Tabla 39. OE-3 — Agregaciones aplicadas.
Técnicas de IA/ML:
TÉCNICA	APLICACIÓN
Reglas De Negocio	Control de acceso por sesión activa y rol asignado en cada solicitud
Validaciones Automáticas	Integridad de tokens JWT, restricción de acceso a módulos no autorizados
Alertas Operativas	Notificación automática por correo al completarse o fallar el proceso de datos
Registro Transaccional Inmutable	Auditoría INSERT-only de toda acción realizada en el sistema
Tabla 40. OE-3 — Técnicas de IA/ML.



OE-4: Inteligencia de Negocio Centralizada para la Ventaja Competitiva Aeronáutica
NIVEL	OBJETIVOS RELACIONADOS
Estratégico	OE-4: Centralizar la inteligencia de negocio aeronáutica para sostener la ventaja competitiva de los clientes aerolínea.
Táctico	OT-4.1: Garantizar integridad del modelo analítico · OT-4.2: Proveer visibilidad ejecutiva de KPIs con alertas · OT-4.3: Analizar puntualidad OTP comparativa · OT-4.4: Evaluar rendimiento de rutas · OT-4.5: Analizar cancelaciones y desvíos · OT-4.6: Generar narrativa automática · OT-4.7: Proveer proyecciones predictivas · OT-4.8: Permitir consultas en lenguaje natural · OT-4.9: Detectar anomalías y simular escenarios de riesgo
Operativo	OO-4.1.1 a OO-4.1.3: Integridad del modelo · OO-4.2.1 a OO-4.2.3: Dashboard y alertas · OO-4.3.1 a OO-4.3.3: Puntualidad · OO-4.4.1, OO-4.4.2: Rutas · OO-4.5.1 a OO-4.5.3: Cancelaciones y desvíos · OO-4.6.1, OO-4.6.2: Narrativa IA · OO-4.7.1 a OO-4.7.3: Predictivo · OO-4.8.1: Asistente conversacional · OO-4.9.1 a OO-4.9.4: Recomendaciones, anomalías, riesgo y simulación
Tabla 41. OE-4 Inteligencia de Negocio Centralizada para Ventaja Competitiva — trazabilidad general.
Casos de uso relacionados:
NIVEL	CASO DE USO
Estratégico	CU-E01 Dashboard KPIs · CU-E02 Alertas · CU-E03 OTP por aerolínea · CU-E04 Comparar rutas · CU-E05 Tendencias · CU-E06 Rendimiento rutas · CU-E07 Tiempo real vs programado · CU-E08 Cancelaciones FAA · CU-E09 Desvíos · CU-E10 Tendencia cancelaciones · CU-E14 Proyección predictiva · CU-E15 Patrones estacionales · CU-E16 Recomendaciones · CU-E17 Informe IA · CU-E18 Asistente conversacional · CU-E20 Anomalías históricas · CU-E21 Índice de riesgo por aerolínea · CU-E22 Simulador what-if
Táctico	CU-T05 Configurar umbrales · CU-T09 Configurar asistente IA
Operativo	CU-O09 Ver modelo · CU-O10 Explorar registros · CU-O11 Validar integridad · CU-O14 Narrativa IA por gráfico
Tabla 42. OE-4 — Casos de uso relacionados.
Modelo Fact-Dim usado:
Tipo	TABLA
Hechos Atómica	fact_vuelo (2.000.000 registros · 1 registro por vuelo)
Hechos Agregación	agg_otp_aerolinea_mes · agg_kpi_global_dia · agg_rutas_eficiencia · agg_cancelaciones_causa · agg_causas_retraso_mes · agg_otp_dia_semana · agg_desvios_ruta
Dimensiones	dim_tiempo · dim_aerolinea · dim_aeropuerto · dim_avion · dim_retraso_causa · dim_cancelacion · dim_distancia · dim_desvio · dim_horario · dim_clasificacion_retraso · dim_ruta
Tabla 43. OE-4 — Modelo Fact-Dim usado.
Nota: El pipeline orquestado en OE-3 (OT-3.2) transforma pb_vuelos_raw hacia el modelo dimensional aquí descrito; OE-4 consume estas tablas para fines exclusivamente analíticos.
Agregaciones aplicadas:
INDICADOR	CÁLCULO
Otp Global Y Por Aerolínea	COUNT(arr_delay ≤ 15) / COUNT(total) × 100 GROUP BY carrier, year, month
Retraso Promedio	AVG(arr_delay) GROUP BY carrier, origin, dest
Eficiencia De Ruta	(AVG(tiempo_real) − AVG(tiempo_prog)) / AVG(tiempo_prog) × 100
Distribución De Causas	SUM(CarrierDelay, WeatherDelay, NASDelay, SecurityDelay, LateAircraftDelay)
Cancelaciones Por Causa Faa	COUNT(Cancelled=1) GROUP BY CancellationCode, year, month
Desvíos Por Ruta	COUNT(Diverted=1) GROUP BY origin, dest, alt_airport
Otp Por Día De Semana	COUNT(a_tiempo) / COUNT(total) × 100 GROUP BY DayOfWeek
Kpis Diarios Globales	OTP, AVG(retraso), COUNT(cancelados), COUNT(desviados) GROUP BY date
Tabla 44. OE-4 — Agregaciones aplicadas.

Técnicas de IA/ML:
TÉCNICA	APLICACIÓN
Business Intelligence Y Agregaciones	Todos los módulos analíticos: dashboard, puntualidad, rutas, cancelaciones
Benchmarking Competitivo	CU-E04: comparativa de aerolíneas en rutas compartidas con doble eje
Predicción Con Series De Tiempo (Prophet)	CU-E14 y CU-E15: proyección de OTP y cancelaciones 3-6 meses con estacionalidad
Detección De Anomalías	CU-E02: alertas automáticas por cruce de umbrales configurados
Modelos De Lenguaje Natural — Narrativa	CU-O14: párrafo ejecutivo por gráfico o KPI en todos los módulos de E2
Recuperación Aumentada Con Ia (Rag)	CU-E18: asistente analítico conversacional con contexto del modelo analítico
Tabla 45. OE-4 — Técnicas de IA/ML.

7.13 Resumen final por nivel
NIVEL	CASOS DE USO IMPLEMENTADOS	TÉCNICAS APLICADAS	RESULTADO ESPERADO
Estratégico	CU-E01 a CU-E19 · 19 casos de uso · E2, E3 y E4	Business Intelligence, agregaciones, benchmarking competitivo, predicción con series de tiempo, narrativa con modelos de lenguaje, asistente conversacional RAG	Inteligencia operacional accionable para aerolíneas cliente: rankings de puntualidad, análisis de cancelaciones, evaluación de rutas, proyecciones a 6 meses e informes ejecutivos listos para presentación
Táctico	CU-T01 a CU-T13 · 13 casos de uso · E1, E2 y E4	Configuración de alertas dinámicas, monitoreo de infraestructura, control de acceso RBAC, orquestación de procesos automatizados, gestión de socios tecnológicos	Sistema configurado y operativo para el equipo de AeroTrack sin necesidad de intervención técnica; alertas activas, pipeline programado y socios integrados
Operativo	CU-O01 a CU-O18 · 18 casos de uso · E1, E2, E3 y E4	Reglas de negocio, validaciones automáticas, registro transaccional inmutable, extracción paralela de datos, narrativa IA por gráfico, control de acceso por sesión	Ejecución eficiente de tareas diarias: análisis actualizados en menos de 3 segundos, pipeline ejecutado con alta disponibilidad y trazabilidad completa de todas las acciones del sistema
Tabla 46. Resumen final de AeroTrack Analytics por nivel organizacional.



8. Técnicas de Inteligencia Artificial y Aprendizaje Automático
AeroTrack Analytics incorpora técnicas de inteligencia artificial en tres módulos del sistema, cada uno con una función diferenciada que amplía el valor de la inteligencia entregada a los clientes más allá del análisis histórico descriptivo.
8.1 Narrativa Analítica Automatizada por Gráfico e Indicador
El módulo de narrativa analítica aplica modelos de lenguaje natural para generar interpretaciones ejecutivas específicas de cada gráfico o indicador clave que el analista visualiza en los módulos de análisis de la segunda entrega del sistema. Al hacer clic en el botón de narrativa asociado a un gráfico o KPI, el sistema envía al modelo de lenguaje los indicadores calculados de ese elemento específico y recibe como respuesta un párrafo ejecutivo en español que aparece en una ventana emergente sin interrumpir el flujo de análisis.
Entrada del modelo. Conjunto de indicadores cuantitativos del gráfico o KPI seleccionado, calculados por el motor analítico para el período y filtros activos en ese momento.
Salida del modelo. Un párrafo de tres a cuatro oraciones en español con estructura ejecutiva: hallazgo principal, causa probable, impacto operacional y recomendación accionable para ese indicador específico.
Esquema de resiliencia. El sistema opera con un proveedor de lenguaje principal y un proveedor de respaldo, ambos configurables desde el panel de administración. Si el proveedor principal no está disponible, el sistema conmuta automáticamente al proveedor de respaldo sin interrupción del servicio. Los resultados se almacenan en caché por un período configurable para evitar consultas repetidas ante datos idénticos.
Caso de uso relacionado. CU-O14: Consultar narrativa IA de un gráfico o KPI. CU-T09: Configurar proveedor de inteligencia artificial.
8.2 Módulo de Predicción con Series de Tiempo
El módulo predictivo, disponible a partir de la tercera entrega del sistema, aplica modelos de análisis de series de tiempo sobre el histórico de puntualidad y cancelaciones para generar proyecciones a tres y seis meses. El modelo identifica tendencias, estacionalidad y patrones cíclicos en los datos históricos para estimar el comportamiento futuro de los indicadores operacionales con intervalos de confianza cuantificados.
Entrada del modelo. Serie de tiempo mensual del índice de puntualidad y la tasa de cancelación por aerolínea y ruta, construida a partir del modelo analítico histórico con un mínimo de doce meses de datos.
Salida del modelo. Proyección del índice de puntualidad y tasa de cancelación para los próximos tres a seis meses, con intervalo de confianza del noventa por ciento, identificación de meses de riesgo elevado y recomendaciones operacionales priorizadas según el nivel de riesgo proyectado.
Casos de uso relacionados. CU-E14: Generar proyección de riesgo operacional. CU-E15: Analizar patrones estacionales. CU-E16: Ver recomendaciones automáticas priorizadas. CU-E17: Exportar informe ejecutivo IA.
8.3 Asistente Analítico Conversacional
El asistente analítico conversacional, disponible a partir de la tercera entrega, permite al analista realizar consultas en lenguaje natural sobre los datos del sistema. El asistente emplea una arquitectura de generación aumentada por recuperación (RAG), en la que el modelo de lenguaje combina su capacidad generativa con información recuperada directamente del modelo analítico para responder preguntas específicas sobre los datos de vuelo.
Entrada del modelo. Pregunta del analista en lenguaje natural, junto con el contexto relevante recuperado de las tablas de indicadores del modelo analítico que corresponde a la consulta formulada.
Salida del modelo. Respuesta en lenguaje natural en español con la información solicitada, fundamentada en los datos reales del sistema y con indicación de las fuentes de información utilizadas para elaborar la respuesta.
Casos de uso relacionados. CU-E18: Consultar asistente analítico conversacional con inteligencia artificial. CU-T09: Configurar proveedor de inteligencia artificial.
9. Calidad del Sistema
[Sección pendiente de completar: análisis de calidad del sistema según ISO/IEC 25010 — características de adecuación funcional, eficiencia de desempeño, compatibilidad, usabilidad, fiabilidad, seguridad, mantenibilidad y portabilidad]
10. Conclusiones
[Sección pendiente de completar: conclusiones del análisis empresarial y del sistema]
11. Referencias Bibliográficas
[1] Bureau of Transportation Statistics. (2025). Reporting Carrier On-Time Performance (1987 – present). TranStats – U.S. Department of Transportation. https://www.transtats.bts.gov/ontime/
[2] Bureau of Transportation Statistics. (2025). Airline On-Time Tables. U.S. Department of Transportation. https://www.bts.gov/explore-topics-and-geography/topics/airlines-and-airports/airline-time-tables
[3] Kimball, R., & Ross, M. (2013). The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling (3.ª ed.). John Wiley & Sons.
[4] International Civil Aviation Organization (ICAO). (2023). Annual Report of the Council 2022: The World of Air Transport in 2022. ICAO. https://www.icao.int/world-air-transport-2023

