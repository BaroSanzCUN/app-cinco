# Contrato API: Gobierno IA DEV

## Alcance

Este contrato define el flujo de gobierno para propuestas de conocimiento en IA DEV.

Ruta base: `/ia-dev`

Autenticacion: JWT/sesion requerida (`IsAuthenticatedUser`).

Contrato relacionado de memoria gobernada: `backend/apps/ia_dev/API_CONTRACT_MEMORY.md`.

## 1) Crear propuesta

Endpoint: `POST /knowledge/proposals/`

Request minimo:

```json
{
  "message": "crear regla para marcar reincidencia injustificada mayor a 2"
}
```
Exito:

- `201 Created`

Forma de respuesta:

```json
{
  "ok": true,
  "requires_auth": true,
  "applied": false,
  "proposal": {
    "proposal_id": "KPRO-XXXXXXXX",
    "status": "pending"
  }
}
```

Errores de validacion:

- `400 Bad Request`

## 2) Listar propuestas

Endpoint: `GET /knowledge/proposals/?status=pending&limit=30`

Exito:

- `200 OK`

Forma de respuesta:

```json
{
  "status": "ok",
  "count": 1,
  "proposals": []
}
```

## 3) Aprobar propuesta (modo sync)

Condicion: `IA_DEV_ASYNC_MODE=sync`

Endpoint: `POST /knowledge/proposals/approve/`

Request:

```json
{
  "proposal_id": "KPRO-XXXXXXXX",
  "auth_key": "secret_if_mode_ceo",
  "idempotency_key": "approve-kpro-001"
}
```

Exito:

- `200 OK` cuando se aplica o cuando es idempotente

Error de autorizacion:

- `403 Forbidden` cuando la clave es invalida y el modo es `ceo`

Error de negocio/validacion:

- `400 Bad Request`

## 4) Aprobar propuesta (modo async)

Condicion: `IA_DEV_ASYNC_MODE=db_queue` (o cualquier valor distinto de `sync`)

Endpoint: `POST /knowledge/proposals/approve/`

Request:

```json
{
  "proposal_id": "KPRO-XXXXXXXX",
  "auth_key": "secret_if_mode_ceo",
  "idempotency_key": "approve-kpro-001"
}
```

Aceptado:

- `202 Accepted`

Forma de respuesta:

```json
{
  "ok": true,
  "status": "accepted",
  "async_mode": "db_queue",
  "job": {
    "job_id": "JOB-XXXXXXXXXX",
    "status": "pending"
  }
}
```

## 5) Consultar job async

Endpoint: `GET /async/jobs/?job_id=JOB-XXXXXXXXXX`

Exito:

- `200 OK`

No encontrado:

- `404 Not Found`

Forma de respuesta:

```json
{
  "status": "ok",
  "job": {
    "job_id": "JOB-XXXXXXXXXX",
    "job_type": "knowledge_approve",
    "status": "pending|running|done|failed",
    "result": {},
    "error": null
  }
}
```

## 6) Rechazar propuesta

Endpoint: `POST /knowledge/proposals/reject/`

Request:

```json
{
  "proposal_id": "KPRO-XXXXXXXX",
  "reason": "No cumple politica"
}
```

Exito:

- `200 OK`

## Idempotencia y concurrencia

- Aprobaciones soportan `idempotency_key` en body o `X-Idempotency-Key`.
- `apply_proposal` usa bloqueo DB (`FOR UPDATE`) y estado transitorio `applying`.
- Enqueue async soporta reuso idempotente por `idempotency_key`.
- El worker reclama jobs pendientes con update condicional para evitar doble ejecucion.
