"""Unit tests for EVMRPCProvider.

Mocks urllib.request.urlopen (stdlib unittest.mock) so these run without any
real network access and without installing anything.
"""
import json
import unittest
from unittest.mock import MagicMock, patch

from app.blockchain.exceptions import RpcError, RpcTransportError
from app.blockchain.evm_rpc_provider import EVMRPCProvider

RPC_URL = "https://sepolia.base.org"


def make_response(result=None, error=None):
    """Build a mock context-manager response matching urlopen()'s shape."""
    body = {"jsonrpc": "2.0", "id": 1}
    if error is not None:
        body["error"] = error
    else:
        body["result"] = result
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(body).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False
    return mock_resp


class TestEVMRPCProvider(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.provider = EVMRPCProvider(RPC_URL)

    def test_requires_rpc_url(self):
        with self.assertRaises(ValueError):
            EVMRPCProvider("")

    @patch("urllib.request.urlopen")
    async def test_get_balance_decodes_hex(self, mock_urlopen):
        mock_urlopen.return_value = make_response(result="0x1bc16d674ec80000")  # 2 * 10**18
        balance = await self.provider.get_balance("0xabc")
        self.assertEqual(balance, 2_000_000_000_000_000_000)
        # Verify the JSON-RPC request shape sent over the wire.
        sent_request = mock_urlopen.call_args[0][0]
        sent_body = json.loads(sent_request.data)
        self.assertEqual(sent_body["method"], "eth_getBalance")
        self.assertEqual(sent_body["params"], ["0xabc", "latest"])

    @patch("urllib.request.urlopen")
    async def test_get_transaction_returns_none_when_missing(self, mock_urlopen):
        mock_urlopen.return_value = make_response(result=None)
        tx = await self.provider.get_transaction("0xdeadbeef")
        self.assertIsNone(tx)

    @patch("urllib.request.urlopen")
    async def test_get_transaction_parses_fields(self, mock_urlopen):
        mock_urlopen.return_value = make_response(
            result={
                "hash": "0xabc123",
                "from": "0xfrom",
                "to": "0xto",
                "value": "0xde0b6b3a7640000",  # 1e18
                "input": "0x",
                "blockNumber": "0xa",
                "nonce": "0x5",
                "gas": "0x5208",
                "gasPrice": "0x3b9aca00",
            }
        )
        tx = await self.provider.get_transaction("0xabc123")
        self.assertEqual(tx.hash, "0xabc123")
        self.assertEqual(tx.value, "1000000000000000000")
        self.assertEqual(tx.block_number, 10)
        self.assertEqual(tx.nonce, 5)

    @patch("urllib.request.urlopen")
    async def test_rpc_error_raised(self, mock_urlopen):
        mock_urlopen.return_value = make_response(
            error={"code": -32602, "message": "invalid params"}
        )
        with self.assertRaises(RpcError) as ctx:
            await self.provider.get_balance("0xabc")
        self.assertEqual(ctx.exception.code, -32602)

    @patch("urllib.request.urlopen")
    async def test_call_revert_returns_failed_call_result_not_exception(self, mock_urlopen):
        mock_urlopen.return_value = make_response(
            error={"code": 3, "message": "execution reverted: insufficient balance"}
        )
        result = await self.provider.call(to="0xcontract", data="0x12345678")
        self.assertFalse(result.success)
        self.assertIn("insufficient balance", result.error)

    @patch("urllib.request.urlopen")
    async def test_transport_error_wrapped(self, mock_urlopen):
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        with self.assertRaises(RpcTransportError):
            await self.provider.get_balance("0xabc")

    @patch("urllib.request.urlopen")
    async def test_get_code_returns_0x_for_eoa(self, mock_urlopen):
        mock_urlopen.return_value = make_response(result="0x")
        code = await self.provider.get_code("0xsomeeoa")
        self.assertEqual(code, "0x")

    @patch("urllib.request.urlopen")
    async def test_get_block_not_found_raises(self, mock_urlopen):
        mock_urlopen.return_value = make_response(result=None)
        with self.assertRaises(RpcError):
            await self.provider.get_block("0x999999")


if __name__ == "__main__":
    unittest.main()
