from .domain_context_loader import DomainContextLoader
from .domain_registry import DomainDescriptor, DomainRegistry
from .task_aggregator import TaskAggregator
from .task_contracts import (
    AggregatedResponse,
    DelegationResult,
    DelegationTask,
    EntityScope,
    build_task_id,
)
from .task_planner import TaskPlanner

__all__ = [
    "AggregatedResponse",
    "DelegationCoordinator",
    "DelegationResult",
    "DelegationTask",
    "DomainContextLoader",
    "DomainDescriptor",
    "DomainRegistry",
    "EntityScope",
    "TaskAggregator",
    "TaskPlanner",
    "build_task_id",
]


def __getattr__(name: str):
    if name == "DelegationCoordinator":
        from .delegation_coordinator import DelegationCoordinator

        return DelegationCoordinator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
