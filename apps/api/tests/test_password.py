"""Unit tests for stdlib PBKDF2 password hashing."""
import unittest

from app.auth.password import hash_password, needs_rehash, verify_password


class TestHashPassword(unittest.TestCase):
    def test_rejects_empty_password(self):
        with self.assertRaises(ValueError):
            hash_password("")

    def test_hash_is_not_the_plaintext(self):
        hashed = hash_password("correct horse battery staple")
        self.assertNotIn("correct horse battery staple", hashed)

    def test_same_password_hashes_differently_each_time(self):
        # Salts must differ, so two hashes of the same password must too.
        h1 = hash_password("hunter2")
        h2 = hash_password("hunter2")
        self.assertNotEqual(h1, h2)


class TestVerifyPassword(unittest.TestCase):
    def test_correct_password_verifies(self):
        hashed = hash_password("hunter2")
        self.assertTrue(verify_password("hunter2", hashed))

    def test_incorrect_password_fails(self):
        hashed = hash_password("hunter2")
        self.assertFalse(verify_password("wrong password", hashed))

    def test_empty_candidate_against_real_hash_fails(self):
        hashed = hash_password("hunter2")
        self.assertFalse(verify_password("", hashed))

    def test_malformed_stored_hash_fails_closed_not_raises(self):
        self.assertFalse(verify_password("hunter2", "not-a-real-hash"))
        self.assertFalse(verify_password("hunter2", ""))
        self.assertFalse(verify_password("hunter2", "pbkdf2_sha256$notanumber$abc$def"))

    def test_wrong_algorithm_tag_fails(self):
        hashed = hash_password("hunter2")
        tampered = hashed.replace("pbkdf2_sha256", "md5", 1)
        self.assertFalse(verify_password("hunter2", tampered))

    def test_low_iteration_hash_still_verifies_correctly(self):
        hashed = hash_password("hunter2", iterations=1000)
        self.assertTrue(verify_password("hunter2", hashed))
        self.assertFalse(verify_password("wrong", hashed))


class TestNeedsRehash(unittest.TestCase):
    def test_current_default_does_not_need_rehash(self):
        hashed = hash_password("hunter2")
        self.assertFalse(needs_rehash(hashed))

    def test_low_iteration_hash_needs_rehash(self):
        hashed = hash_password("hunter2", iterations=1000)
        self.assertTrue(needs_rehash(hashed))

    def test_malformed_hash_needs_rehash(self):
        self.assertTrue(needs_rehash("garbage"))


if __name__ == "__main__":
    unittest.main()
