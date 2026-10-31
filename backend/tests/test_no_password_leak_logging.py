"""Regression tests: authentication code paths must never log plaintext
passwords or password-hash fragments, per the security scan follow-up.
"""
import logging

from app.utils.auth_system import AuthGuard


SECRET_PASSWORD = "Sup3r$ecretPassw0rd!"


def test_verify_password_success_does_not_log_secret(caplog):
    guard = AuthGuard()
    hashed = guard.hash_password(SECRET_PASSWORD)
    with caplog.at_level(logging.DEBUG):
        assert guard.verify_password(SECRET_PASSWORD, hashed) is True
    haystack = "\n".join(record.getMessage() for record in caplog.records)
    assert SECRET_PASSWORD not in haystack
    assert hashed not in haystack
    assert hashed[:20] not in haystack


def test_verify_password_failure_does_not_log_secret(caplog):
    guard = AuthGuard()
    hashed = guard.hash_password(SECRET_PASSWORD)
    with caplog.at_level(logging.DEBUG):
        assert guard.verify_password("WrongPassword123!", hashed) is False
    haystack = "\n".join(record.getMessage() for record in caplog.records)
    assert SECRET_PASSWORD not in haystack
    assert "WrongPassword123!" not in haystack
    assert hashed not in haystack
    assert hashed[:20] not in haystack


def test_verify_password_malformed_hash_does_not_log_secret(caplog):
    guard = AuthGuard()
    malformed_hash = "not-a-real-bcrypt-hash-$2b$12$abcdefghijklmnopqrstuv"
    with caplog.at_level(logging.DEBUG):
        assert guard.verify_password(SECRET_PASSWORD, malformed_hash) is False
    haystack = "\n".join(record.getMessage() for record in caplog.records)
    assert SECRET_PASSWORD not in haystack
    assert malformed_hash not in haystack
