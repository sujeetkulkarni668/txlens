"""Unit tests for the stdlib HS256 JWT implementation."""
import time
import unittest

from app.auth.jwt import ExpiredTokenError, InvalidTokenError, decode_jwt, encode_jwt

SECRET = "test-secret-key"


class TestEncodeDecodeRoundTrip(unittest.TestCase):
    def test_round_trip_preserves_claims(self):
        token = encode_jwt({"sub": "user-123", "role": "user"}, SECRET)
        claims = decode_jwt(token, SECRET)
        self.assertEqual(claims["sub"], "user-123")
        self.assertEqual(claims["role"], "user")

    def test_token_has_three_dot_separated_segments(self):
        token = encode_jwt({"sub": "user-123"}, SECRET)
        self.assertEqual(len(token.split(".")), 3)

    def test_iat_is_set_automatically(self):
        token = encode_jwt({"sub": "user-123"}, SECRET)
        claims = decode_jwt(token, SECRET)
        self.assertIn("iat", claims)
        self.assertAlmostEqual(claims["iat"], int(time.time()), delta=5)


class TestExpiry(unittest.TestCase):
    def test_unexpired_token_decodes(self):
        token = encode_jwt({"sub": "user-123"}, SECRET, expires_in_seconds=3600)
        claims = decode_jwt(token, SECRET)
        self.assertEqual(claims["sub"], "user-123")

    def test_expired_token_raises_expired_token_error(self):
        token = encode_jwt({"sub": "user-123"}, SECRET, expires_in_seconds=-1)
        with self.assertRaises(ExpiredTokenError):
            decode_jwt(token, SECRET)

    def test_no_expiry_means_no_expiry_check(self):
        token = encode_jwt({"sub": "user-123"}, SECRET)  # no expires_in_seconds
        claims = decode_jwt(token, SECRET)
        self.assertNotIn("exp", claims)


class TestTamperingIsRejected(unittest.TestCase):
    def test_wrong_secret_is_rejected(self):
        token = encode_jwt({"sub": "user-123"}, SECRET)
        with self.assertRaises(InvalidTokenError):
            decode_jwt(token, "a-different-secret")

    def test_tampered_payload_is_rejected(self):
        token = encode_jwt({"sub": "user-123", "role": "user"}, SECRET)
        header_b64, payload_b64, sig_b64 = token.split(".")

        # Forge a payload claiming admin, keeping the original signature.
        import base64
        import json

        forged_payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "user-123", "role": "admin"}).encode()
        ).rstrip(b"=").decode()
        forged_token = f"{header_b64}.{forged_payload}.{sig_b64}"

        with self.assertRaises(InvalidTokenError):
            decode_jwt(forged_token, SECRET)

    def test_malformed_token_missing_segments_is_rejected(self):
        with self.assertRaises(InvalidTokenError):
            decode_jwt("not.a.valid.jwt.at.all", SECRET)
        with self.assertRaises(InvalidTokenError):
            decode_jwt("onlyonesegment", SECRET)

    def test_alg_none_attack_is_rejected(self):
        # The classic JWT "alg: none" bypass — forge a token with no
        # signature at all and an empty signature segment.
        import base64
        import json

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "attacker", "role": "admin"}).encode()
        ).rstrip(b"=").decode()
        forged_token = f"{header}.{payload}."

        with self.assertRaises(InvalidTokenError):
            decode_jwt(forged_token, SECRET)

    def test_garbage_base64_does_not_crash_decoder(self):
        with self.assertRaises(InvalidTokenError):
            decode_jwt("!!!.###.$$$", SECRET)


if __name__ == "__main__":
    unittest.main()
