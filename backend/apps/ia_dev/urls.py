from django.urls import path

from apps.ia_dev.views import IADevChatView, IADevHealthView, IADevMemoryResetView, IADevTicketView

urlpatterns = [
    path("chat/", IADevChatView.as_view(), name="ia-dev-chat"),
    path("memory/reset/", IADevMemoryResetView.as_view(), name="ia-dev-memory-reset"),
    path("health/", IADevHealthView.as_view(), name="ia-dev-health"),
    path("tickets/", IADevTicketView.as_view(), name="ia-dev-ticket-create"),
]
