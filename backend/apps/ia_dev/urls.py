from django.urls import path

from apps.ia_dev.views import (
    IADevAttendancePeriodResolveView,
    IADevAsyncJobView,
    IADevChatView,
    IADevHealthView,
    IADevKnowledgeApproveView,
    IADevKnowledgeProposalView,
    IADevKnowledgeRejectView,
    IADevMemoryAuditView,
    IADevMemoryProposalApproveView,
    IADevMemoryProposalRejectView,
    IADevMemoryProposalView,
    IADevMemoryResetView,
    IADevObservabilitySummaryView,
    IADevTicketView,
    IADevUserMemoryView,
)

urlpatterns = [
    path("chat/", IADevChatView.as_view(), name="ia-dev-chat"),
    path("attendance/period/resolve/", IADevAttendancePeriodResolveView.as_view(), name="ia-dev-attendance-period-resolve"),
    path("memory/reset/", IADevMemoryResetView.as_view(), name="ia-dev-memory-reset"),
    path("memory/user/", IADevUserMemoryView.as_view(), name="ia-dev-memory-user"),
    path("memory/proposals/", IADevMemoryProposalView.as_view(), name="ia-dev-memory-proposals"),
    path("memory/proposals/approve/", IADevMemoryProposalApproveView.as_view(), name="ia-dev-memory-proposals-approve"),
    path("memory/proposals/reject/", IADevMemoryProposalRejectView.as_view(), name="ia-dev-memory-proposals-reject"),
    path("memory/audit/", IADevMemoryAuditView.as_view(), name="ia-dev-memory-audit"),
    path("health/", IADevHealthView.as_view(), name="ia-dev-health"),
    path("tickets/", IADevTicketView.as_view(), name="ia-dev-ticket-create"),
    path("knowledge/proposals/", IADevKnowledgeProposalView.as_view(), name="ia-dev-knowledge-proposal"),
    path("knowledge/proposals/approve/", IADevKnowledgeApproveView.as_view(), name="ia-dev-knowledge-approve"),
    path("knowledge/proposals/reject/", IADevKnowledgeRejectView.as_view(), name="ia-dev-knowledge-reject"),
    path("async/jobs/", IADevAsyncJobView.as_view(), name="ia-dev-async-job-status"),
    path("observability/summary/", IADevObservabilitySummaryView.as_view(), name="ia-dev-observability-summary"),
]
