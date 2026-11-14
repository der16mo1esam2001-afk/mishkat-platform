from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from ...database import db_hub
from ...security import Principal, get_current_principal

router = APIRouter(prefix="/agronex", tags=["agronex-agriculture"])


class FarmInput(BaseModel):
    farm_code: str = Field(min_length=3, max_length=64)
    name: str = Field(min_length=2, max_length=120)
    area: float | None = Field(default=None, gt=0)
    area_unit: str = Field(default="ha", max_length=16)
    country_code: str = Field(default="EG", min_length=2, max_length=2)


class PlotInput(BaseModel):
    farm_id: UUID
    plot_code: str = Field(min_length=2, max_length=64)
    area_ha: float | None = Field(default=None, gt=0)
    soil_type: str | None = Field(default=None, max_length=64)
    irrigation_type: Literal["drip", "sprinkler", "flood", "pivot", "rainfed"] = "drip"


class CropCycleInput(BaseModel):
    plot_id: UUID
    crop_code: str = Field(min_length=2, max_length=64)
    variety: str | None = Field(default=None, max_length=64)
    planting_date: date
    expected_harvest_date: date | None = None
    cycle_status: Literal["planned", "active", "harvested", "failed"] = "active"


class DiseaseObservationInput(BaseModel):
    crop_cycle_id: UUID
    suspected_condition: str = Field(min_length=3, max_length=160)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_ref: str = Field(min_length=2, max_length=120)


@router.get("/safety-policy")
def agronex_safety_policy():
    return {
        "domain": "AGRONEX",
        "scope": "Agricultural intelligence and crop monitoring",
        "chemical_recommendations": "Strictly Prohibited. No pesticide or fertilizer chemical dosages without official local regulatory licensing and agronomic expert sign-off.",
        "disease_labeling": "Image or telemetry models may only output 'suspected condition' with confidence; never 'confirmed' without expert/laboratory review.",
        "macro_data_boundary": "FAOSTAT and NASA POWER values represent macro/gridded statistics, not individual farm in-situ sensors.",
    }


@router.post("/farms", status_code=201)
def create_farm(
    payload: FarmInput,
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("agronex", principal) as conn:
        row = conn.execute(
            """INSERT INTO public.farms (owner_id, farm_code, name, area, area_unit, country_code)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (owner_id, farm_code)
               DO UPDATE SET name = EXCLUDED.name, area = EXCLUDED.area
               RETURNING id, farm_code, name, area, area_unit, country_code, created_at""",
            (str(principal.user_id), payload.farm_code, payload.name, payload.area, payload.area_unit, payload.country_code),
        ).fetchone()

        conn.execute(
            """INSERT INTO public.audit_events
               (owner_id, event_type, entity_type, entity_id, actor_type, details)
               VALUES (%s, 'farm_registered', 'farm', %s, 'user', %s::jsonb)""",
            (str(principal.user_id), str(row["id"]), json.dumps({"farm_code": payload.farm_code})),
        )
    return {"farm": dict(row)}


@router.get("/farms")
def list_farms(
    limit: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("agronex", principal) as conn:
        rows = conn.execute(
            """SELECT id, farm_code, name, area, area_unit, country_code, created_at
               FROM public.farms WHERE owner_id = %s
               ORDER BY created_at DESC LIMIT %s""",
            (str(principal.user_id), limit),
        ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/plots", status_code=201)
def create_plot(
    payload: PlotInput,
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("agronex", principal) as conn:
        farm = conn.execute(
            "SELECT id FROM public.farms WHERE owner_id = %s AND id = %s",
            (str(principal.user_id), str(payload.farm_id)),
        ).fetchone()
        if not farm:
            raise HTTPException(status_code=404, detail="Farm not found or not owned by principal")

        row = conn.execute(
            """INSERT INTO public.plots (owner_id, farm_id, plot_code, area_ha, soil_type, irrigation_type)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (owner_id, farm_id, plot_code)
               DO UPDATE SET area_ha = EXCLUDED.area_ha, soil_type = EXCLUDED.soil_type
               RETURNING id, farm_id, plot_code, area_ha, soil_type, irrigation_type""",
            (str(principal.user_id), str(payload.farm_id), payload.plot_code, payload.area_ha, payload.soil_type, payload.irrigation_type),
        ).fetchone()
    return {"plot": dict(row)}


@router.post("/disease-observations", status_code=201)
def record_disease_observation(
    payload: DiseaseObservationInput,
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("agronex", principal) as conn:
        cycle = conn.execute(
            "SELECT id FROM public.crop_cycles WHERE owner_id = %s AND id = %s",
            (str(principal.user_id), str(payload.crop_cycle_id)),
        ).fetchone()
        if not cycle:
            raise HTTPException(status_code=404, detail="Crop cycle not found")

        row = conn.execute(
            """INSERT INTO public.disease_observations
               (owner_id, crop_cycle_id, observed_at, suspected_condition, confidence, expert_review_status, source_ref)
               VALUES (%s, %s, now(), %s, %s, 'pending', %s)
               RETURNING id, crop_cycle_id, observed_at, suspected_condition, confidence, expert_review_status, source_ref""",
            (str(principal.user_id), str(payload.crop_cycle_id), payload.suspected_condition, payload.confidence, payload.source_ref),
        ).fetchone()

        conn.execute(
            """INSERT INTO public.audit_events
               (owner_id, event_type, entity_type, entity_id, actor_type, details)
               VALUES (%s, 'disease_suspected', 'disease_observation', %s, 'user', %s::jsonb)""",
            (str(principal.user_id), str(row["id"]), json.dumps({"condition": payload.suspected_condition})),
        )
    return {
        "observation": dict(row),
        "safety_advisory": "This condition is flagged as suspected. Confirm with an agricultural extension officer or laboratory before applying any interventions.",
    }
