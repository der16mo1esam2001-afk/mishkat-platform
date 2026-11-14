from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.middleware import RateLimiter, redact_sensitive_text
from app.security import (
    ALLOWED_ROLES,
    Principal,
    get_current_principal,
    issue_local_development_token,
    require_role,
)


def test_issue_local_development_token_roles():
    for role in ALLOWED_ROLES:
        uid = uuid4()
        token_data = issue_local_development_token(user_id=uid, role=role)
        assert token_data["role"] == role
        assert token_data["user_id"] == str(uid)
        assert token_data["token_type"] == "bearer"


def test_rbac_require_role_dependency():
    test_app = FastAPI()

    @test_app.get("/admin-only")
    def admin_route(principal: Principal = Depends(require_role("platform_admin"))):
        return {"status": "authorized", "user": str(principal.user_id)}

    @test_app.get("/operator-or-admin")
    def operator_route(principal: Principal = Depends(require_role("domain_operator", "platform_admin"))):
        return {"status": "authorized", "role": principal.role}

    with TestClient(test_app) as client:
        # 1. Learner trying to access admin-only: 403 Forbidden
        learner_token = issue_local_development_token(role="learner")
        res_learner = client.get("/admin-only", headers={"Authorization": f"Bearer {learner_token['access_token']}"})
        assert res_learner.status_code == 403
        assert "Insufficient permissions" in res_learner.json()["detail"]

        # 2. Admin accessing admin-only: 200 OK
        admin_token = issue_local_development_token(role="platform_admin")
        res_admin = client.get("/admin-only", headers={"Authorization": f"Bearer {admin_token['access_token']}"})
        assert res_admin.status_code == 200
        assert res_admin.json()["status"] == "authorized"

        # 3. Domain operator accessing operator-or-admin: 200 OK
        op_token = issue_local_development_token(role="domain_operator")
        res_op = client.get("/operator-or-admin", headers={"Authorization": f"Bearer {op_token['access_token']}"})
        assert res_op.status_code == 200


def test_rate_limiter_throttling():
    limiter = RateLimiter(requests_per_minute=5)
    client_ip = "192.168.1.100"

    for _ in range(5):
        assert limiter.is_allowed(client_ip) is True

    # 6th request within window must be rejected
    assert limiter.is_allowed(client_ip) is False


def test_redact_sensitive_text():
    sample_log = "Error occurred with api_key='sk-live-1234567890' and password='mySecretPassword' and Bearer eyJhbGciOiJIUzI1NiJ9.test"
    redacted = redact_sensitive_text(sample_log)
    assert "sk-live-1234567890" not in redacted
    assert "mySecretPassword" not in redacted
    assert "eyJhbGciOiJIUzI1NiJ9" not in redacted
    assert "[REDACTED]" in redacted
