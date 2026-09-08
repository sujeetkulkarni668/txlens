"""Unit tests for the sensitive-tool authorization gate."""
import unittest

from mcp_server.authorization import check_authorization
from mcp_server.schemas import PermissionClass


class TestCheckAuthorization(unittest.TestCase):
    def test_read_only_never_requires_authorization(self):
        self.assertIsNone(
            check_authorization(permission_class=PermissionClass.READ_ONLY, authorized=False)
        )

    def test_sensitive_without_authorization_is_denied(self):
        reason = check_authorization(permission_class=PermissionClass.SENSITIVE, authorized=False)
        self.assertIsNotNone(reason)
        self.assertIn("authorization", reason)

    def test_sensitive_with_authorization_is_allowed(self):
        self.assertIsNone(
            check_authorization(permission_class=PermissionClass.SENSITIVE, authorized=True)
        )


if __name__ == "__main__":
    unittest.main()
