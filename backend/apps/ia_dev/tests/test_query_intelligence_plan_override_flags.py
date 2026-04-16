from __future__ import annotations

import os
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ia_dev.application.orchestration.chat_application_service import (
    ChatApplicationService,
)


class QueryIntelligencePlanOverrideFlagTests(SimpleTestCase):
    def setUp(self):
        self.service = ChatApplicationService()
        self.base_candidates = [
            {
                "capability_id": "attendance.summary.by_supervisor.v1",
                "capability_exists": True,
                "rollout_enabled": True,
                "handler_key": "attendance.summary_by_supervisor",
                "policy_tags": ["contains_personal_data"],
                "legacy_intents": ["attendance_query"],
                "reason": "candidate_1",
                "source": {
                    "intent": "attendance_query",
                    "domain": "attendance",
                    "output_mode": "summary",
                    "needs_database": True,
                },
                "dictionary_hints": {},
                "candidate_rank": 1,
                "candidate_score": 100,
            }
        ]
        self.fallback_plan = dict(self.base_candidates[0])
        self.classification = {
            "intent": "attendance_query",
            "domain": "attendance",
            "output_mode": "summary",
            "needs_database": True,
        }
        self.query_intelligence = {
            "mode": "active",
            "execution_plan": {
                "capability_id": "attendance.trend.daily.v1",
                "constraints": {"period_scope": {"label": "ultimos_6_meses"}},
            },
        }

    def test_soft_mode_keeps_primary_candidate_and_appends_semantic_override(self):
        with patch.dict(
            os.environ,
            {
                "IA_DEV_QUERY_INTELLIGENCE_PLAN_OVERRIDE_MODE": "soft",
            },
            clear=False,
        ):
            plans = self.service._apply_query_intelligence_plan_overrides(
                candidate_plans=self.base_candidates,
                fallback_plan=self.fallback_plan,
                query_intelligence=self.query_intelligence,
                classification=self.classification,
            )
        self.assertEqual(str(plans[0].get("capability_id") or ""), "attendance.summary.by_supervisor.v1")
        capability_ids = [str(item.get("capability_id") or "") for item in plans]
        self.assertIn("attendance.trend.daily.v1", capability_ids)

    def test_hard_mode_replaces_primary_candidate(self):
        with patch.dict(
            os.environ,
            {
                "IA_DEV_QUERY_INTELLIGENCE_PLAN_OVERRIDE_MODE": "hard",
            },
            clear=False,
        ):
            plans = self.service._apply_query_intelligence_plan_overrides(
                candidate_plans=self.base_candidates,
                fallback_plan=self.fallback_plan,
                query_intelligence=self.query_intelligence,
                classification=self.classification,
            )
        self.assertEqual(str(plans[0].get("capability_id") or ""), "attendance.trend.daily.v1")

    def test_off_mode_does_not_override_candidate_order(self):
        with patch.dict(
            os.environ,
            {
                "IA_DEV_QUERY_INTELLIGENCE_PLAN_OVERRIDE_MODE": "off",
            },
            clear=False,
        ):
            plans = self.service._apply_query_intelligence_plan_overrides(
                candidate_plans=self.base_candidates,
                fallback_plan=self.fallback_plan,
                query_intelligence=self.query_intelligence,
                classification=self.classification,
            )
        self.assertEqual(len(plans), 1)
        self.assertEqual(str(plans[0].get("capability_id") or ""), "attendance.summary.by_supervisor.v1")

