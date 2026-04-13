# Guia de Backend (Django)

Este backend esta pensado para operar en entornos controlados, donde la base de datos ya existe y no debe alterarse sin aprobacion.

## Requisitos

- Python 3.11+
- `pip`
- Acceso a la base de datos configurada en `.env`

## Configuracion rapida

1. Ubicate en la carpeta `backend`.
2. Crea entorno virtual:
   - Windows: `python -m venv .venv`
   - Linux/macOS: `python3 -m venv .venv`
3. Activa el entorno:
   - Windows: `.\.venv\Scripts\activate`
   - Linux/macOS: `source .venv/bin/activate`
4. Instala dependencias:
   - `pip install -r requirements.txt`
5. Crea tu `.env` desde `.env.example`.

## Ejecucion

- Servidor de desarrollo:
  - `python manage.py runserver 127.0.0.1:8000`

## Comandos permitidos

- `python manage.py runserver`
- `python manage.py check`
- `python manage.py showmigrations`

## Comandos restringidos

No ejecutes estos comandos sin autorizacion explicita:

- `python manage.py makemigrations`
- `python manage.py migrate`
- `python manage.py flush`

## IA DEV: gobierno de conocimiento

Se agrego un nucleo de gobierno/autoevolucion para propuestas de reglas de negocio en `ai_dictionary.dd_reglas`.

- Modo de gobierno: `IA_DEV_KNOWLEDGE_GOVERNANCE_MODE`
  - `ceo`: requiere aprobacion con clave.
  - `auto`: aplica automaticamente.
  - `directo`: aplica automaticamente (sin paso manual).
- Clave de aprobacion CEO: `IA_DEV_CEO_AUTH_KEY`

## IA DEV: estado distribuido, cola y observabilidad

- Memoria de sesion y tickets persistidos en DB.
- Cache opcional con Redis (desactivada por defecto):
  - `IA_DEV_USE_REDIS`
  - `IA_DEV_REDIS_URL`
  - `IA_DEV_REDIS_PREFIX`
  - `IA_DEV_REDIS_TTL_SECONDS`
- Cola asincrona DB-backed para aprobaciones:
  - `IA_DEV_ASYNC_MODE=sync|db_queue`
  - Worker: `python manage.py process_ia_dev_jobs --limit 25`
- Observabilidad operativa:
  - Latencia por tool
  - Latencia por corrida del orquestador
  - Tokens/costo estimado OpenAI
  - Endpoint resumen: `GET /ia-dev/observability/summary/`
- Delegacion por dominios (PR11 inicial):
  - `IA_DEV_DELEGATION_ENABLED=1|0`
  - `IA_DEV_DELEGATION_MODE=off|shadow|active`
  - `IA_DEV_SYSTEM_SCHEMA=<schema_opcional>`: enruta tablas `ia_dev_*` a un schema especifico sin cambiar el `db_alias`.
    - Si no se define, mantiene el comportamiento actual (schema por defecto de `IA_DEV_DB_ALIAS`).
    - `ai_dictionary` se mantiene como fuente semantica para sync/catalogo; no se usa como destino por defecto.
  - `shadow`: planifica subtareas y registra observabilidad sin alterar la respuesta visible.
  - `active`: habilita ejecucion delegada para dominios soportados.
  - `IA_DEV_DOMAIN_REGISTRY_SYNC_ENABLED=1|0`: sincroniza catalogo desde `ai_dictionary` en runtime.
  - `IA_DEV_SQL_ASSISTED_ENABLED=1|0`: habilita ejecucion de SQL asistido restringido (solo SELECT + LIMIT).
  - `IA_DEV_DB_READONLY_ALIAS`: alias de conexion read-only para SQL asistido.
  - `IA_DEV_DOMAIN_ONBOARDING_WORKFLOW_ENABLED=1|0`: activa transiciones `planned -> partial -> active`.
  - Feature flags por dominio:
    - `IA_DEV_DOMAIN_AUSENTISMO_ENABLED`
    - `IA_DEV_DOMAIN_EMPLEADOS_ENABLED`
    - `IA_DEV_DOMAIN_TRANSPORTE_ENABLED`
    - `IA_DEV_DOMAIN_COMISIONES_ENABLED`
    - `IA_DEV_DOMAIN_FACTURACION_ENABLED`
    - `IA_DEV_DOMAIN_VIATICOS_ENABLED`
    - `IA_DEV_DOMAIN_HORAS_EXTRAS_ENABLED`
- Resolucion de periodos para asistencia:
  - `IA_DEV_USE_OPENAI_PERIOD=1` permite que GPT proponga fechas.
  - `IA_DEV_PERIOD_MODEL` define el modelo para extraer rango.
  - Semantica fija en lenguaje natural:
    - "ultimo mes" => ultimos 30 dias moviles.
    - "mes anterior/mes pasado" => mes calendario anterior.
  - Filtro de personal por estado en consultas de asistencia:
    - all (default), activos, inactivos.
    - El parser lo detecta en texto del usuario (por ejemplo: \"solo activos\").
  - Mapeo de tablas por diccionario:
    - `IA_DEV_USE_DD_TABLAS_MAPPING=1` usa `ai_dictionary.dd_tablas` para resolver schema+tabla reales.
    - Esto ayuda cuando `IA_DEV_PERSONAL_TABLE` o `IA_DEV_ATTENDANCE_TABLE` no coinciden con el schema real.

## Endpoints IA DEV

- `POST /ia-dev/chat/`
- `POST /ia-dev/attendance/period/resolve/`
- `POST /ia-dev/memory/reset/`
- `GET /ia-dev/health/`
- `POST /ia-dev/tickets/`
- `POST /ia-dev/knowledge/proposals/`
- `GET /ia-dev/knowledge/proposals/`
- `POST /ia-dev/knowledge/proposals/approve/`
- `POST /ia-dev/knowledge/proposals/reject/`
- `GET /ia-dev/async/jobs/?job_id=...`
- `GET /ia-dev/observability/summary/`

## Estandar de texto y codificacion

- Todos los archivos de texto deben guardarse en UTF-8.
- Mantener textos en espanol latino.
- Evita caracteres corruptos (mojibake) en tildes, enes y simbolos.
- Validacion sugerida:
  - `powershell -ExecutionPolicy Bypass -File ..\scripts\check_mojibake.ps1`
