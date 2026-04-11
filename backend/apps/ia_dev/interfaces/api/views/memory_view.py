from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ia_dev.interfaces.api.serializers.memory_serializer import (
    normalize_memory_payload,
    parse_limit,
    validate_memory_payload,
)
from apps.ia_dev.services.memory_governance_service import MemoryGovernanceService
from apps.security.permissions.api_permissions import IsAuthenticatedUser


memory_governance_service = MemoryGovernanceService()


def _resolve_user_key(request) -> str:
    user = getattr(request, "user", None)
    if not user:
        return "unknown"
    user_id = getattr(user, "id", None)
    username = getattr(user, "username", None)
    if user_id is not None:
        return f"user:{user_id}"
    if username:
        return f"user:{username}"
    return "unknown"


def _resolve_role(request) -> str:
    user = getattr(request, "user", None)
    if not user:
        return "user"
    try:
        if user.groups.filter(name__iexact="governance").exists():
            return "governance"
    except Exception:
        pass
    if bool(getattr(user, "is_superuser", False)):
        return "admin"
    if bool(getattr(user, "is_staff", False)):
        return "lead"
    return "user"


def _is_admin_like(request) -> bool:
    return _resolve_role(request) in {"admin", "lead", "governance"}


class IADevMemoryProposalView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def get(self, request):
        status_filter = str(request.query_params.get("status", "")).strip() or None
        scope_filter = str(request.query_params.get("scope", "")).strip() or None
        limit = parse_limit(request.query_params.get("limit"), default=30, max_value=200)
        user_key = _resolve_user_key(request)
        proposer_user_key = None if _is_admin_like(request) else user_key
        proposals = memory_governance_service.list_proposals(
            status=status_filter,
            scope=scope_filter,
            proposer_user_key=proposer_user_key,
            limit=limit,
        )
        if not _is_admin_like(request):
            proposals = [
                item for item in proposals if str(item.get("proposer_user_key") or "") == user_key
            ]
        return Response(
            {
                "status": "ok",
                "count": len(proposals),
                "proposals": proposals,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        user_key = _resolve_user_key(request)
        payload = normalize_memory_payload(dict(request.data or {}))
        is_valid, error = validate_memory_payload(payload)
        if not is_valid:
            return Response(
                {"ok": False, "error": error or "payload invalido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = memory_governance_service.create_proposal(
            user_key=user_key,
            payload=payload,
            source_run_id=payload.get("source_run_id"),
        )
        if not result.get("ok"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            result,
            status=status.HTTP_200_OK if result.get("idempotent") else status.HTTP_201_CREATED,
        )


class IADevMemoryProposalApproveView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def post(self, request):
        proposal_id = str(request.data.get("proposal_id", "")).strip()
        if not proposal_id:
            return Response(
                {"ok": False, "error": "proposal_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        proposal = memory_governance_service.get_proposal(proposal_id=proposal_id)
        if not proposal:
            return Response(
                {"ok": False, "error": "proposal_id not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        proposal_scope = str(proposal.get("scope") or "").lower()
        if proposal_scope in ("business", "general") and not _is_admin_like(request):
            return Response(
                {"ok": False, "error": "No autorizado para aprobar memoria business/general"},
                status=status.HTTP_403_FORBIDDEN,
            )
        result = memory_governance_service.approve_proposal(
            proposal_id=proposal_id,
            actor_user_key=_resolve_user_key(request),
            actor_role=_resolve_role(request),
            comment=str(request.data.get("comment", "")).strip(),
        )
        if not result.get("ok"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class IADevMemoryProposalRejectView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def post(self, request):
        proposal_id = str(request.data.get("proposal_id", "")).strip()
        if not proposal_id:
            return Response(
                {"ok": False, "error": "proposal_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        proposal = memory_governance_service.get_proposal(proposal_id=proposal_id)
        if not proposal:
            return Response(
                {"ok": False, "error": "proposal_id not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        proposal_scope = str(proposal.get("scope") or "").lower()
        if proposal_scope in ("business", "general") and not _is_admin_like(request):
            return Response(
                {"ok": False, "error": "No autorizado para rechazar memoria business/general"},
                status=status.HTTP_403_FORBIDDEN,
            )
        result = memory_governance_service.reject_proposal(
            proposal_id=proposal_id,
            actor_user_key=_resolve_user_key(request),
            actor_role=_resolve_role(request),
            comment=str(request.data.get("comment", "")).strip(),
        )
        if not result.get("ok"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class IADevUserMemoryView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def get(self, request):
        requester_user_key = _resolve_user_key(request)
        query_user_key = str(request.query_params.get("user_key", "")).strip() or None
        if query_user_key and query_user_key != requester_user_key and not _is_admin_like(request):
            return Response(
                {"ok": False, "error": "No autorizado para consultar memoria de otro usuario"},
                status=status.HTTP_403_FORBIDDEN,
            )
        user_key = query_user_key or requester_user_key
        limit = parse_limit(request.query_params.get("limit"), default=100, max_value=300)
        rows = memory_governance_service.get_user_preferences(user_key=user_key, limit=limit)
        return Response(
            {"status": "ok", "count": len(rows), "memory": rows},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        requester_user_key = _resolve_user_key(request)
        body_user_key = str(request.data.get("user_key", "")).strip() or None
        if body_user_key and body_user_key != requester_user_key and not _is_admin_like(request):
            return Response(
                {"ok": False, "error": "No autorizado para escribir memoria de otro usuario"},
                status=status.HTTP_403_FORBIDDEN,
            )
        user_key = body_user_key or requester_user_key
        memory_key = str(request.data.get("memory_key", "")).strip()
        if not memory_key:
            return Response(
                {"ok": False, "error": "memory_key is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        is_valid, error = validate_memory_payload(
            {
                "candidate_key": memory_key,
                "candidate_value": request.data.get("memory_value"),
                "scope": "user",
                "sensitivity": str(request.data.get("sensitivity", "low")).strip().lower(),
                "reason": "",
            }
        )
        if not is_valid:
            return Response(
                {"ok": False, "error": error or "payload invalido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = memory_governance_service.set_user_preference(
            user_key=user_key,
            memory_key=memory_key,
            memory_value=request.data.get("memory_value"),
            sensitivity=str(request.data.get("sensitivity", "low")).strip().lower(),
            source="api_user_memory",
        )
        return Response(result, status=status.HTTP_200_OK if result.get("ok") else status.HTTP_400_BAD_REQUEST)


class IADevMemoryAuditView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def get(self, request):
        limit = parse_limit(request.query_params.get("limit"), default=100, max_value=500)
        memory_scope = str(request.query_params.get("scope", "")).strip() or None
        entity_key = str(request.query_params.get("entity_key", "")).strip() or None
        user_key = _resolve_user_key(request)
        if not _is_admin_like(request):
            if memory_scope and memory_scope != "user":
                return Response(
                    {"ok": False, "error": "No autorizado para consultar auditoria global"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if entity_key and not entity_key.startswith(f"{user_key}:"):
                return Response(
                    {"ok": False, "error": "No autorizado para consultar auditoria de otro usuario"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            memory_scope = "user"
        rows = memory_governance_service.get_audit_events(
            memory_scope=memory_scope,
            entity_key=entity_key,
            limit=limit,
        )
        if not _is_admin_like(request):
            rows = [
                item
                for item in rows
                if str(item.get("entity_key") or "").startswith(f"{user_key}:")
            ]
        return Response(
            {"status": "ok", "count": len(rows), "events": rows},
            status=status.HTTP_200_OK,
        )
