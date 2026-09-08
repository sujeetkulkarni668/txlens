"""Unit tests for TxLensAPIClient — mocks urllib.request.urlopen, no real
network access needed."""
import json
import unittest
from unittest.mock import MagicMock, patch

from mcp_server.client import TxLensAPIClient, TxLensAPIError

BASE_URL = "http://localhost:8000"


def make_response(body: dict, status: int = 200):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(body).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False
    return mock_resp


class TestTxLensAPIClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TxLensAPIClient(BASE_URL)

    @patch("urllib.request.urlopen")
    async def test_get_wallet_sends_correct_request(self, mock_urlopen):
        mock_urlopen.return_value = make_response({"address": "0xabc", "balance_wei": "0"})
        result = await self.client.get_wallet("0xabc")
        self.assertEqual(result["address"], "0xabc")
        sent_request = mock_urlopen.call_args[0][0]
        self.assertEqual(sent_request.get_method(), "GET")
        self.assertTrue(sent_request.full_url.endswith("/api/v1/wallets/0xabc"))
        self.assertNotIn("Authorization", sent_request.headers)

    @patch("urllib.request.urlopen")
    async def test_api_token_is_sent_as_bearer_header(self, mock_urlopen):
        mock_urlopen.return_value = make_response({"decision": "ALLOW"})
        client = TxLensAPIClient(BASE_URL, api_token="test-token-123")
        await client.list_policies()
        sent_request = mock_urlopen.call_args[0][0]
        self.assertEqual(sent_request.headers.get("Authorization"), "Bearer test-token-123")

    @patch("urllib.request.urlopen")
    async def test_set_api_token_updates_subsequent_requests(self, mock_urlopen):
        mock_urlopen.return_value = make_response({"decision": "ALLOW"})
        client = TxLensAPIClient(BASE_URL)
        client.set_api_token("new-token")
        await client.list_policies()
        sent_request = mock_urlopen.call_args[0][0]
        self.assertEqual(sent_request.headers.get("Authorization"), "Bearer new-token")

    @patch("urllib.request.urlopen")
    async def test_create_policy_sends_post_with_body(self, mock_urlopen):
        mock_urlopen.return_value = make_response({"id": "1", "name": "cap"})
        await self.client.create_policy({"name": "cap", "rule_type": "maximum_transaction_value"})
        sent_request = mock_urlopen.call_args[0][0]
        self.assertEqual(sent_request.get_method(), "POST")
        body = json.loads(sent_request.data)
        self.assertEqual(body["name"], "cap")

    @patch("urllib.request.urlopen")
    async def test_http_error_raises_txlens_api_error_with_detail(self, mock_urlopen):
        import urllib.error

        error_body = json.dumps({"detail": "policy not found"}).encode("utf-8")
        http_error = urllib.error.HTTPError(
            url=BASE_URL, code=404, msg="Not Found", hdrs=None, fp=None
        )
        http_error.read = lambda: error_body
        mock_urlopen.side_effect = http_error

        with self.assertRaises(TxLensAPIError) as ctx:
            await self.client.get_wallet("0xabc")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.message)

    @patch("urllib.request.urlopen")
    async def test_unreachable_backend_raises_txlens_api_error(self, mock_urlopen):
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        with self.assertRaises(TxLensAPIError) as ctx:
            await self.client.get_wallet("0xabc")
        self.assertIsNone(ctx.exception.status_code)


if __name__ == "__main__":
    unittest.main()
