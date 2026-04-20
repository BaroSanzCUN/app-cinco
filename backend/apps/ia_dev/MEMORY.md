## IA DEV Memory Governance

This file defines memory taxonomy and write/read controls for IA DEV.

### Memory Types

1. `session`
- Short conversational context.
- Last period, last entity, grouped/itemized mode, current follow-up.
- Fast turnover and resettable.

2. `user`
- User preferences and format/style choices.
- Scoped to authenticated user key.
- Low-friction persistence for non-sensitive data.

3. `business`
- Reusable domain facts and approved operational patterns.
- Domain/capability scoped.
- Never store user-private details.

4. `workflow`
- Jobs, approvals, retries, idempotency, version state.
- Operational state machine support.

5. `general`
- Cross-domain learned system behavior.
- Must be proposal-based and approved before application.

### Write Policy
- `session`: direct write allowed.
- `user`: direct write allowed when sensitivity is low/medium.
- `business`: proposal + approval required.
- `general`: proposal + approval required (always).
- `workflow`: system-managed, never from raw LLM output.

### Approval Model
- Proposal record in `ia_dev_learned_memory_proposals`.
- Decision records in `ia_dev_learned_memory_approvals`.
- Applied writes only after approved status.

### Audit Requirements
- Every memory proposal and decision must be audited.
- Include actor, scope, action, run_id, trace_id.

### Non-Goals
- Memory files are not execution logic.
- No runtime user/business content should be committed in repository docs.
