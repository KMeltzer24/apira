import os
import unittest

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg2://apira:apira@localhost:5432/apira"
)

from main import _password_matches  # noqa: E402


class PasswordCheckTests(unittest.TestCase):
    def test_accepts_bcrypt_hash_of_password(self):
        stored = "$2b$12$1Wae9KqBggLlzYE1tEr5oO4Y7jtlekYGbhbdJ9d/GcYisJenp8dnC"
        self.assertTrue(_password_matches(stored, "password"))
        self.assertFalse(_password_matches(stored, "wrong"))

    def test_rejects_plaintext_or_garbage(self):
        self.assertFalse(_password_matches("password", "password"))
        self.assertFalse(_password_matches("not-a-hash", "password"))


if __name__ == "__main__":
    unittest.main()
