from django.urls import path

from apps.ia_dev.views import (
    IADevAttendancePeriodResolveView,
    IADevAsyncJobView,
    IADevChatView,
    IADevHealthView,
    IADevKnowledgeApproveView,
    IADevKnowledgeProposalView,
    IADevKnowledgeRejectView,
    IADevMemoryResetView,
    IADevObservabilitySummaryView,
    IADevTicketView,
)

urlpatterns = [
    path("chat/", IADevChatView.as_view(), name="ia-dev-chat"),
    path("attendance/period/resolve/", IADevAttendancePeriodResolveView.as_view(), name="ia-dev-attendance-period-resolve"),
    path("memory/reset/", IADevMemoryResetView.as_view(), name="ia-dev-memory-reset"),
    path("health/", IADevHealthView.as_view(), name="ia-dev-health"),
    path("tickets/", IADevTicketView.as_view(), name="ia-dev-ticket-create"),
    path("knowledge/proposals/", IADevKnowledgeProposalView.as_view(), name="ia-dev-knowledge-proposal"),
    path("knowledge/proposals/approve/", IADevKnowledgeApproveView.as_view(), name="ia-dev-knowledge-approve"),
    path("knowledge/proposals/reject/", IADevKnowledgeRejectView.as_view(), name="ia-dev-knowledge-reject"),
    path("async/jobs/", IADevAsyncJobView.as_view(), name="ia-dev-async-job-status"),
    path("observability/summary/", IADevObservabilitySummaryView.as_view(), name="ia-dev-observability-summary"),
]
