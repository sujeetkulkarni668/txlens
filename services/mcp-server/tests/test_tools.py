"""Unit tests for the MCP tool handlers, using a hand-written FakeClient
(configurable responses/exceptions) and InMemoryAuditLogger — no network,
no real backend needed."""
import unittest

import mcp_server.tools as tools
from mcp_server.audit import InMemoryAuditLogger
from mcp_server.client import TxLensAPIError
from mcp_server.schemas import PermissionClass


class FakeClient:
    def __init__(self, **responses):
        self._responses = responses
        self.calls: list[str] = []

    async def _resolve(self, name, *args):
        self.calls.append(name)
        value = self._responses.get(name)
        if isinstance(value, Exception):
            raise value
        return value

    async def get_wallet(self, address):
        return await self._resolve("get_wallet", address)

    async def get_contract(self, address):
        return await self._resolve("get_contract", address)

    async def get_token(self, address):
        return await self._resolve("get_token", address)

    async def simulate_transaction(self, tx):
        return await self._resolve("simulate_transaction", tx)

    async def analyze_transaction(self, tx):
        return await self._resolve("analyze_transaction", tx)

    async def create_policy(self, policy):
        return await self._resolve("create_policy", policy)


class TestReadOnlyTools(unittest.IsolatedAsyncioTestCase):
    async def test_inspect_wallet_success(self):
        client = FakeClient(get_wallet={"address": "0xabc", "balance_wei": "0"})
        audit = InMemoryAuditLogger()
        result = await tools.inspect_wallet(client, audit, address="0xabc")
        self.assertTrue(result.success)
        self.assertEqual(result.output["address"], "0xabc")
        self.assertEqual(len(audit.entries), 1)
        self.assertTrue(audit.entries[0].authorized)

    async def test_inspect_wallet_backend_error_is_structured_not_raised(self):
        client = FakeClient(get_wallet=TxLensAPIError(500, "internal error"))
        audit = InMemoryAuditLogger()
        result = await tools.inspect_wallet(client, audit, address="0xabc")
        self.assertFalse(result.success)
        self.assertIn("internal error", result.error)
        self.assertEqual(audit.entries[0].error, result.error)

    async def test_get_wallet_transactions_reports_not_implemented(self):
        client = FakeClient()
        audit = InMemoryAuditLogger()
        result = await tools.get_wallet_transactions(client, audit, address="0xabc")
        self.assertFalse(result.success)
        self.assertIn("not implemented", result.error)
        # never called the backend for a capability that doesn't exist
        self.assertEqual(client.calls, [])

    async def test_check_wallet_risk_reports_not_implemented(self):
        client = FakeClient()
        audit = InMemoryAuditLogger()
        result = await tools.check_wallet_risk(client, audit, address="0xabc")
        self.assertFalse(result.success)
        self.assertIn("not implemented", result.error)

    async def test_trace_transaction_extracts_only_trace_fields(self):
        client = FakeClient(
            simulate_transaction={
                "success": True, "gas_estimate": "21000", "trace_supported": True,
                "events": [{"type": "Transfer"}], "asset_changes": [], "approvals": [],
                "warnings": [],
            }
        )
        audit = InMemoryAuditLogger()
        result = await tools.trace_transaction(client, audit, transaction={"to": "0xabc"})
        self.assertTrue(result.success)
        self.assertEqual(set(result.output.keys()), {"trace_supported", "events", "asset_changes", "warnings"})
        self.assertNotIn("gas_estimate", result.output)

    async def test_check_policy_extracts_only_policy_field(self):
        client = FakeClient(
            analyze_transaction={"parsed": {}, "policy": {"decision": "ALLOW"}, "risk": {}}
        )
        audit = InMemoryAuditLogger()
        result = await tools.check_policy(client, audit, transaction={"to": "0xabc"})
        self.assertEqual(result.output, {"decision": "ALLOW"})

    async def test_create_security_report_marks_not_persisted(self):
        client = FakeClient(analyze_transaction={"parsed": {"tx_type": "native_transfer"}})
        audit = InMemoryAuditLogger()
        result = await tools.create_security_report(client, audit, transaction={"to": "0xabc"})
        self.assertTrue(result.success)
        self.assertFalse(result.output["persisted"])


class TestSensitiveTools(unittest.IsolatedAsyncioTestCase):
    async def test_create_policy_denied_without_authorization(self):
        client = FakeClient()
        audit = InMemoryAuditLogger()
        result = await tools.create_policy(
            client, audit, name="cap", rule_type="maximum_transaction_value",
            parameters={"max_value": 1.0}, authorized=False,
        )
        self.assertFalse(result.success)
        self.assertFalse(result.authorized)
        self.assertEqual(client.calls, [])  # never touched the backend
        self.assertEqual(audit.entries[0].permission_class, PermissionClass.SENSITIVE)
        self.assertFalse(audit.entries[0].authorized)

    async def test_create_policy_succeeds_with_authorization(self):
        client = FakeClient(create_policy={"id": "1", "name": "cap"})
        audit = InMemoryAuditLogger()
        result = await tools.create_policy(
            client, audit, name="cap", rule_type="maximum_transaction_value",
            parameters={"max_value": 1.0}, authorized=True,
        )
        self.assertTrue(result.success)
        self.assertEqual(client.calls, ["create_policy"])

    async def test_request_approval_denied_without_authorization(self):
        client = FakeClient()
        audit = InMemoryAuditLogger()
        result = await tools.request_approval(client, audit, transaction={"to": "0xabc"}, authorized=False)
        self.assertFalse(result.success)
        self.assertFalse(result.authorized)

    async def test_request_approval_reports_not_implemented_even_when_authorized(self):
        client = FakeClient()
        audit = InMemoryAuditLogger()
        result = await tools.request_approval(client, audit, transaction={"to": "0xabc"}, authorized=True)
        self.assertTrue(result.authorized)
        self.assertFalse(result.success)
        self.assertIn("not implemented", result.error)

    async def test_every_sensitive_call_is_audited_regardless_of_outcome(self):
        client = FakeClient(create_policy=TxLensAPIError(400, "bad request"))
        audit = InMemoryAuditLogger()
        await tools.create_policy(
            client, audit, name="x", rule_type="maximum_transaction_value",
            parameters={}, authorized=True,
        )
        self.assertEqual(len(audit.entries), 1)
        self.assertEqual(audit.entries[0].error, "bad request")


if __name__ == "__main__":
    unittest.main()
