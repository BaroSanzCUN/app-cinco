# Guia De Capa Semantica Empresarial

## Recomendacion Arquitectonica

La practica recomendada para empresas con multiples tablas, procesos y agentes no es
usar solo base de datos ni solo texto libre. La opcion mas estable es una capa semantica
hibrida:

- `ai_dictionary`: catalogo estructurado y gobernado.
- Archivos YAML versionados: contexto operativo corto, reglas de negocio y ejemplos.
- Planner deterministico: selecciona dominio, tablas, columnas y joins candidatos.
- LLM: desambiguacion y normalizacion final, no descubrimiento libre de negocio.

## Estructura Recomendada Por Dominio

Para cada dominio de negocio, mantener en `backend/apps/ia_dev/domains/<dominio>/`:

- `dominio.yaml`
- `contexto.yaml`
- `reglas.yaml`
- `ejemplos.yaml`

El directorio `backend/apps/ia_dev/domains/registry/` queda reservado para compatibilidad
incremental y definiciones legacy de transicion.

## Rol De Cada Archivo

### `dominio.yaml`

Define el contrato base del dominio:

- nombre del dominio
- objetivo de negocio
- entidad principal
- tablas asociadas
- columnas clave
- joins conocidos
- filtros soportados
- group by soportados
- metricas soportadas

### `contexto.yaml`

Explica al agente como debe pensar el dominio:

- descripcion del dominio
- criterio principal de seleccion de tabla
- defaults de negocio
- vocabulario interno
- tablas prioritarias
- columnas prioritarias

### `reglas.yaml`

Expone reglas concretas y gobernables:

- mapeos implicitos
- defaults
- restricciones
- criterios de prioridad
- equivalencias de lenguaje

### `ejemplos.yaml`

Sirve como entrenamiento operativo controlado:

- consulta ejemplo
- interpretacion esperada
- capacidad esperada
- filtros o agrupaciones esperadas

## Distribucion Profesional De Responsabilidades

### En `ai_dictionary`

Guardar:

- dominios
- tablas
- columnas
- sinonimos
- capacidades por columna
- valores permitidos
- joins permitidos
- reglas simples y reutilizables

### En Archivos YAML

Guardar:

- contexto del agente
- reglas de negocio compuestas
- defaults semanticos
- ejemplos reales de consulta
- ambiguedades frecuentes
- vocabulario interno de la empresa

## Regla De Nombres

Todo artefacto de negocio debe seguir [REGLA_NOMENCLATURA_EMPRESA.md](./REGLA_NOMENCLATURA_EMPRESA.md).

## Estrategia De Migracion Recomendada

1. Mantener el runtime tecnico actual.
2. No renombrar el legado masivamente.
3. Empezar a crear todo lo nuevo en espanol.
4. Versionar contexto, reglas y ejemplos por dominio.
5. Hacer migracion gradual del legado cuando haya pruebas.

## Dominios Iniciales Ya Preparados

- `empleados`
- `ausentismo`

Cada uno ya tiene archivos de:

- contexto
- reglas
- ejemplos
