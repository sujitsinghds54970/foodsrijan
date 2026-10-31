import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app import database
from app.main import app


def test_connection_accepts_sqlalchemy_two(monkeypatch):
    engine = create_engine("sqlite://", poolclass=QueuePool)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine))
    try:
        assert database.test_connection() is True
        assert engine.pool.checkedout() == 0
    finally:
        engine.dispose()


def test_connection_failure_closes_session_and_logs(monkeypatch, caplog):
    class FailingSession:
        closed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

        def execute(self, statement):
            raise OperationalError("SELECT 1", {}, RuntimeError("Database unavailable"))

    session = FailingSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)
    with caplog.at_level(logging.ERROR):
        assert database.test_connection() is False
    assert session.closed
    assert "Database connection check failed" in caplog.text


@pytest.mark.parametrize("available,status_code,status,database_status", [
    (True, 200, "healthy", "available"),
    (False, 503, "unhealthy", "unavailable"),
])
def test_health_reports_database_availability(monkeypatch, available, status_code, status, database_status):
    monkeypatch.setattr("app.main.test_connection", lambda: available)
    response = TestClient(app).get("/health")
    assert response.status_code == status_code
    assert response.json()["status"] == status
    assert response.json()["database"] == database_status
    assert response.json()["timestamp"]
