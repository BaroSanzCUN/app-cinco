# Guia Para Incluir Nueva Tabla Y Nuevo Agente Empresarial

## Objetivo

Esta guia explica, paso a paso, como integrar una nueva tabla de negocio al sistema IA
y como decidir si esa tabla:

- vive dentro de un dominio/agente existente
- o requiere un dominio/agente nuevo

Tambien explica como relacionarla con `empleados` u otro dominio ya existente para
consultas cruzadas, agrupaciones, joins y razonamiento multiagente empresarial.

La guia esta alineada con la arquitectura actual del proyecto:

- `ai_dictionary` como fuente estructurada
- `YAML` por dominio como fuente semantica versionada
- `planner/query intelligence` como capa deterministica
- `OpenAI` como capa de desambiguacion final
- memoria de patrones satisfactorios como acelerador de consultas repetidas

## Regla General De Diseño

Antes de crear nada, responde esta pregunta:

### Caso A. Solo nueva tabla dentro de un dominio existente

Usa esta opcion cuando la nueva tabla:

- pertenece al mismo proceso de negocio
- comparte vocabulario principal
- comparte filtros o dimensiones base
- solo necesita joins con tablas ya conocidas

Ejemplos:

- una tabla nueva de novedades de personal que sigue siendo parte de `empleados`
- una tabla nueva de detalle de ausentismos que sigue siendo parte de `ausentismo`

### Caso B. Nuevo dominio y nuevo agente

Usa esta opcion cuando la nueva tabla:

- representa un proceso distinto
- tiene reglas de negocio propias
- requiere vocabulario operativo diferente
- necesita capacidades y respuestas propias

Ejemplos:

- `inventario_red`
- `cuadrillas`
- `tickets_servicio`
- `clientes`

## Decidir Si Va Con Empleados O Se Relaciona Con Empleados

Si la nueva tabla tiene una clave como:

- `cedula`
- `id_empleado`
- `codigo_sap`
- `supervisor`

entonces normalmente no debe duplicar atributos de personal como:

- `area`
- `cargo`
- `tipo_labor`
- `carpeta`
- `sede`

En lugar de eso:

1. La tabla nueva guarda su hecho de negocio.
2. `empleados` sigue siendo el maestro de personal.
3. El sistema resuelve dimensiones de personal por join controlado.

Ese es el patron correcto para consultas como:

- `ausentismos por cargo`
- `viaticos por area`
- `ordenes por supervisor`
- `tickets de empleados operativos por sede`

## Estructura Oficial En El Repositorio

Todo dominio debe vivir en:

`backend/apps/ia_dev/domains/<dominio>/`

Archivos obligatorios:

- `dominio.yaml`
- `contexto.yaml`
- `reglas.yaml`
- `ejemplos.yaml`
- `handler.py`

Archivos opcionales:

- `consultas.yaml`
- `metricas.yaml`
- `vocabulario.yaml`

Los nombres de negocio deben ir en espanol, segun:

- [REGLA_NOMENCLATURA_EMPRESA.md](./REGLA_NOMENCLATURA_EMPRESA.md)
- [GUIA_CAPA_SEMANTICA_EMPRESA.md](./GUIA_CAPA_SEMANTICA_EMPRESA.md)

## Flujo Recomendado De Implementacion

## Paso 1. Definir El Caso De Negocio

Documenta primero:

- nombre del dominio
- objetivo del agente
- entidad principal
- tabla principal
- tabla secundaria si existe
- identificadores unicos
- dimensiones agrupables
- filtros frecuentes
- metricas principales
- relacion con `empleados` o con otro dominio

Plantilla minima:

```yaml
dominio: inventario_red
objetivo: Consultar activos de red y su estado operativo.
entidad_principal: activo_red
tabla_principal: inventario_red_activos
identificadores:
  - serial
  - codigo_activo
dimensiones:
  - sede
  - tipo_activo
  - estado_operativo
filtros:
  - serial
  - codigo_activo
  - sede
  - estado_operativo
metricas:
  - count
relaciones:
  - con: empleados
    por: supervisor_cedula -> cinco_base_de_personal.cedula
```

## Paso 2. Registrar El Dominio En `ai_dictionary`

Si es un dominio nuevo:

### 2.1 Crear o actualizar `dd_dominios`

Ejemplo:

```sql
INSERT INTO ai_dictionary.dd_dominios
(codigo, nombre, descripcion, activo, creado_en)
SELECT 'INVENTARIO_RED', 'Inventario red', 'Dominio de activos de red', 1, NOW()
WHERE NOT EXISTS (
  SELECT 1
  FROM ai_dictionary.dd_dominios
  WHERE codigo = 'INVENTARIO_RED'
);
```

Si solo agregas tabla a un dominio existente, no crees otro dominio.

## Paso 3. Registrar La Tabla En `dd_tablas`

Ejemplo:

```sql
SET @dom_id := (
  SELECT id
  FROM ai_dictionary.dd_dominios
  WHERE codigo = 'INVENTARIO_RED'
  LIMIT 1
);

INSERT INTO ai_dictionary.dd_tablas
(dominio_id, schema_name, table_name, alias_negocio, descripcion, clave_negocio, nivel_confianza, activo, creado_en)
SELECT
  @dom_id,
  'bd_c3nc4s1s',
  'inventario_red_activos',
  'activos_red',
  'Activos de red',
  'serial',
  'ALTO',
  1,
  NOW()
WHERE NOT EXISTS (
  SELECT 1
  FROM ai_dictionary.dd_tablas
  WHERE dominio_id = @dom_id
    AND schema_name = 'bd_c3nc4s1s'
    AND table_name = 'inventario_red_activos'
);
```

## Paso 4. Registrar Las Columnas En `dd_campos`

Aqui defines el significado de cada columna.

Columnas minimas recomendadas:

- identificador
- nombre/logica de negocio
- es_filtro
- es_group_by
- es_metrica
- definicion_negocio

Ejemplo:

```sql
SET @tabla_id := (
  SELECT id
  FROM ai_dictionary.dd_tablas
  WHERE schema_name = 'bd_c3nc4s1s'
    AND table_name = 'inventario_red_activos'
  LIMIT 1
);

INSERT INTO ai_dictionary.dd_campos
(tabla_id, column_name, campo_logico, definicion_negocio, tipo_dato, es_filtro, es_group_by, es_metrica, activo, creado_en)
SELECT @tabla_id, 'serial', 'serial', 'Serial unico del activo', 'varchar', 1, 0, 0, 1, NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM ai_dictionary.dd_campos
  WHERE tabla_id = @tabla_id AND column_name = 'serial'
);

INSERT INTO ai_dictionary.dd_campos
(tabla_id, column_name, campo_logico, definicion_negocio, tipo_dato, es_filtro, es_group_by, es_metrica, activo, creado_en)
SELECT @tabla_id, 'tipo_activo', 'tipo_activo', 'Tipo de activo de red', 'varchar', 1, 1, 0, 1, NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM ai_dictionary.dd_campos
  WHERE tabla_id = @tabla_id AND column_name = 'tipo_activo'
);
```

## Paso 5. Registrar Capacidades Por Columna En `ia_dev_capacidades_columna`

Este paso es el que vuelve la columna util para el runtime.

Ejemplo:

```sql
INSERT INTO ai_dictionary.ia_dev_capacidades_columna (
  campo_id,
  supports_filter,
  supports_group_by,
  supports_metric,
  supports_dimension,
  is_date,
  is_identifier,
  is_chart_dimension,
  is_chart_measure,
  normalization_strategy,
  priority,
  active,
  created_at,
  updated_at
)
SELECT
  c.id,
  1,
  1,
  0,
  1,
  0,
  CASE WHEN c.column_name = 'serial' THEN 1 ELSE 0 END,
  1,
  0,
  'literal_keyword',
  90,
  1,
  UNIX_TIMESTAMP(),
  UNIX_TIMESTAMP()
FROM ai_dictionary.dd_campos c
WHERE c.tabla_id = @tabla_id
  AND c.column_name IN ('serial', 'tipo_activo', 'sede', 'estado_operativo')
ON DUPLICATE KEY UPDATE
  supports_filter = VALUES(supports_filter),
  supports_group_by = VALUES(supports_group_by),
  supports_dimension = VALUES(supports_dimension),
  is_identifier = VALUES(is_identifier),
  priority = VALUES(priority),
  active = VALUES(active),
  updated_at = VALUES(updated_at);
```

## Paso 6. Registrar Sinonimos En `dd_sinonimos`

Aqui enseñas el lenguaje real del negocio.

Ejemplo:

```sql
INSERT INTO ai_dictionary.dd_sinonimos
(dominio_id, termino, sinonimo, tipo, activo, creado_en)
SELECT @dom_id, 'tipo_activo', 'equipo', 'campo', 1, NOW()
WHERE NOT EXISTS (
  SELECT 1
  FROM ai_dictionary.dd_sinonimos
  WHERE dominio_id = @dom_id
    AND termino = 'tipo_activo'
    AND sinonimo = 'equipo'
);
```

Regla:

- sinonimos de negocio en espanol
- sinonimos concretos
- evita sinonimos demasiado genericos como `dato`, `registro`, `elemento`

## Paso 7. Registrar Relaciones Entre Tablas

Si la nueva tabla debe usar dimensiones de `empleados` o de otra tabla, registra la relacion.

### Opcion recomendada: `dd_relaciones`

Ejemplo:

```sql
INSERT INTO ai_dictionary.dd_relaciones
(dominio_id, nombre_relacion, tabla_origen, tabla_destino, tipo_join, condicion_join_sql, cardinalidad, descripcion, activo, creado_en)
SELECT
  @dom_id,
  'inventario_red_supervisor_empleado',
  'bd_c3nc4s1s.inventario_red_activos',
  'bd_c3nc4s1s.cinco_base_de_personal',
  'left',
  'inventario_red_activos.supervisor_cedula = cinco_base_de_personal.cedula',
  'N:1',
  'Relacion entre activos de red y maestro de empleados por supervisor',
  1,
  NOW()
WHERE NOT EXISTS (
  SELECT 1
  FROM ai_dictionary.dd_relaciones
  WHERE nombre_relacion = 'inventario_red_supervisor_empleado'
);
```

### Cuando relacionar con `empleados`

Hazlo cuando necesites resolver desde la nueva tabla:

- `area`
- `cargo`
- `tipo_labor`
- `carpeta`
- `supervisor`
- `sede`

No copies esas columnas si ya viven correctamente en `cinco_base_de_personal`, salvo que tengas un caso fuerte de historico congelado.

## Paso 8. Crear La Carpeta Del Dominio

Ruta:

`backend/apps/ia_dev/domains/<dominio>/`

Minimo:

```text
backend/apps/ia_dev/domains/inventario_red/
  dominio.yaml
  contexto.yaml
  reglas.yaml
  ejemplos.yaml
  handler.py
```

## Paso 9. Crear `dominio.yaml`

Ejemplo base:

```yaml
codigo_dominio: inventario_red
nombre: Inventario red
descripcion: Dominio para consultar activos de red y su estado operativo.
entidad_principal: activo_red
tablas_principales:
  - bd_c3nc4s1s.inventario_red_activos
tablas_relacionadas:
  - bd_c3nc4s1s.cinco_base_de_personal
joins_conocidos:
  - nombre: inventario_red_supervisor_empleado
    condicion: inventario_red_activos.supervisor_cedula = cinco_base_de_personal.cedula
columnas_clave:
  identificadores:
    - serial
    - codigo_activo
  dimensiones:
    - tipo_activo
    - sede
    - estado_operativo
  filtros:
    - serial
    - codigo_activo
    - estado_operativo
metricas:
  - count
```

## Paso 10. Crear `contexto.yaml`

Aqui se le explica al nodo OpenAI y al runtime como pensar el dominio.

```yaml
descripcion: >
  Este dominio consulta activos de red. La tabla principal contiene el hecho tecnico
  del activo y puede relacionarse con empleados por supervisor_cedula.

criterio_principal: >
  Si la consulta pide serial, codigo de activo, tipo de activo o estado operativo,
  priorizar inventario_red_activos.

defaults_negocio:
  - Si el usuario pide activos sin especificar estado, devolver todos salvo los retirados.
  - Si pide por area o cargo, resolver por join con cinco_base_de_personal.

vocabulario_interno:
  - activo
  - equipo
  - serial
  - red
  - nodo
  - supervisor

tablas_prioritarias:
  - inventario_red_activos
  - cinco_base_de_personal

columnas_prioritarias:
  - serial
  - codigo_activo
  - tipo_activo
  - estado_operativo
  - supervisor_cedula
```

## Paso 11. Crear `reglas.yaml`

```yaml
reglas:
  - codigo: inventario_red_equipo_es_tipo_activo
    descripcion: Si el usuario dice equipo o tipo de equipo, resolver como tipo_activo.
    prioridad: alta

  - codigo: inventario_red_dimensiones_de_personal_por_join
    descripcion: Si el usuario pide area, cargo, tipo_labor o sede, usar join con cinco_base_de_personal.
    prioridad: alta

  - codigo: inventario_red_serial_es_identificador
    descripcion: Si llega un serial exacto, resolver como detalle.
    prioridad: alta
```

## Paso 12. Crear `ejemplos.yaml`

```yaml
ejemplos:
  - consulta: activos por tipo de activo
    interpretacion: Conteo agrupado por tipo_activo.
    capacidad_esperada: inventario_red.count.by_dimension.v1

  - consulta: activos del supervisor 98711054
    interpretacion: Filtro por supervisor_cedula.
    capacidad_esperada: inventario_red.detail.v1

  - consulta: activos por area
    interpretacion: Agrupacion por area usando join con cinco_base_de_personal.
    capacidad_esperada: inventario_red.count.by_dimension.v1
```

## Paso 13. Crear El Handler Del Dominio

Cada dominio nuevo debe tener un handler similar a:

- `backend/apps/ia_dev/domains/empleados/handler.py`
- `backend/apps/ia_dev/domains/attendance/handler.py`
- `backend/apps/ia_dev/domains/transport/handler.py`

Estructura minima:

1. validar `capability_id`
2. resolver filtros runtime
3. resolver group by
4. aplicar joins o llamadas al service correspondiente
5. devolver `reply`, `data`, `trace`, `data_sources`

Si el dominio necesita una app Django propia, crear su service de negocio, por ejemplo:

- `apps/inventario_red/services/activo_service.py`

## Paso 14. Registrar Capabilities

Agregar la nueva capability en:

- `backend/apps/ia_dev/application/routing/capability_catalog.py`

Capacidades minimas recomendadas por dominio:

- `dominio.count.v1`
- `dominio.detail.v1`
- `dominio.summary.by_dimension.v1`

Si el dominio tiene joins con empleados, puedes tener capacidades como:

- `inventario_red.summary.by_area.v1`
- `inventario_red.summary.by_cargo.v1`

Pero si el motor ya soporta dimensiones dinamicas por diccionario, no hace falta una capability por cada columna.

## Paso 15. Registrar Enrutamiento

Revisar y ajustar:

- `intent_to_capability_bridge.py`
- `query_execution_planner.py`
- `query_intent_resolver.py`

Objetivo:

- que el dominio pueda descubrirse por lenguaje natural
- que `por X` implique `group_by`
- que identificadores impliquen `detail`
- que filtros por defecto queden claros

## Paso 16. Relacionarlo Con Empleados U Otro Agente

### 16.1 Relacion por tabla

Registrar `dd_relaciones` y `joins_conocidos` en `dominio.yaml`.

### 16.2 Relacion por semantica

En `reglas.yaml`, dejar claro que ciertas dimensiones salen de otro dominio.

Ejemplo:

```yaml
reglas:
  - codigo: inventario_red_dimensiones_rrhh
    descripcion: Area, cargo, carpeta y tipo_labor se resuelven por join con empleados.
    prioridad: alta
```

### 16.3 Relacion por planner

El runtime debe poder descubrir:

- tabla base
- tabla enriquecedora
- condicion de join
- columnas agrupables de la tabla relacionada

### 16.4 Relacion por agente

En esta arquitectura, la recomendacion principal es:

- primero preferir `planner multi-tabla`
- usar `multiagente real` solo cuando haya subproblemas independientes

Ejemplo correcto:

- `ausentismos por cargo`
  - tabla base: ausentismos
  - join: empleados
  - dimension: cargo

Eso no requiere dos agentes conversando si el join es deterministico.

Ejemplo donde si podria haber dos agentes:

- una consulta compuesta con dos procesos distintos, dos fuentes o dos decisiones de negocio independientes

## Paso 17. Si Quieres Multiagente Real

Usalo cuando:

- hay varios dominios realmente distintos
- una parte resuelve entidad objetivo y otra calcula metricas
- hay fuentes de datos diferentes
- quieres ejecucion paralela

Patron sugerido:

1. agente coordinador identifica subproblemas
2. agente de dominio A resuelve entidades o restricciones
3. agente de dominio B ejecuta hechos/metricas
4. coordinador arma respuesta final

Pero para joins clasicos de negocio, sigue siendo mejor:

- `semantic planner + join controlado`

## Paso 18. Habilitar Memoria De Patrones

Ya quedo recomendada y activada por defecto en el simulador, pero si necesitas revisar:

```powershell
$env:IA_DEV_QUERY_PATTERN_MEMORY_ENABLED="1"
$env:IA_DEV_QUERY_PATTERN_FASTPATH_ENABLED="1"
$env:IA_DEV_QUERY_PATTERN_MEMORY_BUSINESS_ENABLED="1"
$env:IA_DEV_QUERY_PATTERN_MEMORY_BUSINESS_AUTOAPPLY_ENABLED="1"
```

Esto permite:

- aprendizaje por usuario
- aprendizaje por negocio sin identificadores sensibles
- fast-path semantico para consultas repetidas

## Paso 19. Checklist De Integracion

Antes de dar por terminado un dominio nuevo, valida todo esto:

- `dd_dominios` creado o actualizado
- `dd_tablas` creado
- `dd_campos` completos
- `ia_dev_capacidades_columna` completo
- `dd_sinonimos` cargado
- `dd_relaciones` cargado si hay joins
- carpeta del dominio creada
- `dominio.yaml` listo
- `contexto.yaml` listo
- `reglas.yaml` listo
- `ejemplos.yaml` listo
- `handler.py` listo
- capability registrada
- planner y bridge ajustados
- pruebas unitarias creadas
- pruebas de simulador ejecutadas

## Paso 20. Pruebas Minimas Recomendadas

Para cada dominio nuevo, prueba al menos:

### Descubrimiento de dominio

- `consulta basica del dominio`

### Detalle por identificador

- `detalle de <id>`

### Conteo basico

- `cantidad de registros`

### Agrupacion

- `registros por <dimension>`

### Join con empleados

- `registros por area`
- `registros por cargo`

### Tolerancia de lenguaje

- sinonimos
- typos frecuentes
- acentos

## Camino Rapido Recomendado

Si solo quieres meter una tabla nueva de forma segura:

1. decide si va en dominio existente o nuevo
2. registra `dd_tablas`
3. registra `dd_campos`
4. registra `ia_dev_capacidades_columna`
5. registra `dd_sinonimos`
6. si aplica, registra `dd_relaciones`
7. crea o ajusta `contexto.yaml`, `reglas.yaml`, `ejemplos.yaml`
8. si hace falta, ajusta handler
9. corre simulaciones reales

## Plantilla De Decisiones

Usa esta plantilla cada vez que metas una nueva tabla:

```text
Nombre de tabla:
Dominio destino:
Necesita nuevo agente: si/no
Entidad principal:
Identificador unico:
Filtros principales:
Dimensiones agrupables:
Metricas:
Relacion con empleados:
  si/no
  por que campo:
  para que dimensiones:
Relacion con otro dominio:
  si/no
  cual:
Capacidades a exponer:
Consultas iniciales a soportar:
```

## Archivos Del Proyecto Que Mas Vas A Tocar

### Base semantica y runtime

- `backend/apps/ia_dev/application/semantic/semantic_business_resolver.py`
- `backend/apps/ia_dev/application/semantic/query_intent_resolver.py`
- `backend/apps/ia_dev/application/semantic/query_execution_planner.py`
- `backend/apps/ia_dev/application/routing/intent_to_capability_bridge.py`
- `backend/apps/ia_dev/application/routing/capability_catalog.py`
- `backend/apps/ia_dev/application/delegation/domain_context_loader.py`

### Dominio nuevo

- `backend/apps/ia_dev/domains/<dominio>/dominio.yaml`
- `backend/apps/ia_dev/domains/<dominio>/contexto.yaml`
- `backend/apps/ia_dev/domains/<dominio>/reglas.yaml`
- `backend/apps/ia_dev/domains/<dominio>/ejemplos.yaml`
- `backend/apps/ia_dev/domains/<dominio>/handler.py`

### Diccionario y DB

- `ai_dictionary.dd_dominios`
- `ai_dictionary.dd_tablas`
- `ai_dictionary.dd_campos`
- `ai_dictionary.dd_sinonimos`
- `ai_dictionary.dd_relaciones`
- `ai_dictionary.ia_dev_capacidades_columna`

## Recomendacion Final

La secuencia mas estable para escalar en empresa grande es:

1. modelar bien la tabla en `ai_dictionary`
2. darle contexto corto y claro en `YAML`
3. registrar joins permitidos
4. hacer que el planner descubra tablas y columnas candidatas
5. dejar que OpenAI solo desambigue
6. guardar patrones satisfactorios para acelerar lo repetido

Si una tabla nueva queda bien modelada en esas capas, el sistema deja de depender de
hardcodes por consulta y se vuelve cada vez mas reusable.
