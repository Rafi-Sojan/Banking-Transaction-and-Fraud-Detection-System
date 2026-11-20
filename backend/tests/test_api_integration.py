"""Database-backed API workflow coverage.

The test is skipped for developer machines without DATABASE_URL. CI provisions
PostgreSQL and the C++ executable before running it.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

if not os.getenv("DATABASE_URL"):
    pytest.skip("DATABASE_URL is not configured", allow_module_level=True)

from app.databases.postgres import get_connection
from app.main import app
from app.utils.security import hash_password


def test_transfer_investigation_and_reversal_workflow() -> None:
    username = f"integration_{uuid4().hex[:12]}"
    password = "integration-password-123"
    idempotency_prefix = f"integration-{uuid4().hex}"
    transaction_ids: list[int] = []
    alert_ids: list[int] = []
    investigation_ids: list[int] = []
    user_id: int | None = None

    with get_connection() as connection:
        role = connection.execute("SELECT role_id FROM role WHERE role_name = 'investigator'").fetchone()
        row = connection.execute(
            "INSERT INTO app_user (username, password_hash, role_id) VALUES (%s, %s, %s) RETURNING user_id",
            (username, hash_password(password), role["role_id"]),
        ).fetchone()
        user_id = int(row["user_id"])

    try:
        client = TestClient(app)
        login = client.post("/api/v1/auth/login", json={"username": username, "password": password})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        accounts = client.get("/api/v1/accounts", headers=headers)
        assert accounts.status_code == 200, accounts.text
        source_id = accounts.json()[0]["account_id"]
        destination_id = accounts.json()[1]["account_id"]

        low_key = f"{idempotency_prefix}-low"
        low = client.post(
            "/api/v1/transactions/transfers",
            headers=headers,
            json={"source_account_id": source_id, "destination_account_id": destination_id, "amount": "10.00", "idempotency_key": low_key},
        )
        assert low.status_code == 201, low.text
        low_id = low.json()["transaction"]["transaction_id"]
        transaction_ids.append(low_id)
        assert low.json()["transaction"]["status"] == "completed"

        reversal = client.post(
            f"/api/v1/transactions/{low_id}/reverse",
            headers={**headers, "Idempotency-Key": f"{idempotency_prefix}-reverse"},
            json={"reason": "integration cleanup"},
        )
        assert reversal.status_code == 200, reversal.text
        reversal_id = reversal.json()["transaction"]["transaction_id"]
        transaction_ids.append(reversal_id)
        assert reversal.json()["transaction"]["status"] == "completed"

        risk_features = {
            "merchant_category": "crypto",
            "country": "IN",
            "home_country": "US",
            "transaction_count_10m": 5,
            "failed_attempts_1h": 3,
            "account_age_days": 1,
            "is_new_device": True,
            "is_new_location": True,
        }
        high = client.post(
            "/api/v1/transactions/transfers",
            headers=headers,
            json={
                "source_account_id": source_id,
                "destination_account_id": destination_id,
                "amount": "6000.00",
                "idempotency_key": f"{idempotency_prefix}-high",
                "features": risk_features,
            },
        )
        assert high.status_code == 201, high.text
        high_body = high.json()
        high_id = high_body["transaction"]["transaction_id"]
        transaction_ids.append(high_id)
        alert_ids.append(high_body["alert_id"])
        assert high_body["transaction"]["status"] == "held"

        opened = client.post(
            f"/api/v1/fraud/alerts/{high_body['alert_id']}/investigations",
            headers=headers,
            json={"notes": "integration review"},
        )
        assert opened.status_code == 201, opened.text
        investigation_id = opened.json()["investigation_id"]
        investigation_ids.append(investigation_id)

        assigned = client.patch(
            f"/api/v1/fraud/investigations/{investigation_id}/assignment",
            headers=headers,
            json={"assigned_user_id": user_id, "investigation_status": "in_progress"},
        )
        assert assigned.status_code == 200, assigned.text
        action = client.post(
            f"/api/v1/fraud/investigations/{investigation_id}/actions",
            headers=headers,
            json={"action_type": "reviewed", "notes": "rule evidence checked"},
        )
        assert action.status_code == 201, action.text
        closed = client.post(
            f"/api/v1/fraud/investigations/{investigation_id}/close",
            headers=headers,
            json={"outcome": "inconclusive", "notes": "integration complete"},
        )
        assert closed.status_code == 200, closed.text
        assert closed.json()["investigation_status"] == "closed"

        declined = client.post(
            f"/api/v1/transactions/{high_id}/decline",
            headers=headers,
            json={"reason": "integration decline"},
        )
        assert declined.status_code == 200, declined.text
        assert declined.json()["transaction"]["status"] == "declined"

        second_high = client.post(
            "/api/v1/transactions/transfers",
            headers=headers,
            json={
                "source_account_id": source_id,
                "destination_account_id": destination_id,
                "amount": "6000.00",
                "idempotency_key": f"{idempotency_prefix}-approve",
                "features": risk_features,
            },
        )
        assert second_high.status_code == 201, second_high.text
        second_body = second_high.json()
        second_id = second_body["transaction"]["transaction_id"]
        transaction_ids.append(second_id)
        alert_ids.append(second_body["alert_id"])
        approved = client.post(f"/api/v1/transactions/{second_id}/approve", headers=headers)
        assert approved.status_code == 200, approved.text
        assert approved.json()["transaction"]["status"] == "completed"
        second_reversal = client.post(
            f"/api/v1/transactions/{second_id}/reverse",
            headers={**headers, "Idempotency-Key": f"{idempotency_prefix}-approve-reverse"},
            json={},
        )
        assert second_reversal.status_code == 200, second_reversal.text
        transaction_ids.append(second_reversal.json()["transaction"]["transaction_id"])
    finally:
        with get_connection() as connection:
            if investigation_ids:
                connection.execute("DELETE FROM investigation_action WHERE investigation_id = ANY(%s)", (investigation_ids,))
                connection.execute("DELETE FROM investigation WHERE investigation_id = ANY(%s)", (investigation_ids,))
            if alert_ids:
                connection.execute("DELETE FROM fraud_rule_result WHERE alert_id = ANY(%s)", (alert_ids,))
                connection.execute("DELETE FROM fraud_alert WHERE alert_id = ANY(%s)", (alert_ids,))
            if transaction_ids:
                connection.execute("DELETE FROM transactions WHERE transaction_id = ANY(%s)", (transaction_ids,))
            if user_id is not None:
                connection.execute("DELETE FROM audit_log WHERE user_id = %s", (user_id,))
                connection.execute("DELETE FROM app_user WHERE user_id = %s", (user_id,))


def test_administrator_provisions_user_and_registers_model() -> None:
    admin_username = f"admin_{uuid4().hex[:12]}"
    provisioned_username = f"provisioned_{uuid4().hex[:12]}"
    admin_password = "administrator-password-123"
    provisioned_user_id: int | None = None
    admin_id: int | None = None
    model_id: int | None = None

    with get_connection() as connection:
        role = connection.execute("SELECT role_id FROM role WHERE role_name = 'administrator'").fetchone()
        row = connection.execute(
            "INSERT INTO app_user (username, password_hash, role_id) VALUES (%s, %s, %s) RETURNING user_id",
            (admin_username, hash_password(admin_password), role["role_id"]),
        ).fetchone()
        admin_id = int(row["user_id"])

    try:
        client = TestClient(app)
        login = client.post("/api/v1/auth/login", json={"username": admin_username, "password": admin_password})
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        created = client.post(
            "/api/v1/auth/users",
            headers=headers,
            json={"username": provisioned_username, "password": "provisioned-password-123", "role_name": "investigator"},
        )
        assert created.status_code == 201, created.text
        provisioned_user_id = created.json()["user_id"]

        model = client.post(
            "/api/v1/models",
            headers=headers,
            json={
                "model_name": f"integration-model-{uuid4().hex[:8]}",
                "version": "0.0.1",
                "model_path": "ml/models/not-trained-integration.joblib",
                "deployment_status": "offline",
                "metadata": {"test": True},
            },
        )
        assert model.status_code == 201, model.text
        model_id = model.json()["model_id"]
        listed = client.get("/api/v1/models", headers=headers)
        assert listed.status_code == 200, listed.text
        assert any(item["model_id"] == model_id for item in listed.json())
    finally:
        with get_connection() as connection:
            if model_id is not None:
                connection.execute("DELETE FROM audit_log WHERE entity_type = 'ml_model' AND entity_id = %s", (model_id,))
                connection.execute("DELETE FROM ml_model WHERE model_id = %s", (model_id,))
            if provisioned_user_id is not None:
                connection.execute("DELETE FROM audit_log WHERE entity_type = 'app_user' AND entity_id = %s", (provisioned_user_id,))
                connection.execute("DELETE FROM app_user WHERE user_id = %s", (provisioned_user_id,))
            if admin_id is not None:
                connection.execute("DELETE FROM audit_log WHERE user_id = %s", (admin_id,))
                connection.execute("DELETE FROM app_user WHERE user_id = %s", (admin_id,))
