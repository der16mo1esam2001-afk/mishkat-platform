from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_five_independent_database_migrations_exist():
    domains = {"vitalis", "aquanex", "agronex", "energis", "nexora"}
    for domain in domains:
        migration = ROOT / "database" / domain / "02-schema.sql"
        assert migration.exists(), f"Missing database schema for {domain}"
        text = migration.read_text(encoding="utf-8")
        assert "ENABLE ROW LEVEL SECURITY" in text
        assert "FORCE ROW LEVEL SECURITY" in text
        assert "owner_id = app_private.current_user_id()" in text
        assert "BYPASSRLS" not in text


def test_domain_database_urls_are_separate_in_compose():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for name in ("vitalis", "aquanex", "agronex", "energis", "nexora"):
        assert f"{name}_data:" in compose
        assert f"{name}-db:" in compose
        assert f"{name.upper()}_DB_URL" in compose
        assert f"@{name}-db:5432/{name}" in compose


def test_no_real_world_fake_kpis_in_dashboard():
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "لا تُعرض بيانات افتراضية" in html
    assert "بانتظار الاتصال" in html
    assert "86%" not in html and "92%" not in html


def test_nasa_connector_is_documented_and_validates_missing_values():
    backend = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    assert "/connectors/nasa-power/fetch" in backend
    assert "ALLSKY_SFC_SW_DWN" in backend
    assert "-999" in backend
    assert "NASA POWER Daily API" in backend


def test_source_registry_contains_all_critical_public_sources():
    catalog = (ROOT / "backend" / "app" / "catalog.py").read_text(encoding="utf-8")
    for source in ("WHO Global Health Observatory", "Aqueduct 4.0", "FAOSTAT API", "FAO WaPOR v3", "NASA POWER Daily API", "Ember Data API", "UNESCO Institute for Statistics"):
        assert source in catalog


def test_dev_auth_is_separate_from_production_auth_mode():
    security = (ROOT / "backend" / "app" / "security.py").read_text(encoding="utf-8")
    assert "settings.auth_mode == \"development\"" in security
    assert "settings.auth_mode == \"supabase_jwks\"" in security
    assert "settings.dev_auth_enabled" in security


def test_api_liveness_and_explicit_unconfigured_ai():
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        home = client.get("/")
        assert home.status_code == 200 and "MISHKAT" in home.text
        manifest = client.get("/manifest.webmanifest")
        assert manifest.status_code == 200 and manifest.json()["display"] == "standalone"
        sw = client.get("/sw.js")
        assert sw.status_code == 200 and "api/" in sw.text
        live = client.get("/api/v1/health/live")
        assert live.status_code == 200
        token = client.post("/api/v1/auth/dev-token")
        assert token.status_code == 200
        headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
        ai = client.get("/api/v1/ai/status", headers=headers)
        assert ai.status_code == 200
        assert ai.json()["status"] == "not_configured"
        bad_ag = client.post("/api/v1/connectors/nasa-power/fetch", headers=headers, json={"latitude": 30, "longitude": 31, "start_date": "2026-10-01", "end_date": "2026-10-02", "community": "AG", "parameters": ["ALLSKY_SFC_SW_DWN"]})
        assert bad_ag.status_code == 422
        bad_re = client.post("/api/v1/connectors/nasa-power/fetch", headers=headers, json={"latitude": 30, "longitude": 31, "start_date": "2026-10-01", "end_date": "2026-10-02", "community": "RE", "parameters": ["T2M"]})
        assert bad_re.status_code == 422
        sources = client.get("/api/v1/evidence/sources", headers=headers)
        assert sources.status_code == 200
        assert len(sources.json()["items"]) >= 7


def test_pwa_does_not_cache_api_or_sensitive_responses():
    sw = (ROOT / "frontend" / "sw.js").read_text(encoding="utf-8")
    assert "url.pathname.startsWith('/api/')" in sw
    assert "Never cache API responses" in sw
    assert "caches.match" in sw


def test_common_provenance_and_model_registry_are_isolated():
    for domain in ("vitalis", "aquanex", "agronex", "energis", "nexora"):
        sql = (ROOT / "database" / domain / "02-schema.sql").read_text(encoding="utf-8")
        for table in ("ingestion_runs", "model_registry"):
            assert f"CREATE TABLE IF NOT EXISTS public.{table}" in sql
            assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY" in sql
            assert f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in (ROOT / "database" / "common_rls.sql").read_text(encoding="utf-8")


def test_nasa_import_is_linked_to_an_ingestion_run_and_audit_event():
    backend = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    assert "INSERT INTO public.ingestion_runs" in backend
    assert "ingestion_run_id" in backend
    assert "INSERT INTO public.audit_events" in backend
    assert "status='completed'" in backend


def test_foreign_keys_enforce_owner_boundary():
    for domain in ("vitalis", "aquanex", "agronex", "energis", "nexora"):
        sql = (ROOT / "database" / domain / "02-schema.sql").read_text(encoding="utf-8")
        # Domain tables must not use a naked id-only FK to another tenant-owned table.
        assert not re.search(r"REFERENCES public\.[a-z_]+\(id\)", sql)
        assert "FOREIGN KEY (owner_id," in sql or domain == "aquanex"


def test_new_workspace_activity_and_nexora_routes_are_present():
    backend = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    for route in (
        "/modules/{domain}/activity",
        "/nexora/profile",
        "/nexora/goals",
        "/nexora/paths",
    ):
        assert route in backend
    assert "profile_consent_recorded" in backend
    assert "learning_goal_created" in backend
    assert "learning_path_created" in backend


def test_production_settings_reject_development_auth():
    import pytest
    from pydantic import ValidationError
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from app.settings import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production", auth_mode="development", dev_auth_enabled=True)


def test_security_headers_and_api_no_store():
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["cache-control"] == "no-store, max-age=0"
        assert response.headers.get("x-request-id")


def test_nexora_profile_requires_adult_confirmation_and_explicit_consent():
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        token = client.post("/api/v1/auth/dev-token")
        headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
        response = client.put("/api/v1/nexora/profile", headers=headers, json={
            "display_name": "Test Learner", "locale": "ar-EG",
            "adult_confirmed": False, "consent_confirmed": False, "consent_policy_version": "2026-11-14-v1",
        })
        assert response.status_code == 422
        assert "adults only" in response.json()["detail"]


def test_nexora_profile_goals_and_paths_use_owner_scoped_queries(monkeypatch):
    from contextlib import contextmanager
    import sys
    from uuid import UUID
    sys.path.insert(0, str(ROOT / "backend"))
    from fastapi.testclient import TestClient
    from app.database import db_hub
    from app.main import app

    captured = []
    learner_id = "11111111-1111-4111-8111-111111111111"
    def row(**values):
        return values

    class FakeResult:
        def __init__(self, one=None, many=None):
            self.one = one
            self.many = many or []
        def fetchone(self):
            return self.one
        def fetchall(self):
            return self.many

    class FakeConnection:
        def execute(self, query, params=None):
            compact = " ".join(query.split())
            captured.append((compact, params))
            if "INSERT INTO public.learner_profiles" in compact:
                return FakeResult(row(id=UUID(learner_id), display_name="Test Learner", locale="ar-EG", age_band=None, accessibility_preferences={}, consent_status="granted", created_at="2026-11-14T00:00:00Z", updated_at="2026-11-14T00:00:00Z"))
            if "SELECT id, consent_status FROM public.learner_profiles" in compact:
                return FakeResult(row(id=UUID(learner_id), consent_status="granted"))
            if "INSERT INTO public.learning_goals" in compact:
                return FakeResult(row(id=UUID("22222222-2222-4222-8222-222222222222"), title="Learn Python", domain="Programming", target_date=None, status="active", created_at="2026-11-14T00:00:00Z"))
            if "INSERT INTO public.learning_paths" in compact:
                return FakeResult(row(id=UUID("33333333-3333-4333-8333-333333333333"), title="Python Foundations", domain="Programming", objective="Build a small verified application", status="draft", created_at="2026-11-14T00:00:00Z"))
            return FakeResult()
        @contextmanager
        def transaction(self):
            yield self

    @contextmanager
    def fake_user_connection(domain, principal):
        assert domain == "nexora"
        yield FakeConnection()

    monkeypatch.setattr(db_hub, "user_connection", fake_user_connection)
    with TestClient(app) as client:
        token = client.post("/api/v1/auth/dev-token")
        headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
        profile = client.put("/api/v1/nexora/profile", headers=headers, json={
            "display_name": "  Test   Learner  ", "locale": "ar-EG",
            "adult_confirmed": True, "consent_confirmed": True, "consent_policy_version": "2026-11-14-v1",
        })
        assert profile.status_code == 200
        assert profile.json()["profile"]["display_name"] == "Test Learner"
        goal = client.post("/api/v1/nexora/goals", headers=headers, json={"title": "Learn Python", "domain": "Programming"})
        assert goal.status_code == 201
        path = client.post("/api/v1/nexora/paths", headers=headers, json={"title": "Python Foundations", "domain": "Programming", "objective": "Build a small verified application"})
        assert path.status_code == 201
    # The authenticated identity, not a client-supplied owner_id, is bound to every write.
    writes = [params for query, params in captured if "INSERT INTO public.learner_profiles" in query or "INSERT INTO public.learning_goals" in query or "INSERT INTO public.learning_paths" in query]
    assert len(writes) == 3
    assert all(str(params[0]) == "9e3c8e5e-ef0b-4ca7-8ae5-7c15f6a9e201" for params in writes)
    assert all("owner_id" in query.lower() for query, _ in captured if query.startswith("INSERT INTO public.learning_"))


def test_nexora_consent_migration_is_append_only_and_rls_protected():
    migration = (ROOT / "database" / "nexora" / "03-learner-consents.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS public.learner_consents" in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "FOR INSERT TO mishkat_app" in migration
    assert "FOR SELECT TO mishkat_app" in migration
    assert "GRANT SELECT, INSERT" in migration
    assert "GRANT UPDATE" not in migration and "GRANT DELETE" not in migration


def test_nexora_withdrawn_consent_blocks_goal_updates(monkeypatch):
    from contextlib import contextmanager
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from fastapi.testclient import TestClient
    from app.database import db_hub
    from app.main import app

    class FakeResult:
        def __init__(self, one=None): self.one = one
        def fetchone(self): return self.one

    class FakeConnection:
        def execute(self, query, params=None):
            compact = " ".join(query.split())
            if "SELECT consent_status FROM public.learner_profiles" in compact:
                return FakeResult({"consent_status": "withdrawn"})
            raise AssertionError(f"Unexpected write/query after withdrawn consent: {compact}")

    @contextmanager
    def fake_user_connection(domain, principal):
        assert domain == "nexora"
        yield FakeConnection()

    monkeypatch.setattr(db_hub, "user_connection", fake_user_connection)
    with TestClient(app) as client:
        token = client.post("/api/v1/auth/dev-token")
        headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
        response = client.patch("/api/v1/nexora/goals/22222222-2222-4222-8222-222222222222?status=completed", headers=headers)
        assert response.status_code == 409
        assert "consent is not active" in response.json()["detail"]


def test_nexora_export_is_owner_scoped_and_includes_consent_history(monkeypatch):
    from contextlib import contextmanager
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from fastapi.testclient import TestClient
    from app.database import db_hub
    from app.main import app

    seen = []
    class FakeResult:
        def __init__(self, one=None, many=None): self.one, self.many = one, many or []
        def fetchone(self): return self.one
        def fetchall(self): return self.many

    class FakeConnection:
        def execute(self, query, params=None):
            compact = " ".join(query.split())
            seen.append((compact, params))
            if "FROM public.learner_profiles" in compact:
                return FakeResult(one={"id":"learner-1", "display_name":"Learner", "locale":"ar-EG", "age_band":None, "accessibility_preferences":{}, "consent_status":"granted", "created_at":"2026-11-14T00:00:00Z", "updated_at":"2026-11-14T00:00:00Z"})
            if "FROM public.learning_goals" in compact:
                return FakeResult(many=[{"id":"goal-1", "title":"Learn Python", "domain":"Programming", "target_date":None, "status":"active", "created_at":"2026-11-14T00:00:00Z"}])
            if "FROM public.learning_paths" in compact:
                return FakeResult(many=[])
            if "FROM public.learner_consents" in compact:
                return FakeResult(many=[{"consent_type":"learning_profile_storage", "policy_version":"2026-11-14-v1", "granted":True, "locale":"ar-EG", "recorded_at":"2026-11-14T00:00:00Z"}])
            raise AssertionError(f"Unexpected export query: {compact}")

    @contextmanager
    def fake_user_connection(domain, principal):
        assert domain == "nexora"
        yield FakeConnection()

    monkeypatch.setattr(db_hub, "user_connection", fake_user_connection)
    with TestClient(app) as client:
        token = client.post("/api/v1/auth/dev-token")
        headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
        response = client.get("/api/v1/nexora/export", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["export_schema"] == "mishkat.nexora.export.v1"
        assert payload["goals"][0]["title"] == "Learn Python"
        assert payload["consent_history"][0]["policy_version"] == "2026-11-14-v1"
    assert all(params == ("9e3c8e5e-ef0b-4ca7-8ae5-7c15f6a9e201",) for _, params in seen)


def test_nexora_export_button_is_present_and_cache_version_is_bumped():
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "assets" / "app.js").read_text(encoding="utf-8")
    sw = (ROOT / "frontend" / "sw.js").read_text(encoding="utf-8")
    assert 'id="nexoraExportData"' in html
    assert "async function exportNexoraData()" in js
    assert "mishkat-shell-v2" in sw
    assert "mishkat-shell-v1" not in sw


def test_frontend_html_ids_are_unique():
    from html.parser import HTMLParser

    class IdParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids = []
        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if values.get("id"):
                self.ids.append(values["id"])

    parser = IdParser()
    parser.feed((ROOT / "frontend" / "index.html").read_text(encoding="utf-8"))
    assert len(parser.ids) == len(set(parser.ids)), "Frontend contains duplicate HTML IDs"
