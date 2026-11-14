from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from ...database import db_hub
from ...security import Principal, get_current_principal

router = APIRouter(prefix="/energis", tags=["energis-energy"])


class EnergySiteInput(BaseModel):
    site_code: str = Field(min_length=3, max_length=64)
    name: str = Field(min_length=2, max_length=120)
    site_type: Literal["building", "factory", "solar_plant", "wind_plant", "grid_asset", "other"]
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    country_code: str = Field(default="EG", min_length=2, max_length=2)
    source_ref: str = Field(default="site_registry", min_length=2, max_length=120)


class MeterInput(BaseModel):
    site_id: UUID
    meter_code: str = Field(min_length=3, max_length=64)
    meter_type: Literal["electricity", "gas", "thermal", "solar_inverter", "submeter"]
    unit: Literal["kWh", "MWh", "kW", "MW", "m3"] = "kWh"


class MeterReadingInput(BaseModel):
    meter_id: UUID
    value: float = Field(ge=0)
    unit: str = Field(min_length=1, max_length=24)
    quality_flag: Literal["valid", "suspect", "invalid", "unreviewed"] = "valid"
    source_ref: str = Field(min_length=2, max_length=120)


class ForecastInput(BaseModel):
    site_id: UUID
    target_metric: Literal["load_kwh", "solar_generation_kwh", "peak_demand_kw"]
    predicted_value: float = Field(ge=0)
    lower_bound: float | None = Field(default=None, ge=0)
    upper_bound: float | None = Field(default=None, ge=0)
    unit: str = Field(min_length=1, max_length=24)
    model_name: str = Field(min_length=2, max_length=64)
    model_version: str = Field(min_length=1, max_length=32)

    @field_validator("upper_bound")
    @classmethod
    def check_bounds(cls, v: float | None, info: Any) -> float | None:
        return v


@router.get("/safety-policy")
def energis_safety_policy():
    return {
        "domain": "ENERGIS",
        "scope": "Energy intelligence, load forecasting, and consumption efficiency",
        "grid_control": "Strictly Read-Only. No autonomous circuit-breaker tripping, voltage regulation, or load shedding.",
        "forecast_uncertainty": "All energy forecasts must provide uncertainty intervals (lower and upper bounds) and documented baseline metrics (MAE/RMSE).",
        "macro_attribution": "Ember statistics represent national aggregate data and are not facility meter telemetry.",
    }


@router.post("/sites", status_code=201)
def create_site(
    payload: EnergySiteInput,
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("energis", principal) as conn:
        row = conn.execute(
            """INSERT INTO public.energy_sites
               (owner_id, site_code, name, site_type, latitude, longitude, country_code, source_ref)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (owner_id, site_code)
               DO UPDATE SET name = EXCLUDED.name, site_type = EXCLUDED.site_type
               RETURNING id, site_code, name, site_type, latitude, longitude, country_code, created_at""",
            (str(principal.user_id), payload.site_code, payload.name, payload.site_type, payload.latitude, payload.longitude, payload.country_code, payload.source_ref),
        ).fetchone()

        conn.execute(
            """INSERT INTO public.audit_events
               (owner_id, event_type, entity_type, entity_id, actor_type, details)
               VALUES (%s, 'energy_site_registered', 'energy_site', %s, 'user', %s::jsonb)""",
            (str(principal.user_id), str(row["id"]), json.dumps({"site_code": payload.site_code})),
        )
    return {"site": dict(row)}


@router.get("/sites")
def list_sites(
    limit: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("energis", principal) as conn:
        rows = conn.execute(
            """SELECT id, site_code, name, site_type, latitude, longitude, country_code, created_at
               FROM public.energy_sites WHERE owner_id = %s
               ORDER BY created_at DESC LIMIT %s""",
            (str(principal.user_id), limit),
        ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/meters", status_code=201)
def create_meter(
    payload: MeterInput,
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("energis", principal) as conn:
        site = conn.execute(
            "SELECT id FROM public.energy_sites WHERE owner_id = %s AND id = %s",
            (str(principal.user_id), str(payload.site_id)),
        ).fetchone()
        if not site:
            raise HTTPException(status_code=404, detail="Energy site not found or not owned by principal")

        row = conn.execute(
            """INSERT INTO public.meters (owner_id, site_id, meter_code, meter_type, unit)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (owner_id, meter_code)
               DO UPDATE SET meter_type = EXCLUDED.meter_type
               RETURNING id, site_id, meter_code, meter_type, unit""",
            (str(principal.user_id), str(payload.site_id), payload.meter_code, payload.meter_type, payload.unit),
        ).fetchone()
    return {"meter": dict(row)}


@router.post("/forecasts", status_code=201)
def record_forecast(
    payload: ForecastInput,
    principal: Principal = Depends(get_current_principal),
):
    if payload.lower_bound is not None and payload.upper_bound is not None:
        if payload.lower_bound > payload.upper_bound:
            raise HTTPException(status_code=422, detail="lower_bound must be less than or equal to upper_bound")

    with db_hub.user_connection("energis", principal) as conn:
        site = conn.execute(
            "SELECT id FROM public.energy_sites WHERE owner_id = %s AND id = %s",
            (str(principal.user_id), str(payload.site_id)),
        ).fetchone()
        if not site:
            raise HTTPException(status_code=404, detail="Energy site not found")

        row = conn.execute(
            """INSERT INTO public.forecasts
               (owner_id, site_id, target_metric, horizon_start, horizon_end,
                predicted_value, unit, lower_bound, upper_bound, model_name, model_version)
               VALUES (%s, %s, %s, now(), now() + interval '24 hours', %s, %s, %s, %s, %s, %s)
               RETURNING id, site_id, target_metric, horizon_start, horizon_end,
                         predicted_value, unit, lower_bound, upper_bound, model_name, model_version, created_at""",
            (
                str(principal.user_id),
                str(payload.site_id),
                payload.target_metric,
                payload.predicted_value,
                payload.unit,
                payload.lower_bound,
                payload.upper_bound,
                payload.model_name,
                payload.model_version,
            ),
        ).fetchone()
    return {"forecast": dict(row)}
