# Contrato API: Memoria IA DEV

## Alcance

Contrato incremental para endpoints de memoria bajo `/ia-dev/memory/*`.

- Endpoint base legacy preservado: `POST /ia-dev/chat/`
- Autenticacion requerida: `IsAuthenticatedUser`
- Compatibilidad: PR1 y orquestador legacy sin ruptura
- Integracion runtime en chat controlada por feature flags:
  - `IA_DEV_MEMORY_READ_ENABLED`
  - `IA_DEV_MEMORY_WRITE_ENABLED`
  - `IA_DEV_MEMORY_PROPOSALS_ENABLED`
  - `IA_DEV_POLICY_RUNTIME_ENABLED`
  - `IA_DEV_WORKFLOW_STATE_ENABLED`

## Extensiones en `POST /ia-dev/chat/`

Campos nuevos de respuesta (compatibles y opcionales):

```json
{
  "actions": [],
  "memory_candidates": [],
  "pending_proposals": []
}
```

Semantica:

- `memory_candidates`: candidatos detectados por loop agentic en la corrida.
- `pending_proposals`: propuestas de memoria en estado pendiente/approval relacionadas.
- `actions`: acciones sugeridas para frontend (por ejemplo, revisar propuestas).
  El payload puede incluir `workflow_statuses` para priorizacion visual.

## 1) Memoria de cuenta

### GET `/ia-dev/memory/user/`

Query params:

- `user_key` (opcional, solo admin/lead/governance)
- `limit` (opcional, default `100`, max `300`)

Respuesta `200`:

```json
{
  "status": "ok",
  "count": 1,
  "memory": [
    {
      "user_key": "user:12",
      "memory_key": "attendance.output_mode",
      "memory_value": {"value": "grouped"},
      "sensitivity": "low"
    }
  ]
}
```

Restricciones:

- Cuenta normal solo puede leer su propio `user_key`.
- `403` si intenta consultar memoria de otra cuenta.

### POST `/ia-dev/memory/user/`

Request:

```json
{
  "memory_key": "attendance.output_mode",
  "memory_value": {"value": "grouped"},
  "sensitivity": "low"
}
```

Campos opcionales:

- `user_key` (solo admin/lead/governance)

Validaciones:

- `memory_key` obligatorio, formato seguro `[A-Za-z0-9_.:-]`, max `120`
- `sensitivity` en `low|medium|high`
- `memory_value` serializable y max `8KB`

## 2) Propuestas de memoria aprendida

### GET `/ia-dev/memory/proposals/`

Query params:

- `status` (opcional)
- `scope` (opcional)
- `limit` (opcional, default `30`, max `200`)

RBAC:

- admin/lead/governance: puede listar global
- cuenta normal: solo sus propuestas (`proposer_user_key`)

Extensiones PR7:

- Cada propuesta puede incluir:
  - `workflow_status`
  - `workflow_key`
  - `workflow` (detalle del estado operativo)
- La respuesta incluye `approval_policy` (metadata cargada desde `POLICIES/approval_policy.yaml`).

### POST `/ia-dev/memory/proposals/`

Request minimo:

```json
{
  "scope": "business",
  "candidate_key": "attendance.rule.recurrence",
  "candidate_value": {"threshold": 3},
  "reason": "regla reusable",
  "sensitivity": "medium",
  "idempotency_key": "lmp-001"
}
```

Reglas:

- `scope` permitido: `session|user|business|workflow|general`
- `candidate_key` obligatorio y seguro
- `candidate_value` serializable, max `8KB`
- `reason` max `4KB`

Estados HTTP:

- `201` propuesta creada
- `200` idempotente (ya existia por `idempotency_key`)
- `400` validacion o error de negocio

## 3) Aprobacion/Rechazo de propuestas

### POST `/ia-dev/memory/proposals/approve/`
### POST `/ia-dev/memory/proposals/reject/`

Request:

```json
{
  "proposal_id": "LMP-XXXXXXXX",
  "comment": "aprobada por governance"
}
```

RBAC:

- Alcance `business` o `general`: gobernado por `POLICIES/approval_policy.yaml`
- Cuenta normal: no puede aprobar/rechazar global

Estados:

- `200` aplicado/rechazado o idempotente
- `403` no autorizado
- `404` proposal no existe
- `400` error de validacion/estado

## 4) Auditoria de memoria

### GET `/ia-dev/memory/audit/`

Query params:

- `scope` (opcional)
- `entity_key` (opcional)
- `limit` (opcional, default `100`, max `500`)

RBAC:

- admin/lead/governance: auditoria global
- cuenta normal: solo `scope=user` y su propio prefijo `entity_key`

## Idempotencia y concurrencia

- Propuestas soportan `idempotency_key`.
- En colision de concurrencia (`IntegrityError`) se reintenta lookup y se responde idempotente cuando aplica.
- Operaciones criticas ejecutan `transaction.atomic(using=db_alias)`.

## Workflow state (PR7)

- Tabla operativa: `ia_dev_workflow_state`
- Tipo usado para propuestas: `workflow_type=memory_proposal`
- Estados soportados:
  - `pending`
  - `approved`
  - `rejected`
  - `applied`
  - `failed`
  - `expired`
- Transiciones invalidas se bloquean cuando `IA_DEV_WORKFLOW_ENFORCE_TRANSITIONS=1`.
