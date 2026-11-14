from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from ...database import db_hub
from ...security import Principal, get_current_principal

router = APIRouter(prefix="/aquanex", tags=["aquanex-water"])


class WaterAssetInput(BaseModel):
    asset_code: str = Field(min_length=3, max_length=64)
    asset_type: Literal["pipeline", "pump", "reservoir", "valve", "treatment_plant", "meter", "other"]
    status: Literal["active", "inactive", "maintenance", "unknown"] = "active"
    capacity_value: float | None = Field(default=None, ge=0)
    capacity_unit: str | None = Field(default="m3/day", max_length=24)
    source_ref: str = Field(min_length=2, max_length=120)

    @field_validator("asset_code")
    @classmethod
    def clean_code(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("asset_code cannot be blank")
        return cleaned


class TelemetryReadingInput(BaseModel):
    asset_id: UUID | None = None
    sensor_ref: str = Field(min_length=3, max_length=64)
    metric_code: Literal["FLOW_RATE", "PRESSURE", "WATER_LEVEL", "TURBIDITY", "PH", "CHLORINE"]
    value: float
    unit: str = Field(min_length=1, max_length=24)
    quality_flag: Literal["valid", "suspect", "invalid", "unreviewed"] = "unreviewed"
    source_ref: str = Field(min_length=2, max_length=120)


class WaterSampleInput(BaseModel):
    sample_ref: str = Field(min_length=3, max_length=64)
    parameter_code: str = Field(min_length=2, max_length=32)
    value: float
    unit: str = Field(min_length=1, max_length=24)
    method: str | None = Field(default=None, max_length=120)
    laboratory_ref: str | None = Field(default=None, max_length=120)
    source_ref: str = Field(min_length=2, max_length=120)


class WaterAlertVerificationInput(BaseModel):
    status: Literal["open", "acknowledged", "resolved", "false_positive"]
    human_verified: bool
    notes: str | None = Field(default=None, max_length=500)


@router.get("/safety-policy")
def aquanex_safety_policy():
    return {
        "domain": "AQUANEX",
        "scope": "Water resources and distribution intelligence",
        "scada_mode": "Strictly Read-Only",
        "actuation_allowed": False,
        "leak_detection_rule": "Anomalies remain 'suspected leak' until physical or acoustic field verification",
        "wri_indicators": "Sub-basin risk indicators represent strategic risk, not real-time pipe pressure",
    }


@router.post("/assets", status_code=201)
def register_water_asset(
    payload: WaterAssetInput,
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("aquanex", principal) as conn:
        row = conn.execute(
            """INSERT INTO public.water_assets
               (owner_id, asset_code, asset_type, status, capacity_value, capacity_unit, source_ref)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (owner_id, asset_code)
               DO UPDATE SET status = EXCLUDED.status, capacity_value = EXCLUDED.capacity_value
               RETURNING id, asset_code, asset_type, status, capacity_value, capacity_unit, created_at""",
            (str(principal.user_id), payload.asset_code, payload.asset_type, payload.status, payload.capacity_value, payload.capacity_unit, payload.source_ref),
        ).fetchone()

        conn.execute(
            """INSERT INTO public.audit_events
               (owner_id, event_type, entity_type, entity_id, actor_type, details)
               VALUES (%s, 'water_asset_registered', 'water_asset', %s, 'user', %s::jsonb)""",
            (str(principal.user_id), str(row["id"]), json.dumps({"asset_code": payload.asset_code})),
        )
    return {"asset": dict(row)}


@router.get("/assets")
def list_water_assets(
    limit: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("aquanex", principal) as conn:
        rows = conn.execute(
            """SELECT id, asset_code, asset_type, status, capacity_value, capacity_unit, created_at
               FROM public.water_assets
               WHERE owner_id = %s
               ORDER BY created_at DESC LIMIT %s""",
            (str(principal.user_id), limit),
        ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/telemetry", status_code=201)
def record_telemetry(
    payload: TelemetryReadingInput,
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("aquanex", principal) as conn:
        if payload.asset_id:
            asset = conn.execute(
                "SELECT id FROM public.water_assets WHERE owner_id = %s AND id = %s",
                (str(principal.user_id), str(payload.asset_id)),
            ).fetchone()
            if not asset:
                raise HTTPException(status_code=404, detail="Water asset not found")

        row = conn.execute(
            """INSERT INTO public.telemetry_readings
               (owner_id, asset_id, sensor_ref, metric_code, value, unit, measured_at, quality_flag, source_ref)
               VALUES (%s, %s, %s, %s, %s, %s, now(), %s, %s)
               ON CONFLICT (owner_id, sensor_ref, metric_code, measured_at)
               DO UPDATE SET value = EXCLUDED.value, quality_flag = EXCLUDED.quality_flag
               RETURNING id, sensor_ref, metric_code, value, unit, measured_at, quality_flag""",
            (str(principal.user_id), str(payload.asset_id) if payload.asset_id else None,
             payload.sensor_ref, payload.metric_code, payload.value, payload.unit, payload.quality_flag, payload.source_ref),
        ).fetchone()
    return {"reading": dict(row)}


@router.patch("/alerts/{alert_id}")
def verify_water_alert(
    alert_id: UUID,
    payload: WaterAlertVerificationInput,
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("aquanex", principal) as conn:
        row = conn.execute(
            """UPDATE public.water_alerts
               SET status = %s, human_verified = %s,
                   evidence = evidence || %s::jsonb,
                   resolved_at = CASE WHEN %s IN ('resolved', 'false_positive') THEN now() ELSE NULL END
               WHERE owner_id = %s AND id = %s
               RETURNING id, alert_type, severity, status, human_verified, created_at, resolved_at""",
            (payload.status, payload.human_verified, json.dumps({"verification_notes": payload.notes}), payload.status, str(principal.user_id), str(alert_id)),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found or not owned by principal")

        conn.execute(
            """INSERT INTO public.audit_events
               (owner_id, event_type, entity_type, entity_id, actor_type, details)
               VALUES (%s, 'water_alert_reviewed', 'water_alert', %s, 'user', %s::jsonb)""",
            (str(principal.user_id), str(alert_id), json.dumps({"status": payload.status, "verified": payload.human_verified})),
        )
    return {"alert": dict(row)}
