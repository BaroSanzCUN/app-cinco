from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ia_dev.services.dictionary_tool_service import DictionaryToolService
from apps.ia_dev.services.orchestrator_service import IADevOrchestratorService
from apps.ia_dev.services.ticket_service import TicketService
from apps.security.permissions.api_permissions import IsAuthenticatedUser


orchestrator_service = IADevOrchestratorService()
dictionary_tool_service = DictionaryToolService()


class IADevChatView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def post(self, request):
        message = str(request.data.get("message", "")).strip()
        session_id = request.data.get("session_id")
        reset_memory = bool(request.data.get("reset_memory", False))

        if not message:
            return Response(
                {"detail": "message is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = orchestrator_service.run(
            message=message,
            session_id=session_id,
            reset_memory=reset_memory,
        )
        return Response(result, status=status.HTTP_200_OK)


class IADevMemoryResetView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def post(self, request):
        session_id = str(request.data.get("session_id", "")).strip()
        if not session_id:
            return Response(
                {"detail": "session_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = orchestrator_service.reset_memory(session_id)
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)


class IADevHealthView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def get(self, request):
        try:
            dictionary_status = dictionary_tool_service.check_connection()
            try:
                dictionary_status["snapshot"] = dictionary_tool_service.get_dictionary_snapshot()
            except Exception:
                pass
            payload = {
                "status": "ok",
                "data_sources": {
                    "ai_dictionary": dictionary_status,
                },
            }
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as exc:
            payload = {
                "status": "degraded",
                "data_sources": {
                    "ai_dictionary": {
                        "ok": False,
                        "error": str(exc),
                    }
                },
            }
            return Response(payload, status=status.HTTP_200_OK)


class IADevTicketView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def post(self, request):
        title = str(request.data.get("title", "")).strip()
        description = str(request.data.get("description", "")).strip()
        category = str(request.data.get("category", "general")).strip().lower()
        session_id = str(request.data.get("session_id", "")).strip() or None

        if not title:
            return Response(
                {"detail": "title is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not description:
            return Response(
                {"detail": "description is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ticket = TicketService.create_ticket(
            title=title,
            description=description,
            category=category,
            session_id=session_id,
        )
        return Response(
            {
                "status": "created",
                "ticket": ticket,
            },
            status=status.HTTP_201_CREATED,
        )
