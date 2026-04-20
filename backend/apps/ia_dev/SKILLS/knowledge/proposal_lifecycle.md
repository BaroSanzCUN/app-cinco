# Skill: Knowledge Proposal Lifecycle

## Goal
Run a safe lifecycle for business-rule evolution.

## Procedure
1. Create proposal from request.
2. Detect similar existing rules.
3. Route to approval (sync or async).
4. Apply with idempotency and transaction lock.
5. Record persistence and audit events.

## Constraints
- No direct global writes without approval.
- Keep proposal traceability and versioning.
