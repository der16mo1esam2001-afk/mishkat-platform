from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import db_hub
from app.main import app


class InMemoryDomainConnection:
    """Mock connection for owner-scoped domain slice testing without live PostgreSQL."""

    def __init__(self, owner_id: UUID) -> None:
        self.owner_id = str(owner_id)
        self.queries: list[tuple[str, Any]] = []

    def execute(self, query: str, params: Any = None):
        compact = " ".join(query.split())
        self.queries.append((compact, params))

        # Vitalis mocks
        if "INSERT INTO public.patient_profiles" in compact:
            return MockResult(one={"id": uuid4(), "pseudonymous_ref": params[1], "age_band": params[2], "sex_code": params[3], "consent_status": "granted", "data_classification": params[4], "created_at": "2026-11-14T00:00:00Z"})
        if "SELECT id, pseudonymous_ref" in compact:
            return MockResult(many=[{"id": uuid4(), "pseudonymous_ref": "PAT-EG-001", "age_band": "30-44", "sex_code": "M", "consent_status": "granted", "data_classification": "sensitive", "created_at": "2026-11-14T00:00:00Z"}])
        if "SELECT id FROM public.patient_profiles" in compact:
            return MockResult(one={"id": params[1]})
        if "INSERT INTO public.clinical_observations" in compact:
            return MockResult(one={"id": uuid4(), "patient_id": params[1], "code": params[4], "display": params[5], "value_numeric": params[6], "unit": params[8], "effective_at": "2026-11-14T00:00:00Z", "created_at": "2026-11-14T00:00:00Z"})
        if "INSERT INTO public.care_plans" in compact:
            return MockResult(one={"id": uuid4(), "patient_id": params[1], "title": params[2], "plan_status": params[3], "next_review_at": "2026-12-14T00:00:00Z", "created_at": "2026-11-14T00:00:00Z"})

        # Aquanex mocks
        if "INSERT INTO public.water_assets" in compact:
            return MockResult(one={"id": uuid4(), "asset_code": params[1], "asset_type": params[2], "status": params[3], "capacity_value": params[4], "capacity_unit": params[5], "created_at": "2026-11-14T00:00:00Z"})
        if "SELECT id, asset_code" in compact:
            return MockResult(many=[{"id": uuid4(), "asset_code": "PUMP-STA-01", "asset_type": "pump", "status": "active", "capacity_value": 500.0, "capacity_unit": "m3/day", "created_at": "2026-11-14T00:00:00Z"}])
        if "SELECT id FROM public.water_assets" in compact:
            return MockResult(one={"id": params[1]})
        if "INSERT INTO public.telemetry_readings" in compact:
            return MockResult(one={"id": uuid4(), "sensor_ref": params[2], "metric_code": params[3], "value": params[4], "unit": params[5], "measured_at": "2026-11-14T00:00:00Z", "quality_flag": params[6]})
        if "UPDATE public.water_alerts" in compact:
            return MockResult(one={"id": params[5], "alert_type": "pressure_drop", "severity": "high", "status": params[0], "human_verified": params[1], "created_at": "2026-11-14T00:00:00Z", "resolved_at": "2026-11-14T00:00:00Z"})

        # Agronex mocks
        if "INSERT INTO public.farms" in compact:
            return MockResult(one={"id": uuid4(), "farm_code": params[1], "name": params[2], "area": params[3], "area_unit": params[4], "country_code": params[5], "created_at": "2026-11-14T00:00:00Z"})
        if "SELECT id, farm_code" in compact:
            return MockResult(many=[{"id": uuid4(), "farm_code": "FARM-DELTA-01", "name": "Delta Oasis", "area": 45.0, "area_unit": "ha", "country_code": "EG", "created_at": "2026-11-14T00:00:00Z"}])
        if "SELECT id FROM public.farms" in compact:
            return MockResult(one={"id": params[1]})
        if "INSERT INTO public.plots" in compact:
            return MockResult(one={"id": uuid4(), "farm_id": params[1], "plot_code": params[2], "area_ha": params[3], "soil_type": params[4], "irrigation_type": params[5]})
        if "SELECT id FROM public.crop_cycles" in compact:
            return MockResult(one={"id": params[1]})
        if "INSERT INTO public.disease_observations" in compact:
            return MockResult(one={"id": uuid4(), "crop_cycle_id": params[1], "observed_at": "2026-11-14T00:00:00Z", "suspected_condition": params[2], "confidence": params[3], "expert_review_status": "pending", "source_ref": params[4]})

        # Energis mocks
        if "INSERT INTO public.energy_sites" in compact:
            return MockResult(one={"id": uuid4(), "site_code": params[1], "name": params[2], "site_type": params[3], "latitude": params[4], "longitude": params[5], "country_code": params[6], "created_at": "2026-11-14T00:00:00Z"})
        if "SELECT id, site_code" in compact:
            return MockResult(many=[{"id": uuid4(), "site_code": "SOLAR-BENBAN-01", "name": "Benban Plant 1", "site_type": "solar_plant", "latitude": 24.4, "longitude": 32.7, "country_code": "EG", "created_at": "2026-11-14T00:00:00Z"}])
        if "SELECT id FROM public.energy_sites" in compact:
            return MockResult(one={"id": params[1]})
        if "INSERT INTO public.meters" in compact:
            return MockResult(one={"id": uuid4(), "site_id": params[1], "meter_code": params[2], "meter_type": params[3], "unit": params[4]})
        if "INSERT INTO public.forecasts" in compact:
            return MockResult(one={"id": uuid4(), "site_id": params[1], "target_metric": params[2], "horizon_start": "2026-11-14T00:00:00Z", "horizon_end": "2026-11-15T00:00:00Z", "predicted_value": params[3], "unit": params[4], "lower_bound": params[5], "upper_bound": params[6], "model_name": params[7], "model_version": params[8], "created_at": "2026-11-14T00:00:00Z"})

        # Shared audit/generic
        if "INSERT INTO public.audit_events" in compact:
            return MockResult(one={"id": uuid4()})

        return MockResult()

    @contextmanager
    def transaction(self):
        yield self


class MockResult:
    def __init__(self, one=None, many=None):
        self.one = one
        self.many = many or []

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.many


@pytest.fixture
def auth_headers():
    with TestClient(app) as client:
        token = client.post("/api/v1/auth/dev-token")
        assert token.status_code == 200
        return {"Authorization": f"Bearer {token.json()['access_token']}"}


def test_vitalis_vertical_slice(monkeypatch, auth_headers):
    @contextmanager
    def mock_conn(domain, principal):
        assert domain == "vitalis"
        yield InMemoryDomainConnection(principal.user_id)

    monkeypatch.setattr(db_hub, "user_connection", mock_conn)

    with TestClient(app) as client:
        # Check medical safety policy
        policy = client.get("/api/v1/vitalis/safety-policy")
        assert policy.status_code == 200
        assert policy.json()["autonomous_diagnosis"] is False
        assert policy.json()["autonomous_prescription"] is False

        # Create pseudonymous patient profile
        p_res = client.post("/api/v1/vitalis/patients", headers=auth_headers, json={
            "pseudonymous_ref": "PAT-EGY-789",
            "age_band": "30-44",
            "sex_code": "F",
            "data_classification": "sensitive",
        })
        assert p_res.status_code == 201
        patient_id = p_res.json()["patient"]["id"]

        # List patients
        list_res = client.get("/api/v1/vitalis/patients", headers=auth_headers)
        assert list_res.status_code == 200
        assert len(list_res.json()["items"]) >= 1

        # Record clinical observation with FHIR representation
        obs_res = client.post("/api/v1/vitalis/observations", headers=auth_headers, json={
            "patient_id": patient_id,
            "code_system": "LOINC",
            "code": "8480-6",
            "display": "Systolic blood pressure",
            "value_numeric": 120.0,
            "unit": "mmHg",
            "source_ref": "clinical_trial_visit_1",
        })
        assert obs_res.status_code == 201
        assert obs_res.json()["fhir_r5"]["resourceType"] == "Observation"
        assert obs_res.json()["fhir_r5"]["valueQuantity"]["value"] == 120.0

        # Create care plan
        plan_res = client.post("/api/v1/vitalis/care-plans", headers=auth_headers, json={
            "patient_id": patient_id,
            "title": "Hypertension preventive lifestyle monitoring",
            "plan_status": "active",
            "next_review_days": 60,
        })
        assert plan_res.status_code == 201


def test_aquanex_vertical_slice(monkeypatch, auth_headers):
    @contextmanager
    def mock_conn(domain, principal):
        assert domain == "aquanex"
        yield InMemoryDomainConnection(principal.user_id)

    monkeypatch.setattr(db_hub, "user_connection", mock_conn)

    with TestClient(app) as client:
        # Check water safety policy
        policy = client.get("/api/v1/aquanex/safety-policy")
        assert policy.status_code == 200
        assert policy.json()["actuation_allowed"] is False
        assert "Strictly Read-Only" in policy.json()["scada_mode"]

        # Register water asset
        asset_res = client.post("/api/v1/aquanex/assets", headers=auth_headers, json={
            "asset_code": "PIPE-MAIN-001",
            "asset_type": "pipeline",
            "status": "active",
            "capacity_value": 12000.0,
            "capacity_unit": "m3/day",
            "source_ref": "gis_survey_2025",
        })
        assert asset_res.status_code == 201
        asset_id = asset_res.json()["asset"]["id"]

        # Record telemetry reading
        tel_res = client.post("/api/v1/aquanex/telemetry", headers=auth_headers, json={
            "asset_id": asset_id,
            "sensor_ref": "SENS-PR-402",
            "metric_code": "PRESSURE",
            "value": 4.5,
            "unit": "bar",
            "quality_flag": "valid",
            "source_ref": "utility_telemetry_gw",
        })
        assert tel_res.status_code == 201

        # Verify water alert with human sign-off
        alert_id = str(uuid4())
        alert_res = client.patch(f"/api/v1/aquanex/alerts/{alert_id}", headers=auth_headers, json={
            "status": "resolved",
            "human_verified": True,
            "notes": "Field technician inspected valve joint. Repaired packing seal.",
        })
        assert alert_res.status_code == 200
        assert alert_res.json()["alert"]["human_verified"] is True


def test_agronex_vertical_slice(monkeypatch, auth_headers):
    @contextmanager
    def mock_conn(domain, principal):
        assert domain == "agronex"
        yield InMemoryDomainConnection(principal.user_id)

    monkeypatch.setattr(db_hub, "user_connection", mock_conn)

    with TestClient(app) as client:
        # Check agricultural safety policy
        policy = client.get("/api/v1/agronex/safety-policy")
        assert policy.status_code == 200
        assert "Strictly Prohibited" in policy.json()["chemical_recommendations"]

        # Create farm
        farm_res = client.post("/api/v1/agronex/farms", headers=auth_headers, json={
            "farm_code": "FARM-FAYOUM-1",
            "name": "Fayoum Pilot Farm",
            "area": 25.5,
            "area_unit": "ha",
            "country_code": "EG",
        })
        assert farm_res.status_code == 201
        farm_id = farm_res.json()["farm"]["id"]

        # Create plot
        plot_res = client.post("/api/v1/agronex/plots", headers=auth_headers, json={
            "farm_id": farm_id,
            "plot_code": "PLOT-A",
            "area_ha": 10.0,
            "soil_type": "Clay loam",
            "irrigation_type": "drip",
        })
        assert plot_res.status_code == 201

        # Record disease observation: MUST be suspected, never auto-prescribed
        cycle_id = str(uuid4())
        dis_res = client.post("/api/v1/agronex/disease-observations", headers=auth_headers, json={
            "crop_cycle_id": cycle_id,
            "suspected_condition": "Suspected Wheat Leaf Rust (Puccinia triticina)",
            "confidence": 0.82,
            "source_ref": "multispectral_drone_pass_1",
        })
        assert dis_res.status_code == 201
        assert "suspected" in dis_res.json()["safety_advisory"].lower()


def test_energis_vertical_slice(monkeypatch, auth_headers):
    @contextmanager
    def mock_conn(domain, principal):
        assert domain == "energis"
        yield InMemoryDomainConnection(principal.user_id)

    monkeypatch.setattr(db_hub, "user_connection", mock_conn)

    with TestClient(app) as client:
        # Check energy safety policy
        policy = client.get("/api/v1/energis/safety-policy")
        assert policy.status_code == 200
        assert "Strictly Read-Only" in policy.json()["grid_control"]

        # Create site
        site_res = client.post("/api/v1/energis/sites", headers=auth_headers, json={
            "site_code": "SOLAR-ASWAN-01",
            "name": "Aswan Solar Project",
            "site_type": "solar_plant",
            "latitude": 24.08,
            "longitude": 32.89,
            "country_code": "EG",
        })
        assert site_res.status_code == 201
        site_id = site_res.json()["site"]["id"]

        # Create meter
        meter_res = client.post("/api/v1/energis/meters", headers=auth_headers, json={
            "site_id": site_id,
            "meter_code": "MTR-INV-001",
            "meter_type": "solar_inverter",
            "unit": "kWh",
        })
        assert meter_res.status_code == 201

        # Forecast with uncertainty bounds: valid bounds
        fc_res = client.post("/api/v1/energis/forecasts", headers=auth_headers, json={
            "site_id": site_id,
            "target_metric": "solar_generation_kwh",
            "predicted_value": 4500.0,
            "lower_bound": 4100.0,
            "upper_bound": 4900.0,
            "unit": "kWh",
            "model_name": "solar_irradiance_persistence_v2",
            "model_version": "2.1.0",
        })
        assert fc_res.status_code == 201

        # Forecast with inverted bounds: must fail with 422
        bad_fc = client.post("/api/v1/energis/forecasts", headers=auth_headers, json={
            "site_id": site_id,
            "target_metric": "solar_generation_kwh",
            "predicted_value": 4500.0,
            "lower_bound": 5000.0,
            "upper_bound": 4000.0,
            "unit": "kWh",
            "model_name": "solar_irradiance_persistence_v2",
            "model_version": "2.1.0",
        })
        assert bad_fc.status_code == 422
