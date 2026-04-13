from __future__ import annotations

from django.test import SimpleTestCase

from apps.ia_dev.application.policies.approval_policy_service import ApprovalPolicyService


class ApprovalPolicyServiceTests(SimpleTestCase):
    def test_business_requires_approval(self):
        service = ApprovalPolicyService()
        self.assertTrue(service.requires_approval_for_scope("business"))
        self.assertTrue(service.requires_approval_for_scope("general"))
        self.assertFalse(service.requires_approval_for_scope("user"))

    def test_role_permissions_from_policy(self):
        service = ApprovalPolicyService()
        self.assertTrue(service.can_review(scope="business", role="admin", action="approve"))
        self.assertTrue(service.can_review(scope="business", role="governance", action="reject"))
        self.assertFalse(service.can_review(scope="business", role="user", action="approve"))
