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
