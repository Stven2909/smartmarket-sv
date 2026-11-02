# SmartMarket SV — Visión de Negocio

> **Documento base para la materia de Emprendedurismo.** Está escrito en lenguaje de negocio:
> problema, contexto, propuesta de valor, modelo de negocio, impacto social y roadmap. Los detalles
> técnicos viven en `02-arquitectura.md` y en el resto de la documentación del repositorio.
>
> **Nota sobre cifras:** las cifras macroeconómicas citadas provienen del levantamiento usado en el
> anteproyecto y deben conservar su fuente oficial en la versión final que se entregue al docente.
> No se incluyen proyecciones financieras ni datos de mercado que el equipo no haya verificado.

---

## 1. Resumen ejecutivo

SmartMarket SV es una plataforma web instalable (PWA) que ayuda a las familias salvadoreñas a
planificar su compra de supermercado con información comparable y neutral: precios, promociones,
disponibilidad y ubicación de sucursales. A partir de una lista de compras y un presupuesto, el
sistema calcula la alternativa que mejor equilibra costo, distancia y tiempo, y un Sistema Experto
explica la recomendación en lenguaje sencillo.

El problema que atiende es concreto: el costo de la Canasta Básica Alimentaria ha subido de forma
sostenida —de alrededor de **$200 en 2019 a más de $256 en 2026**— mientras la información de
precios sigue dispersa entre sitios web, volantes, grupos de mensajería y visitas físicas. Esa
asimetría de información castiga especialmente a los hogares que compran al día y no pueden
absorber variaciones de precio.

La propuesta no es "otro supermercado en línea", sino una **capa neutral de decisión** entre el
consumidor y las cadenas. El MVP ya está construido y verificado: catálogo, buscador, listas,
comparador, optimización, promociones, historial de precios, panel administrativo, PWA y chat
explicativo. El siguiente paso es ampliar cobertura y validar el modelo con usuarios reales.

---

## 2. El problema

### 2.1 Contexto económico

El Salvador es una economía dolarizada, con alta dependencia de remesas y con un consumo de
supermercado concentrado en pocas cadenas. En ese contexto, el precio de los alimentos es uno de
los gastos que más presiona el presupuesto familiar. La Canasta Básica Alimentaria (CBA) es la
referencia oficial para medir ese costo: si sube más rápido que el ingreso del hogar, la familia
debe recortar cantidad, calidad o ambas.

La cifra de referencia del anteproyecto —**~$200 en 2019 y más de $256 en 2026**— resume una
tendencia, no un dato aislado: el encarecimiento acumulado obliga a comparar mejor cada compra.
Sin embargo, comparar bien es precisamente lo que el mercado no facilita.

### 2.2 La brecha de información

Una familia que quiere ahorrar hoy enfrenta cinco fricciones:

1. **Precios dispersos.** Cada cadena publica precios en su propio sitio, con formatos, vigencias y
   niveles de detalle distintos. No existe un comparador local que los unifique.
2. **Promociones difíciles de verificar.** Las ofertas cambian por sucursal y por semana; el
   consumidor se entera tarde o no se entera.
3. **Costo oculto del recorrido.** El supermercado más barato puede estar lejos. Sin calcular
   distancia y tiempo, el "ahorro" se consume en transporte.
4. **Presupuesto sin herramienta.** Planificar una lista con un monto límite se hace de memoria o
   en una hoja de cálculo, sin saber si alcanza antes de llegar a la caja.
5. **Explicaciones ausentes.** Los comparadores suelen mostrar un ranking sin decir *por qué* una
   opción es mejor para ese hogar en particular.

### 2.3 A quién afecta

El impacto no es homogéneo:

- **Hogares de ingresos bajos y medios:** compran con presupuesto ajustado y tienen menos margen
  para equivocarse.
- **Familias con personas dependientes:** la lista incluye productos esenciales que no se pueden
  sustituir libremente.
- **Personas sin auto:** la distancia y el tiempo pesan más que el precio nominal.
- **Estudiantes y personas que viven solas:** compran en volúmenes pequeños y con alta frecuencia.

La plataforma prioriza a estos perfiles, no al consumidor de conveniencia que ya tiene tiempo y
transporte para recorrer varias tiendas.

---

## 3. Contexto y oportunidad

### 3.1 Mercado local

El mercado de supermercados salvadoreño está dominado por unas pocas cadenas con presencia
nacional y por formatos de descuento. Esa concentración tiene dos caras:

- **Ventaja para el proyecto:** un número manejable de fuentes permite construir un catálogo
  comparable con esfuerzo razonable.
- **Riesgo:** cualquier dependencia excesiva de una sola cadena o de una sola fuente de datos
  vuelve frágil la propuesta.

Por eso la arquitectura trata las fuentes de precios como **intercambiables** y mantiene la carga
manual como respaldo. El sistema no depende de que un sitio permita automatización.

### 3.2 Digitalización

La penetración de teléfonos inteligentes y la familiaridad con aplicaciones de mensajería hacen
viable una solución móvil. Una PWA —instalable desde el navegador, sin tienda de aplicaciones—
reduce la barrera de entrada: no exige descargar un APK ni pagar por distribución, y funciona en
Android, iOS y escritorio con una sola base de código.

### 3.3 Por qué ahora

Tres condiciones convergen:

1. El costo de los alimentos sigue siendo un tema de conversación cotidiano.
2. Las cadenas ya publican parte de su catálogo en línea, lo que hace posible comparar.
3. Las herramientas de desarrollo web permiten construir y mantener una PWA con un equipo pequeño.

La oportunidad no está en inventar el comercio electrónico, sino en **ordenar información que ya
existe y traducirla en una decisión de compra**.

---

## 4. Revisión de literatura y casos de referencia

### 4.1 Aportes conceptuales

- **Herbert Simon — racionalidad limitada.** El consumidor no optimiza con información perfecta;
  decide con el tiempo, la atención y los datos que tiene a mano. SmartMarket SV reduce ese costo
  de búsqueda y presenta una alternativa "suficientemente buena" en lugar de exigir que la persona
  compare manualmente decenas de precios.
- **Philip Kotler — propuesta de valor y segmentación.** El valor no es el precio más bajo, sino la
  combinación de beneficios que el cliente percibe. La plataforma segmenta por presupuesto,
  movilidad y composición del hogar, y comunica un beneficio claro: *comprar mejor con la
  información que ya existe*.
- **Kaoru Ishikawa — análisis de causas.** El diagrama causa-efecto permite separar síntomas
  ("todo está caro") de causas manejables (información dispersa, promociones opacas, distancia no
  considerada, falta de planificación). El producto ataca las causas, no solo el síntoma.

### 4.2 Casos internacionales

| Referencia | País | Qué hace | Lección para SmartMarket SV |
|---|---|---|---|
| **Carriapp** | Chile | Comparación de precios y promociones entre supermercados. | El valor está en la comparación neutral y en la actualización frecuente. |
| **Tu-Alacena** | Argentina | Comparador de precios de la canasta familiar. | La cercanía al lenguaje del hogar y la lista de compras son claves de adopción. |
| **FindIt / OCU Market** | España | Comparación de precios con respaldo de una organización de consumidores. | La credibilidad y la transparencia metodológica sostienen la confianza. |

Ninguno de estos casos opera en El Salvador con la combinación de **precio + promoción + distancia
+ presupuesto + explicación**. Esa es la brecha que el proyecto busca ocupar.

### 4.3 Lecciones de los casos

1. La comparación debe ser **neutral**: el ranking no se vende.
2. La información debe ser **fresca y trazable**: el usuario necesita saber cuándo se actualizó.
3. La experiencia debe ser **simple**: una lista, un presupuesto y una recomendación.
4. La confianza se construye **explicando**: no basta con mostrar un número.

---

## 5. Análisis de causas raíz

Resumen del diagrama de Ishikawa aplicado al problema ("la familia no logra optimizar su compra"):

| Categoría | Causa identificada | Respuesta del producto |
|---|---|---|
| **Información** | Precios dispersos y en formatos distintos. | Catálogo maestro + normalización + comparador. |
| **Información** | Promociones poco visibles o de vigencia confusa. | Módulo de promociones con precio normal vs. final y fecha de actualización. |
| **Proceso** | La lista se hace de memoria y sin presupuesto. | Lista de compras con presupuesto y productos esenciales/opcionales. |
| **Proceso** | No se evalúa el costo del recorrido. | Score que combina costo, distancia y tiempo. |
| **Personas** | Falta de tiempo para comparar. | Recomendación automática y explicada. |
| **Personas** | Desconfianza en rankings pagados. | Neutralidad declarada y criterio transparente. |
| **Tecnología** | Herramientas existentes no cubren El Salvador. | PWA local, sin dependencia de una tienda. |
| **Entorno** | Fuentes de datos restringidas o cambiantes. | Pipeline desacoplado y carga manual de respaldo. |

---

## 6. Propuesta de valor

### 6.1 Para las familias

> **"Hacé tu lista, poné tu presupuesto y te decimos dónde conviene comprar —con el porqué."**

Beneficios concretos:

- **Ahorro real, no teórico:** el cálculo incluye el costo del recorrido, no solo el precio del
  producto.
- **Decisión en segundos:** una recomendación clara (EXCELENTE / BUENA / NO_RECOMENDABLE) en lugar
  de una tabla que hay que interpretar.
- **Presupuesto respetado:** el sistema indica si la lista cabe en el monto disponible.
- **Explicabilidad:** el Sistema Experto justifica la recomendación con reglas comprensibles.
- **Neutralidad:** ninguna cadena paga por aparecer primero.

### 6.2 Para el ecosistema

- **Para supermercados:** un canal adicional de visibilidad para promociones, sin costo de
  intermediación por venta en el MVP.
- **Para organizaciones de consumidores:** una base metodológica replicable para monitoreo de
  precios.
- **Para la academia:** un caso aplicado de sistemas expertos, optimización y datos abiertos.

### 6.3 Diferenciadores

1. **Local:** diseñado para el mercado salvadoreño, no adaptado de otro país.
2. **Integral:** precio, promoción, distancia, tiempo y presupuesto en una sola decisión.
3. **Explicable:** no es una caja negra; muestra las reglas que sustentan la recomendación.
4. **Resiliente:** sigue funcionando si una fuente de datos o el Sistema Experto falla.
5. **Instalable:** PWA sin tienda de aplicaciones.

---

## 7. Segmento objetivo

### 7.1 Segmento primario

Hogares urbanos de ingresos bajos y medios, con acceso a smartphone, que compran en supermercado
al menos una vez por semana y administran un presupuesto ajustado. Dentro de este segmento se
priorizan:

- Familias con niños o personas dependientes.
- Personas sin vehículo propio.
- Hogares que ya usan WhatsApp o redes sociales para comparar precios.

### 7.2 Segmento secundario

- Estudiantes y profesionales que viven solos.
- Personas mayores con movilidad reducida.
- Organizaciones que asesoran a consumidores.

### 7.3 Perfil de exclusión (por ahora)

El MVP no está pensado para compras mayoristas, restaurantes ni clientes corporativos. Tampoco
para municipios sin cobertura de las cadenas cargadas en el catálogo.

---

## 8. Modelo de negocio

### 8.1 Lienzo resumido

| Bloque | Definición |
|---|---|
| **Propuesta de valor** | Comparar, planificar y decidir la compra de supermercado con una recomendación neutral y explicada. |
| **Segmentos** | Hogares urbanos de ingresos bajos/medios; estudiantes; organizaciones de consumidores. |
| **Canales** | PWA instalable, redes sociales, alianzas con organizaciones locales, voz a voz. |
| **Relación** | Autoservicio con soporte comunitario; contenido educativo sobre precios y presupuesto. |
| **Recursos clave** | Catálogo normalizado, historial de precios, motor de optimización, Sistema Experto, equipo pequeño. |
| **Actividades clave** | Actualización de precios, curaduría de catálogo, mantenimiento de reglas, soporte y difusión. |
| **Aliados clave** | Supermercados (fuente de datos), universidades, organizaciones de consumidores, proveedores de hosting. |
| **Estructura de costos** | Hosting del Sistema Experto, base de datos, desarrollo y mantenimiento, validación legal de fuentes. |
| **Fuentes de ingreso** | A validar: freemium, informes agregados B2B y convenios no intrusivos. |

### 8.2 Modelo de ingresos propuesto (a validar)

El MVP **no monetiza** todavía. La prioridad es demostrar utilidad y confianza. Las líneas a
validar después de la entrega son:

1. **Freemium responsable.** Gratis: comparación, lista, presupuesto y recomendación básica.
   Premium: alertas de precio, historial extendido, listas compartidas y optimización multi-sucursal.
2. **Informes agregados y anonimizados.** Tendencias de precio por categoría para supermercados,
   marcas u organizaciones. Nunca se venden datos personales ni listas identificables.
3. **Convenios y patrocinios transparentes.** Contenido patrocinado claramente etiquetado, sin
   alterar el ranking ni la recomendación.

**Regla de neutralidad:** ningún ingreso puede comprar una mejor posición en el comparador ni en la
recomendación del Sistema Experto. Si esa regla se rompe, se pierde la propuesta de valor.

### 8.3 Estructura de costos

- Hosting del servicio experto (Render) y de la base de datos.
- Mantenimiento del pipeline de precios y curaduría del catálogo.
- Desarrollo y soporte del frontend/PWA.
- Validación legal de las fuentes automatizadas.
- Difusión y alianzas comunitarias.

### 8.4 Sostenibilidad

El proyecto se plantea como **emprendimiento social**: debe cubrir sus costos sin comprometer la
neutralidad. Un modelo freemium con ingresos B2B agregados es más coherente con ese objetivo que
la publicidad masiva o la venta de posiciones.

---

## 9. Impacto social

### 9.1 Impacto directo

- **Ahorro familiar:** la comparación incluye el costo del recorrido, lo que evita "ahorros" que se
  pierden en transporte.
- **Mejor uso del presupuesto:** la lista con monto límite ayuda a llegar a la caja sin sorpresas.
- **Acceso a información:** personas sin tiempo o sin transporte obtienen el mismo análisis que
  alguien que puede recorrer varias tiendas.
- **Educación financiera práctica:** el chat explicativo y las reglas visibles enseñan *por qué*
  una compra conviene.

### 9.2 Alineación con los ODS

| ODS | Contribución |
|---|---|
| **ODS 1 — Fin de la pobreza** | Mejora la eficiencia del gasto familiar en alimentos. |
| **ODS 2 — Hambre cero** | Facilita el acceso a una canasta básica más asequible. |
| **ODS 8 — Trabajo decente y crecimiento económico** | Profesionaliza la información de precios y crea capacidades locales. |
| **ODS 12 — Producción y consumo responsables** | Reduce recorridos innecesarios y promueve decisiones de compra más conscientes. |

### 9.3 Impacto indirecto

- **Transparencia de mercado:** precios comparables presionan a la baja las diferencias injustificadas.
- **Datos para políticas públicas:** el historial agregado puede alimentar análisis de inflación
  local, siempre con salvaguardas de privacidad.
- **Formación de talento:** el equipo practica desarrollo full-stack, ciencia de datos y sistemas
  expertos en un problema real.

---

## 10. Métricas de éxito

### 10.1 Producto

| Métrica | Qué mide | Meta inicial |
|---|---|---|
| Listas creadas por semana | Uso real de la función central. | Validar con piloto. |
| Optimizaciones ejecutadas | Uso del motor de decisión. | Validar con piloto. |
| Ahorro promedio por lista | Valor percibido. | Reportar, no prometer. |
| Recomendaciones aceptadas | Utilidad de la sugerencia. | Validar con piloto. |
| Cobertura de catálogo | Productos con precio en ≥2 cadenas. | Crecer de forma sostenida. |
| Frescura de precios | Antigüedad del último dato. | Definir umbral por fuente. |

### 10.2 Técnicas

| Métrica | Meta |
|---|---|
| Disponibilidad del Sistema Experto | ≥ 99 % en horario de demo. |
| Latencia de `/recommend` | Bajo 1 s en caliente; fallback si supera el timeout. |
| Pruebas de backend | 100 % en verde (hoy: 123 pruebas). |
| Build/lint de frontend | Sin errores (hoy: build OK, 1 warning de Fast Refresh). |
| Cobertura de fuentes | Al menos dos fuentes activas + carga manual. |

### 10.3 Sociales

- Porcentaje de usuarios que reportan haber ahorrado.
- Hogares que usan la lista con presupuesto de forma recurrente.
- Organizaciones aliadas que replican el monitoreo de precios.

---

## 11. Riesgos y mitigación

| Riesgo | Impacto | Mitigación |
|---|---|---|
| **Datos desactualizados** | La recomendación pierde valor y confianza. | Fecha de actualización visible, pipeline con validación y carga manual de respaldo. |
| **Restricciones legales de las fuentes** | Una cadena puede prohibir la extracción. | Alcance acotado, respeto de `robots.txt`, UA identificable, pausas y apagado por configuración. |
| **Dependencia de una sola cadena** | Cobertura frágil. | Fuentes intercambiables y catálogo mínimo con varias cadenas. |
| **Baja adopción** | El producto no se usa. | Piloto con usuarios reales, alianzas comunitarias y onboarding simple. |
| **Monetización prematura** | Se compromete la neutralidad. | No monetizar en el MVP; validar freemium/B2B después. |
| **Cold start del experto** | La demo se siente lenta. | Fallback local, timeout controlado y precalentamiento antes de la defensa. |
| **Privacidad** | Uso indebido de listas o ubicación. | Datos mínimos, consentimiento explícito y agregación para informes. |
| **Equipo pequeño y tiempo limitado** | No se cubre todo el roadmap. | Priorizar MVP y deuda técnica documentada; no prometer funciones no construidas. |

---

## 12. Roadmap de evolución

### V1 — MVP (construido)

- Catálogo maestro, buscador y categorías.
- Listas de compra con presupuesto y productos esenciales/opcionales.
- Comparador y Motor de Optimización con score configurable.
- Promociones e historial de precios con gráficas.
- Sistema Experto con explicación y chat.
- Pipeline de precios con staging y validación.
- PWA instalable, autenticación y panel administrativo.
- CI con pruebas de backend y lint/build de frontend.

### V2 — Validación y cobertura

- Vista de mapa de sucursales.
- Enlaces directos a cada vista y mejor navegación.
- Pruebas de frontend y ampliación de pruebas de API.
- Alertas de precio y listas compartidas.
- Más fuentes de precios y cobertura nacional.
- Piloto con usuarios y medición de ahorro.

### V3 — Escala

- Aplicación móvil nativa (si la PWA no alcanza).
- Programa de fidelización y convenios.
- Informes B2B agregados.
- Expansión a otros mercados de Centroamérica con el mismo modelo.

---

## 13. Conclusión

SmartMarket SV no compite por tener el precio más bajo ni por vender más productos. Compite por
**reducir el costo de decidir**. En un mercado donde la información está dispersa y el presupuesto
familiar es ajustado, ordenar esa información y explicar la mejor alternativa es un valor real,
medible y socialmente relevante.

El MVP demuestra que la propuesta es construible con un equipo pequeño: ya existen catálogo,
comparador, optimización, promociones, historial, PWA y un Sistema Experto que explica sus
recomendaciones. Lo que sigue no es "hacer más pantallas", sino **validar con usuarios, ampliar
cobertura y sostener la neutralidad** —las tres condiciones para que el proyecto pase de prototipo
académico a emprendimiento viable.

---

## 14. Nota sobre fuentes y cifras

Este documento usa como referencia la cifra de Canasta Básica Alimentaria registrada en
`00-contexto-proyecto.md` (**~$200 en 2019 → más de $256 en 2026**). Para la entrega formal se debe
adjuntar la cita completa de la institución que publica el dato y la fecha de consulta. Las demás
cifras del documento son metas internas del equipo o resultados del MVP, no proyecciones de
mercado.

Los casos internacionales (Carriapp, Tu-Alacena, FindIt/OCU Market) se citan como referencia
conceptual; no se usan cifras de esos servicios porque el equipo no las verificó.
