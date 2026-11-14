from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .ai_gateway import (
    AIProviderStatus,
    GroundedResponse,
    ToolActionPreview,
    ai_gateway,
    tool_registry,
)
from .catalog import SOURCE_AS_OF, SOURCES, WORKSPACES
from .connectors import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorStatus,
    FetchResult,
    connector_registry,
)
from .database import db_hub
from .domains import (
    agronex_router,
    aquanex_router,
    energis_router,
    vitalis_router,
)
from .middleware import (
    RateLimiter,
    SecurityAndObservabilityMiddleware,
    rate_limiter,
    redact_sensitive_text,
)
from .security import (
    Principal,
    get_current_principal,
    issue_local_development_token,
    require_role,
)
from .settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        db_hub.open()
    except Exception as exc:  # report a degraded start instead of hiding the failure
        app.state.database_start_error = f"{type(exc).__name__}: {exc}"
    yield
    db_hub.close()


app = FastAPI(
    title="MISHKAT Intelligence Platform API",
    version="0.3.0",
    description="Unified application gateway for five independently isolated sector workspaces.",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    openapi_url="/openapi.json" if settings.environment == "development" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.add_middleware(SecurityAndObservabilityMiddleware)

_FILE = Path(__file__).resolve()
_FRONTEND_CANDIDATES = [_FILE.parents[2] / "frontend", _FILE.parents[1] / "frontend"]
FRONTEND_DIR = next((candidate for candidate in _FRONTEND_CANDIDATES if candidate.is_dir()), _FRONTEND_CANDIDATES[0])
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/manifest.webmanifest", include_in_schema=False)
def pwa_manifest():
    return FileResponse(FRONTEND_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse(FRONTEND_DIR / "sw.js", media_type="application/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/api/v1/health/live", tags=["operations"])
def liveness():
    return {"status": "alive", "service": "mishkat-api", "version": app.version}


@app.get("/api/v1/health/ready", tags=["operations"])
def readiness():
    statuses = db_hub.check()
    ready = bool(statuses) and all(value == "connected" for value in statuses.values())
    return {"status": "ready" if ready else "degraded", "databases": statuses}


@app.post("/api/v1/auth/dev-token", tags=["authentication"])
def dev_token():
    """Local-only token for the closed development environment. Never enabled in production."""
    return issue_local_development_token()


@app.get("/api/v1/system/overview", tags=["system"])
def system_overview(principal: Principal = Depends(get_current_principal)):
    statuses = db_hub.check()
    return {
        "platform": "MISHKAT",
        "version": app.version,
        "authenticated_user": str(principal.user_id),
        "user_role": principal.role,
        "database_isolation": "five independent PostgreSQL databases",
        "databases": statuses,
        "all_databases_connected": all(value == "connected" for value in statuses.values()),
        "warning": "A connected database does not prove domain data quality, external integrations, or production readiness.",
    }


@app.get("/api/v1/workspaces", tags=["workspaces"])
def workspaces(principal: Principal = Depends(get_current_principal)):
    return {"items": WORKSPACES}


@app.get("/api/v1/evidence/sources", tags=["evidence"])
def evidence_sources(principal: Principal = Depends(get_current_principal)):
    return {"as_of": SOURCE_AS_OF, "items": SOURCES}


@app.get("/api/v1/ai/status", tags=["ai-governance"])
def ai_status(principal: Principal = Depends(get_current_principal)):
    return {
        "status": "not_configured",
        "inference_enabled": False,
        "message": "No AI model provider is connected in this engineering package. No generated answer or prediction is being simulated.",
        "required_before_enablement": [
            "approved provider and data-processing terms",
            "server-side secret management",
            "domain-specific safety policy",
            "evaluation dataset and independent acceptance tests",
        ],
        "safe_grounded_assistant_available": True,
    }


class AskGroundedQueryRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)


@app.post("/api/v1/ai/nexora/ask", tags=["ai-governance", "nexora"])
def ask_grounded_assistant(
    payload: AskGroundedQueryRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Low-risk grounded educational assistant query with citations and prompt injection defense."""
    response = ai_gateway.answer_grounded_query(payload.query, user_id=principal.user_id)
    return {
        "query": response.query,
        "answer": response.grounded_answer,
        "citations": [
            {
                "source_id": c.source_id,
                "title": c.title,
                "publisher": c.publisher,
                "license": c.license_name,
                "url": c.source_url,
                "retrieved_at": c.retrieved_at,
                "section": c.section_or_page,
            }
            for c in response.citations
        ],
        "retrieved_facts": response.retrieved_facts,
        "inference_and_advice": response.inference_and_advice,
        "is_refusal": response.is_refusal,
        "refusal_reason": response.refusal_reason,
        "latency_ms": round(response.latency_ms, 2),
        "model_key": response.model_key,
        "prompt_version": response.prompt_version,
    }


@app.get("/api/v1/connectors", tags=["connectors"])
async def list_connectors(principal: Principal = Depends(get_current_principal)):
    return {"items": await connector_registry.get_all_statuses()}


@app.get("/api/v1/connectors/{connector_id}/health", tags=["connectors"])
async def connector_health(connector_id: str, principal: Principal = Depends(get_current_principal)):
    connector = connector_registry.get(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    return await connector.check_health()


class NasaPowerRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    start_date: date
    end_date: date
    parameters: list[str] = Field(default_factory=lambda: ["T2M", "PRECTOTCORR"], min_length=1, max_length=20)
    community: Literal["AG", "RE"] = "AG"


ALLOWED_NASA_PARAMETERS = {
    "AG": {"T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "WS10M"},
    "RE": {"ALLSKY_SFC_SW_DWN"},
}


@app.post("/api/v1/connectors/nasa-power/fetch", tags=["connectors"])
async def fetch_nasa_power(payload: NasaPowerRequest, principal: Principal = Depends(get_current_principal)):
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if (payload.end_date - payload.start_date).days > 370:
        raise HTTPException(status_code=422, detail="A maximum 371-day interval is allowed per request")
    requested = [p.upper() for p in payload.parameters]
    invalid = sorted(set(requested) - ALLOWED_NASA_PARAMETERS[payload.community])
    if invalid:
        raise HTTPException(status_code=422, detail={"invalid_parameters": invalid, "community": payload.community, "allowed": sorted(ALLOWED_NASA_PARAMETERS[payload.community])})

    params = {
        "parameters": ",".join(requested),
        "community": payload.community,
        "longitude": payload.longitude,
        "latitude": payload.latitude,
        "start": payload.start_date.strftime("%Y%m%d"),
        "end": payload.end_date.strftime("%Y%m%d"),
        "format": "JSON",
        "time-standard": "UTC",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(settings.nasa_power_base_url, params=params)
            response.raise_for_status()
            raw = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"NASA POWER request failed: {type(exc).__name__}") from exc

    properties = raw.get("properties", {})
    parameter_data = properties.get("parameter", {})
    parameter_metadata = raw.get("parameters", {})
    if not parameter_data:
        raise HTTPException(status_code=502, detail="NASA POWER returned no parameter series")

    rows: list[dict[str, Any]] = []
    for parameter, observations in parameter_data.items():
        meta = parameter_metadata.get(parameter, {}) if isinstance(parameter_metadata, dict) else {}
        source_unit = meta.get("units") or meta.get("unit") or _nasa_unit(parameter)
        for timestamp, value in observations.items():
            rows.append({"date": timestamp, "parameter": parameter, "value": value, "unit": source_unit})

    domain, table = ("agronex", "weather_observations") if payload.community == "AG" else ("energis", "resource_observations")
    persisted = {domain: 0}
    correlation_id = str(uuid4())
    try:
        with db_hub.user_connection(domain, principal) as conn:
            run = conn.execute(
                """INSERT INTO public.ingestion_runs
                (owner_id, source_id, target_dataset, status, started_at, request_metadata, license_snapshot)
                VALUES (%s, 'nasa_power', %s, 'running', now(), %s::jsonb, 'NASA POWER source terms; attribution retained')
                RETURNING id""",
                (str(principal.user_id), table,
                 __import__("json").dumps({"latitude": payload.latitude, "longitude": payload.longitude,
                                            "start": payload.start_date.isoformat(), "end": payload.end_date.isoformat(),
                                            "parameters": requested, "time_standard": "UTC"})),
            ).fetchone()
            ingestion_run_id = str(run["id"])
            for row in rows:
                conn.execute(
                    f"""INSERT INTO {table}
                    (owner_id, observation_date, parameter_code, value, unit, latitude, longitude,
                     source_id, ingestion_run_id, raw_value)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'nasa_power', %s, %s::jsonb)
                    ON CONFLICT (owner_id, observation_date, parameter_code, latitude, longitude)
                    DO UPDATE SET value = EXCLUDED.value, raw_value = EXCLUDED.raw_value,
                                  ingestion_run_id = EXCLUDED.ingestion_run_id, imported_at = now()""",
                    (
                        str(principal.user_id),
                        datetime.strptime(row["date"], "%Y%m%d").date(),
                        row["parameter"],
                        (float(row["value"]) if row["value"] not in (None, -999, -999.0) else None),
                        row["unit"],
                        payload.latitude,
                        payload.longitude,
                        ingestion_run_id,
                        __import__("json").dumps(row),
                    ),
                )
                persisted[domain] += 1
            conn.execute(
                """UPDATE public.ingestion_runs SET status='completed', finished_at=now(),
                   records_received=%s, records_saved=%s WHERE id=%s""",
                (len(rows), persisted[domain], ingestion_run_id),
            )
            conn.execute(
                """INSERT INTO public.audit_events
                (owner_id, event_type, entity_type, entity_id, actor_type, source_id, correlation_id, details)
                VALUES (%s, 'data_import', %s, %s, 'integration', 'nasa_power', %s, %s::jsonb)""",
                (str(principal.user_id), table, ingestion_run_id, correlation_id,
                 __import__("json").dumps({"record_count": len(rows), "latitude": payload.latitude,
                                            "longitude": payload.longitude, "start": payload.start_date.isoformat(),
                                            "end": payload.end_date.isoformat(), "parameters": requested})),
            )
    except Exception as exc:  # noqa: BLE001
        persisted[domain] = -1
        app.state.last_ingestion_error = {"domain": domain, "error": type(exc).__name__}
        try:
            with db_hub.user_connection(domain, principal) as conn:
                conn.execute(
                    """INSERT INTO public.ingestion_runs
                    (owner_id, source_id, target_dataset, status, started_at, finished_at, error_code, request_metadata)
                    VALUES (%s, 'nasa_power', %s, 'failed', now(), now(), %s, %s::jsonb)""",
                    (str(principal.user_id), table, type(exc).__name__,
                     __import__("json").dumps({"latitude": payload.latitude, "longitude": payload.longitude,
                                                "start": payload.start_date.isoformat(), "end": payload.end_date.isoformat()})),
                )
        except Exception:
            pass

    return {
        "source": "NASA POWER Daily API",
        "source_url": "https://power.larc.nasa.gov/docs/services/api/temporal/daily/",
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "location": {"latitude": payload.latitude, "longitude": payload.longitude},
        "period": {"start": payload.start_date.isoformat(), "end": payload.end_date.isoformat()},
        "time_standard": "UTC",
        "parameters": requested,
        "record_count": len(rows),
        "records": rows,
        "persistence": persisted,
        "limitations": [
            "Units are read from NASA POWER response metadata when provided; the application fallback is documented in the connector and should be checked against the source parameter/community before downstream modeling.",
            "NASA POWER provides gridded meteorological and solar-resource estimates; the selected grid cell may differ from the exact coordinates. It is not a local farm sensor or electricity meter.",
            "A persistence value of -1 means that domain write failed; inspect server logs and the corresponding database before relying on storage.",
            "Null values and the NASA missing-data code -999 are preserved as missing; do not convert them to zero.",
        ],
    }


def _nasa_unit(parameter: str) -> str:
    units = {
        "T2M": "degC", "T2M_MAX": "degC", "T2M_MIN": "degC",
        "PRECTOTCORR": "mm/day", "RH2M": "%", "WS10M": "m/s", "ALLSKY_SFC_SW_DWN": "MJ/m2/day",
    }
    return units.get(parameter, "source-unit-to-verify")


@app.get("/api/v1/modules/{domain}/snapshot", tags=["workspaces"])
def module_snapshot(domain: str, principal: Principal = Depends(get_current_principal)):
    workspace = next((item for item in WORKSPACES if item["id"] == domain), None)
    if not workspace:
        raise HTTPException(status_code=404, detail="Unknown workspace")
    table_map = {
        "vitalis": ["patient_profiles", "encounters", "clinical_observations"],
        "aquanex": ["water_assets", "telemetry_readings", "water_samples", "water_alerts"],
        "agronex": ["farms", "plots", "crop_cycles", "soil_samples", "weather_observations", "yield_records"],
        "energis": ["energy_sites", "meters", "meter_readings", "resource_observations", "anomalies"],
        "nexora": ["learner_profiles", "learning_resources", "learning_paths", "assessments", "assessment_attempts", "mastery_records"],
    }
    counts = {}
    with db_hub.user_connection(domain, principal) as conn:
        for table in table_map[domain]:
            try:
                with conn.transaction():
                    row = conn.execute(f"SELECT count(*) AS n FROM public.{table}").fetchone()
                counts[table] = row["n"]
            except Exception:
                counts[table] = None
    return {"workspace": domain, "counts": counts, "note": "Null means table/schema unavailable or query failed; it is not a zero count."}


DOMAIN_SET = {item["id"] for item in WORKSPACES}
NEXORA_CONSENT_POLICY_VERSION = "2026-11-14-v1"


@app.get("/api/v1/modules/{domain}/activity", tags=["operations", "workspaces"])
def module_activity(
    domain: str,
    limit: int = Query(default=10, ge=1, le=50),
    principal: Principal = Depends(get_current_principal),
):
    """Return owner-scoped ingestion, model and audit summaries for one domain."""
    if domain not in DOMAIN_SET:
        raise HTTPException(status_code=404, detail="Unknown workspace")
    with db_hub.user_connection(domain, principal) as conn:
        ingestion = conn.execute(
            """SELECT id, source_id, target_dataset, status, requested_at, finished_at,
                      records_received, records_saved, error_code
               FROM public.ingestion_runs
               WHERE owner_id=%s ORDER BY requested_at DESC LIMIT %s""",
            (str(principal.user_id), limit),
        ).fetchall()
        models = conn.execute(
            """SELECT model_key, model_version, use_case, status, evaluation_metrics,
                      approved_at, created_at
               FROM public.model_registry
               WHERE owner_id=%s ORDER BY created_at DESC LIMIT %s""",
            (str(principal.user_id), limit),
        ).fetchall()
        events = conn.execute(
            """SELECT event_type, entity_type, entity_id, source_id, occurred_at
               FROM public.audit_events
               WHERE owner_id=%s ORDER BY occurred_at DESC LIMIT %s""",
            (str(principal.user_id), limit),
        ).fetchall()
    return {
        "domain": domain,
        "ingestion_runs": [dict(row) for row in ingestion],
        "models": [dict(row) for row in models],
        "audit_events": [dict(row) for row in events],
        "note": "Only records owned by the authenticated principal are returned. Empty lists mean no matching records were found.",
    }


class NexoraProfileInput(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    locale: Literal["ar-EG", "en"] = "ar-EG"
    adult_confirmed: bool = False
    consent_confirmed: bool = False
    consent_policy_version: str = Field(min_length=1, max_length=40)

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("display_name cannot be blank")
        return cleaned


class NexoraGoalInput(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    domain: str = Field(min_length=2, max_length=100)
    target_date: date | None = None

    @field_validator("title", "domain")
    @classmethod
    def trim_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Field cannot be blank")
        return cleaned


class NexoraPathInput(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    domain: str = Field(min_length=2, max_length=100)
    objective: str = Field(min_length=8, max_length=1200)

    @field_validator("title", "domain", "objective")
    @classmethod
    def trim_path_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Field cannot be blank")
        return cleaned


@app.get("/api/v1/nexora/consent-policy", tags=["nexora", "privacy"])
def nexora_consent_policy(principal: Principal = Depends(get_current_principal)):
    return {
        "policy_version": NEXORA_CONSENT_POLICY_VERSION,
        "scope": "adult_only_learning_profile_pilot",
        "data_fields": ["display_name", "locale", "learning_goals", "learning_path_records"],
        "not_collected_by_this_pilot": ["government_id", "date_of_birth", "biometric_data", "school_records", "clinical_data"],
        "purpose": "Create a learner-owned profile and save learning goals and path descriptions in the isolated NEXORA database.",
        "ai_processing": "No AI provider is connected by this pilot endpoint; no learner text is sent to an LLM by these routes.",
        "withdrawal": "Consent can be withdrawn. New goal/path writes will then be blocked. Previously saved records remain until a deletion/export policy and workflow are implemented.",
        "age_gate": "Adult self-attestation only; not an identity or age verification process. Do not register minors in this pilot.",
    }


@app.get("/api/v1/nexora/profile", tags=["nexora"])
def get_nexora_profile(principal: Principal = Depends(get_current_principal)):
    with db_hub.user_connection("nexora", principal) as conn:
        row = conn.execute(
            """SELECT id, display_name, locale, age_band, accessibility_preferences,
                      consent_status, created_at, updated_at
               FROM public.learner_profiles WHERE owner_id=%s""",
            (str(principal.user_id),),
        ).fetchone()
    return {"profile": dict(row) if row else None, "scope": "adult_pilot_only"}


@app.put("/api/v1/nexora/profile", tags=["nexora"])
def upsert_nexora_profile(payload: NexoraProfileInput, principal: Principal = Depends(get_current_principal)):
    if not payload.adult_confirmed:
        raise HTTPException(status_code=422, detail="This pilot is for adults only. Confirm that the learner is 18 or older.")
    if not payload.consent_confirmed:
        raise HTTPException(status_code=422, detail="Explicit consent is required before storing a learning profile.")
    if payload.consent_policy_version != NEXORA_CONSENT_POLICY_VERSION:
        raise HTTPException(status_code=409, detail="The consent policy has changed. Reload the policy and review it before continuing.")
    with db_hub.user_connection("nexora", principal) as conn:
        row = conn.execute(
            """INSERT INTO public.learner_profiles
               (owner_id, display_name, locale, consent_status)
               VALUES (%s, %s, %s, 'granted')
               ON CONFLICT (owner_id) DO UPDATE SET
                 display_name=EXCLUDED.display_name,
                 locale=EXCLUDED.locale,
                 consent_status='granted',
                 updated_at=now()
               RETURNING id, display_name, locale, age_band, accessibility_preferences,
                         consent_status, created_at, updated_at""",
            (str(principal.user_id), payload.display_name, payload.locale),
        ).fetchone()
        conn.execute(
            """INSERT INTO public.learner_consents
               (owner_id, learner_id, consent_type, policy_version, granted, locale)
               VALUES (%s, %s, 'learning_profile_storage', %s, true, %s)""",
            (str(principal.user_id), str(row["id"]), NEXORA_CONSENT_POLICY_VERSION, payload.locale),
        )
        conn.execute(
            """INSERT INTO public.audit_events
               (owner_id, event_type, entity_type, entity_id, actor_type, details)
               VALUES (%s, 'profile_consent_recorded', 'learner_profile', %s, 'user', %s::jsonb)""",
            (str(principal.user_id), str(row["id"]), __import__("json").dumps({"locale": payload.locale, "consent": "granted", "age_gate": "adult_self_attested"})),
        )
    return {"profile": dict(row), "scope": "adult_pilot_only", "note": "Age is self-attested for this pilot; this is not an identity or age-verification service."}


@app.post("/api/v1/nexora/profile/revoke-consent", tags=["nexora", "privacy"])
def revoke_nexora_consent(principal: Principal = Depends(get_current_principal)):
    with db_hub.user_connection("nexora", principal) as conn:
        profile = conn.execute(
            """UPDATE public.learner_profiles SET consent_status='withdrawn', updated_at=now()
               WHERE owner_id=%s RETURNING id, display_name, locale""",
            (str(principal.user_id),),
        ).fetchone()
        if not profile:
            raise HTTPException(status_code=404, detail="Learner profile not found")
        conn.execute(
            """INSERT INTO public.learner_consents
               (owner_id, learner_id, consent_type, policy_version, granted, locale)
               VALUES (%s, %s, 'learning_profile_storage', %s, false, %s)""",
            (str(principal.user_id), str(profile["id"]), NEXORA_CONSENT_POLICY_VERSION, profile["locale"]),
        )
        conn.execute(
            """INSERT INTO public.audit_events
               (owner_id, event_type, entity_type, entity_id, actor_type, details)
               VALUES (%s, 'profile_consent_withdrawn', 'learner_profile', %s, 'user', '{}'::jsonb)""",
            (str(principal.user_id), str(profile["id"])),
        )
    return {"status": "withdrawn", "new_learning_writes": "blocked", "existing_records": "retained_pending_export_or_deletion_workflow"}


@app.get("/api/v1/nexora/goals", tags=["nexora"])
def list_nexora_goals(principal: Principal = Depends(get_current_principal)):
    with db_hub.user_connection("nexora", principal) as conn:
        rows = conn.execute(
            """SELECT g.id, g.title, g.domain, g.target_date, g.status, g.created_at
               FROM public.learning_goals g
               JOIN public.learner_profiles p ON p.owner_id=g.owner_id AND p.id=g.learner_id
               WHERE g.owner_id=%s ORDER BY g.created_at DESC""",
            (str(principal.user_id),),
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.post("/api/v1/nexora/goals", status_code=201, tags=["nexora"])
def create_nexora_goal(payload: NexoraGoalInput, principal: Principal = Depends(get_current_principal)):
    with db_hub.user_connection("nexora", principal) as conn:
        profile = conn.execute(
            "SELECT id, consent_status FROM public.learner_profiles WHERE owner_id=%s",
            (str(principal.user_id),),
        ).fetchone()
        if not profile or profile["consent_status"] != "granted":
            raise HTTPException(status_code=409, detail="Create a learner profile and record consent before adding goals.")
        row = conn.execute(
            """INSERT INTO public.learning_goals (owner_id, learner_id, title, domain, target_date)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING id, title, domain, target_date, status, created_at""",
            (str(principal.user_id), str(profile["id"]), payload.title, payload.domain, payload.target_date),
        ).fetchone()
        conn.execute(
            """INSERT INTO public.audit_events
               (owner_id, event_type, entity_type, entity_id, actor_type, details)
               VALUES (%s, 'learning_goal_created', 'learning_goal', %s, 'user', %s::jsonb)""",
            (str(principal.user_id), str(row["id"]), __import__("json").dumps({"domain": payload.domain})),
        )
    return {"goal": dict(row)}


@app.patch("/api/v1/nexora/goals/{goal_id}", tags=["nexora"])
def update_nexora_goal(goal_id: UUID, status: Literal["active", "completed", "paused", "cancelled"], principal: Principal = Depends(get_current_principal)):
    with db_hub.user_connection("nexora", principal) as conn:
        profile = conn.execute(
            "SELECT consent_status FROM public.learner_profiles WHERE owner_id=%s",
            (str(principal.user_id),),
        ).fetchone()
        if not profile or profile["consent_status"] != "granted":
            raise HTTPException(status_code=409, detail="Learning goal updates are disabled because learning-profile consent is not active.")
        row = conn.execute(
            """UPDATE public.learning_goals SET status=%s
               WHERE id=%s AND owner_id=%s
               RETURNING id, title, domain, target_date, status, created_at""",
            (status, str(goal_id), str(principal.user_id)),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Learning goal not found")
        conn.execute(
            """INSERT INTO public.audit_events
               (owner_id, event_type, entity_type, entity_id, actor_type, details)
               VALUES (%s, 'learning_goal_updated', 'learning_goal', %s, 'user', %s::jsonb)""",
            (str(principal.user_id), str(row["id"]), __import__("json").dumps({"status": status})),
        )
    return {"goal": dict(row)}


@app.get("/api/v1/nexora/paths", tags=["nexora"])
def list_nexora_paths(principal: Principal = Depends(get_current_principal)):
    with db_hub.user_connection("nexora", principal) as conn:
        rows = conn.execute(
            """SELECT id, title, domain, objective, status, created_at
               FROM public.learning_paths WHERE owner_id=%s ORDER BY created_at DESC""",
            (str(principal.user_id),),
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.post("/api/v1/nexora/paths", status_code=201, tags=["nexora"])
def create_nexora_path(payload: NexoraPathInput, principal: Principal = Depends(get_current_principal)):
    with db_hub.user_connection("nexora", principal) as conn:
        profile = conn.execute(
            "SELECT id, consent_status FROM public.learner_profiles WHERE owner_id=%s",
            (str(principal.user_id),),
        ).fetchone()
        if not profile or profile["consent_status"] != "granted":
            raise HTTPException(status_code=409, detail="Create a learner profile and record consent before creating a learning path.")
        row = conn.execute(
            """INSERT INTO public.learning_paths (owner_id, learner_id, title, domain, objective)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING id, title, domain, objective, status, created_at""",
            (str(principal.user_id), str(profile["id"]), payload.title, payload.domain, payload.objective),
        ).fetchone()
        conn.execute(
            """INSERT INTO public.audit_events
               (owner_id, event_type, entity_type, entity_id, actor_type, details)
               VALUES (%s, 'learning_path_created', 'learning_path', %s, 'user', %s::jsonb)""",
            (str(principal.user_id), str(row["id"]), __import__("json").dumps({"domain": payload.domain})),
        )
    return {"path": dict(row), "note": "This creates a learner-owned path record. It does not generate AI curriculum or licensed learning content."}


@app.get("/api/v1/nexora/export", tags=["nexora", "privacy"])
def export_nexora_data(principal: Principal = Depends(get_current_principal)):
    """Export the authenticated learner's NEXORA profile, consent history, goals and paths."""
    with db_hub.user_connection("nexora", principal) as conn:
        profile = conn.execute(
            """SELECT id, display_name, locale, age_band, accessibility_preferences,
                      consent_status, created_at, updated_at
               FROM public.learner_profiles WHERE owner_id=%s""",
            (str(principal.user_id),),
        ).fetchone()
        if not profile:
            raise HTTPException(status_code=404, detail="Learner profile not found")
        goals = conn.execute(
            """SELECT id, title, domain, target_date, status, created_at
               FROM public.learning_goals WHERE owner_id=%s ORDER BY created_at""",
            (str(principal.user_id),),
        ).fetchall()
        paths = conn.execute(
            """SELECT id, title, domain, objective, status, created_at
               FROM public.learning_paths WHERE owner_id=%s ORDER BY created_at""",
            (str(principal.user_id),),
        ).fetchall()
        consents = conn.execute(
            """SELECT consent_type, policy_version, granted, locale, recorded_at
               FROM public.learner_consents WHERE owner_id=%s ORDER BY recorded_at""",
            (str(principal.user_id),),
        ).fetchall()
    return {
        "export_schema": "mishkat.nexora.export.v1",
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "owner_id": str(principal.user_id),
        "profile": dict(profile),
        "goals": [dict(row) for row in goals],
        "learning_paths": [dict(row) for row in paths],
        "consent_history": [dict(row) for row in consents],
        "limitations": [
            "This export includes the NEXORA profile, goals, path descriptions, and consent history only.",
            "It does not include provider-side logs, browser/session data, or records held by connected institutions.",
            "This export endpoint does not delete source records.",
        ],
    }


# Mount sector-specific modular routers
app.include_router(vitalis_router, prefix="/api/v1")
app.include_router(aquanex_router, prefix="/api/v1")
app.include_router(agronex_router, prefix="/api/v1")
app.include_router(energis_router, prefix="/api/v1")


def run_server() -> None:
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run_server()
