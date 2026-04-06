from django.core.management.base import BaseCommand

from apps.ia_dev.services.async_job_service import AsyncJobService
from apps.ia_dev.services.knowledge_governance_service import KnowledgeGovernanceService


class Command(BaseCommand):
    help = "Procesa jobs asincronos pendientes de IA DEV"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=25)

    def handle(self, *args, **options):
        limit = int(options.get("limit") or 25)
        job_service = AsyncJobService()
        governance = KnowledgeGovernanceService()

        def _handle_knowledge_approve(payload: dict):
            return governance.apply_proposal(
                proposal_id=str(payload.get("proposal_id", "")).strip(),
                auth_key=str(payload.get("auth_key", "")).strip() or None,
                bypass_auth=bool(payload.get("bypass_auth", False)),
                idempotency_key=str(payload.get("idempotency_key", "")).strip() or None,
            )

        processed = job_service.process_pending(
            limit=limit,
            handler_registry={
                "knowledge_approve": _handle_knowledge_approve,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(f"Jobs procesados: {len(processed)}")
        )
        for job in processed:
            self.stdout.write(
                f"- {job.get('job_id')} | {job.get('job_type')} | {job.get('status')}"
            )
