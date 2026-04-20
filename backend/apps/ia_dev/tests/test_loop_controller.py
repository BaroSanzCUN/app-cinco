from __future__ import annotations

from django.test import SimpleTestCase

from apps.ia_dev.application.orchestration.loop_controller import LoopController
from apps.ia_dev.application.orchestration.termination_policy import (
    TerminationPolicy,
    TerminationPolicyConfig,
)


class LoopControllerTests(SimpleTestCase):
    def setUp(self):
        self.controller = LoopController(
            termination_policy=TerminationPolicy(
                config=TerminationPolicyConfig(
                    max_total_cycles=3,
                    max_same_plan_retries=1,
                    max_replans=1,
                    max_llm_review_passes=2,
                    approve_threshold=0.85,
                    retry_same_plan_threshold=0.60,
                    replan_threshold=0.45,
                )
            )
        )

    @staticmethod
    def _satisfaction(*, score: float, approved: bool, issues: list[dict] | None = None) -> dict:
        return {
            "satisfied": bool(approved),
            "reason": "ok" if approved else "not_ok",
            "checks": {},
            "satisfaction_review_gate": {
                "approved": bool(approved),
                "satisfaction_score": float(score),
                "issues": list(issues or []),
                "evidence_sufficient": True,
                "technical_leak_detected": False,
            },
        }

    def test_approves_in_first_cycle(self):
        decision = self.controller.evaluate_cycle(
            cycle_index=1,
            strategy="capability",
            planned_capability={"capability_id": "empleados.count.active.v1"},
            route={"policy_allowed": True, "policy_action": "allow"},
            execution={"ok": True, "error": ""},
            satisfaction=self._satisfaction(score=0.9, approved=True),
            history=[],
            same_plan_retries=0,
            replans_used=0,
            llm_review_passes=0,
        )
        self.assertEqual(str(decision.decision or ""), "approved")

    def test_retry_same_plan_only_once(self):
        first = self.controller.evaluate_cycle(
            cycle_index=1,
            strategy="capability",
            planned_capability={"capability_id": "attendance.unjustified.summary.v1"},
            route={"policy_allowed": True, "policy_action": "allow"},
            execution={"ok": True, "error": ""},
            satisfaction=self._satisfaction(score=0.7, approved=False, issues=[{"code": "semantic_mismatch"}]),
            history=[],
            same_plan_retries=0,
            replans_used=0,
            llm_review_passes=0,
        )
        self.assertEqual(str(first.decision or ""), "retry_same_plan")

        second = self.controller.evaluate_cycle(
            cycle_index=2,
            strategy="capability",
            planned_capability={"capability_id": "attendance.unjustified.summary.v1"},
            route={"policy_allowed": True, "policy_action": "allow"},
            execution={"ok": True, "error": ""},
            satisfaction=self._satisfaction(score=0.7, approved=False, issues=[{"code": "semantic_mismatch"}]),
            history=[first.as_dict()],
            same_plan_retries=1,
            replans_used=0,
            llm_review_passes=0,
        )
        self.assertNotEqual(str(second.decision or ""), "retry_same_plan")

    def test_replan_only_once(self):
        first = self.controller.evaluate_cycle(
            cycle_index=1,
            strategy="capability",
            planned_capability={"capability_id": "attendance.unjustified.summary.v1"},
            route={"policy_allowed": True, "policy_action": "allow"},
            execution={"ok": True, "error": ""},
            satisfaction=self._satisfaction(score=0.5, approved=False, issues=[{"code": "semantic_mismatch"}]),
            history=[],
            same_plan_retries=1,
            replans_used=0,
            llm_review_passes=0,
        )
        self.assertEqual(str(first.decision or ""), "replan")

        second = self.controller.evaluate_cycle(
            cycle_index=2,
            strategy="capability",
            planned_capability={"capability_id": "attendance.trend.daily.v1"},
            route={"policy_allowed": True, "policy_action": "allow"},
            execution={"ok": True, "error": ""},
            satisfaction=self._satisfaction(score=0.5, approved=False, issues=[{"code": "semantic_mismatch"}]),
            history=[first.as_dict()],
            same_plan_retries=1,
            replans_used=1,
            llm_review_passes=0,
        )
        self.assertNotEqual(str(second.decision or ""), "replan")

    def test_stop_for_no_improvement(self):
        history = [
            {
                "cycle_index": 1,
                "satisfaction_score": 0.72,
                "gate_status": "rejected",
                "metadata": {"error_signature": "", "issues": ["semantic_mismatch"]},
            },
            {
                "cycle_index": 2,
                "satisfaction_score": 0.70,
                "gate_status": "rejected",
                "metadata": {"error_signature": "", "issues": ["semantic_mismatch"]},
            },
        ]
        decision = self.controller.evaluate_cycle(
            cycle_index=3,
            strategy="capability",
            planned_capability={"capability_id": "attendance.unjustified.summary.v1"},
            route={"policy_allowed": True, "policy_action": "allow"},
            execution={"ok": True, "error": ""},
            satisfaction=self._satisfaction(score=0.68, approved=False, issues=[{"code": "semantic_mismatch"}]),
            history=history,
            same_plan_retries=1,
            replans_used=1,
            llm_review_passes=0,
        )
        self.assertEqual(str(decision.decision or ""), "stop")
        self.assertEqual(str(decision.stop_reason or ""), "no_improvement")

    def test_stop_for_same_error_repeated(self):
        history = [
            {
                "cycle_index": 1,
                "satisfaction_score": 0.65,
                "gate_status": "rejected",
                "metadata": {"error_signature": "timeout_error", "issues": []},
            }
        ]
        decision = self.controller.evaluate_cycle(
            cycle_index=2,
            strategy="capability",
            planned_capability={"capability_id": "attendance.unjustified.summary.v1"},
            route={"policy_allowed": True, "policy_action": "allow"},
            execution={"ok": False, "error": "timeout_error"},
            satisfaction=self._satisfaction(score=0.62, approved=False, issues=[]),
            history=history,
            same_plan_retries=0,
            replans_used=0,
            llm_review_passes=0,
        )
        self.assertEqual(str(decision.decision or ""), "stop")
        self.assertEqual(str(decision.stop_reason or ""), "same_error_repeated")

