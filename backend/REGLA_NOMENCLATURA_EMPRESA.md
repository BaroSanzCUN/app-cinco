# Regla De Nomenclatura Empresarial

## Objetivo

Unificar el lenguaje del proyecto para que toda la informacion de negocio de la empresa
use nombres en espanol, mientras la infraestructura y los procesos tecnicos internos
pueden seguir en ingles.

## Regla General

- Todo artefacto relacionado con informacion de la empresa debe nombrarse en espanol.
- Todo artefacto tecnico de infraestructura, runtime, adapters, planners, routers,
  observability, OpenAI, cache, transport interno o utilidades de framework puede
  mantenerse en ingles.

## Debe ir en espanol

- Carpetas y archivos de contexto de negocio.
- Archivos de dominios semanticos y sus complementos.
- Nombres de tablas de negocio nuevas.
- Nombres de columnas de negocio nuevas.
- Alias logicos, nombres funcionales y sinonimos del diccionario.
- Reglas de negocio, ejemplos de consulta y vocabulario empresarial.
- Funciones y metodos que expresen procesos propios del negocio de la compania.

## Puede seguir en ingles

- Variables internas de runtime tecnico.
- Funciones auxiliares de parsing, routing, orchestration, policy, cache y adapters.
- Clases base de framework o infraestructura.
- Nombres de metodos internos de bajo nivel cuando no representan lenguaje del negocio.

## Criterio Practico

- Si el nombre lo diria un lider de area, analista o usuario de negocio, debe ir en espanol.
- Si el nombre lo usa principalmente el equipo de plataforma o infraestructura tecnica,
  puede ir en ingles.

## Ejemplos Correctos

- `empleados.contexto.yaml`
- `ausentismo.reglas.yaml`
- `cinco_base_de_personal`
- `tipo_labor`
- `motivo_justificacion`
- `obtener_resumen_de_ausentismo`

## Ejemplos Que Deben Evitarse En Capa De Negocio

- `employees_business_context.yaml`
- `absence_reason_rules.yaml`
- `employee_master`
- `job_type`

## Aplicacion En El Legado

- Esta regla es obligatoria para todo artefacto nuevo.
- El legado se migra de forma incremental y segura.
- No se recomienda renombrado masivo tipo big-bang en codigo productivo.
- Cada refactor debe priorizar compatibilidad y pruebas.
