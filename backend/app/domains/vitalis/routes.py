from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from ...database import db_hub
from ...security import Principal, get_current_principal, require_role

router = APIRouter(prefix="/vitalis", tags=["vitalis-health"])


class PatientProfileInput(BaseModel):
    pseudonymous_ref: str = Field(min_length=3, max_length=64, description="De-identified patient reference")
    age_band: str | None = Field(default=None, pattern=r"^(18-29|30-44|45-59|60-74|75\+)$")
    sex_code: Literal["M", "F", "O", "UNK"] = "UNK"
    data_classification: Literal["sensitive", "restricted"] = "sensitive"

    @field_validator("pseudonymous_ref")
    @classmethod
    def clean_ref(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("pseudonymous_ref cannot be blank")
        return cleaned


class EncounterInput(BaseModel):
    patient_id: UUID
    encounter_ref: str = Field(min_length=3, max_length=64)
    care_setting: Literal["outpatient", "inpatient", "community", "virtual"] = "outpatient"
    status: Literal["planned", "in_progress", "completed", "cancelled"] = "planned"


class ClinicalObservationInput(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    code_system: Literal["LOINC", "SNOMED-CT", "LOCAL"] = "LOINC"
    code: str = Field(min_length=2, max_length=64)
    display: str | None = Field(default=None, max_length=200)
    value_numeric: float | None = None
    value_text: str | None = None
    unit: str | None = Field(default=None, max_length=32)
    source_ref: str = Field(min_length=2, max_length=120)

    @field_validator("value_numeric")
    @classmethod
    def validate_values(cls, v: float | None, info: Any) -> float | None:
        return v


class CarePlanInput(BaseModel):
    patient_id: UUID
    title: str = Field(min_length=3, max_length=160)
    plan_status: Literal["draft", "active", "on_hold", "completed", "cancelled"] = "draft"
    next_review_days: int = Field(default=30, ge=1, le=365)


@router.get("/safety-policy")
def vitalis_safety_policy():
    return {
        "domain": "VITALIS AI",
        "scope": "Clinical workflow support and preventive health intelligence",
        "autonomous_diagnosis": False,
        "autonomous_prescription": False,
        "interoperability_standard": "FHIR R5 (Draft IG)",
        "human_oversight": "Mandatory clinician review before any clinical action",
        "pseudonymization": "All patient profiles must use non-reversible de-identified references",
    }


@router.post("/patients", status_code=201)
def create_patient_profile(
    payload: PatientProfileInput,
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("vitalis", principal) as conn:
        row = conn.execute(
            """INSERT INTO public.patient_profiles
               (owner_id, pseudonymous_ref, age_band, sex_code, data_classification, consent_status)
               VALUES (%s, %s, %s, %s, %s, 'granted')
               ON CONFLICT (owner_id, pseudonymous_ref)
               DO UPDATE SET age_band = EXCLUDED.age_band, sex_code = EXCLUDED.sex_code, updated_at = now()
               RETURNING id, pseudonymous_ref, age_band, sex_code, consent_status, data_classification, created_at""",
            (str(principal.user_id), payload.pseudonymous_ref, payload.age_band, payload.sex_code, payload.data_classification),
        ).fetchone()

        conn.execute(
            """INSERT INTO public.audit_events
               (owner_id, event_type, entity_type, entity_id, actor_type, details)
               VALUES (%s, 'patient_profile_registered', 'patient_profile', %s, 'user', %s::jsonb)""",
            (str(principal.user_id), str(row["id"]), json.dumps({"ref": payload.pseudonymous_ref})),
        )
    return {"patient": dict(row)}


@router.get("/patients")
def list_patients(
    limit: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("vitalis", principal) as conn:
        rows = conn.execute(
            """SELECT id, pseudonymous_ref, age_band, sex_code, consent_status, data_classification, created_at
               FROM public.patient_profiles
               WHERE owner_id = %s
               ORDER BY created_at DESC LIMIT %s""",
            (str(principal.user_id), limit),
        ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/observations", status_code=201)
def record_observation(
    payload: ClinicalObservationInput,
    principal: Principal = Depends(get_current_principal),
):
    if payload.value_numeric is None and not payload.value_text:
        raise HTTPException(status_code=422, detail="Either value_numeric or value_text must be provided")

    fhir_representation = {
        "resourceType": "Observation",
        "status": "preliminary",
        "code": {"coding": [{"system": payload.code_system, "code": payload.code, "display": payload.display}]},
        "subject": {"reference": f"Patient/{payload.patient_id}"},
        "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
        "valueQuantity": {"value": payload.value_numeric, "unit": payload.unit} if payload.value_numeric is not None else None,
        "valueString": payload.value_text,
    }

    with db_hub.user_connection("vitalis", principal) as conn:
        # Verify patient belongs to owner
        patient = conn.execute(
            "SELECT id FROM public.patient_profiles WHERE owner_id = %s AND id = %s",
            (str(principal.user_id), str(payload.patient_id)),
        ).fetchone()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found or not owned by principal")

        row = conn.execute(
            """INSERT INTO public.clinical_observations
               (owner_id, patient_id, encounter_id, code_system, code, display,
                value_numeric, value_text, unit, effective_at, source_ref, fhir_resource_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), %s, %s)
               RETURNING id, patient_id, code, display, value_numeric, unit, effective_at, created_at""",
            (
                str(principal.user_id),
                str(payload.patient_id),
                str(payload.encounter_id) if payload.encounter_id else None,
                payload.code_system,
                payload.code,
                payload.display,
                payload.value_numeric,
                payload.value_text,
                payload.unit,
                payload.source_ref,
                str(uuid4()),
            ),
        ).fetchone()

        conn.execute(
            """INSERT INTO public.audit_events
               (owner_id, event_type, entity_type, entity_id, actor_type, details)
               VALUES (%s, 'clinical_observation_recorded', 'clinical_observation', %s, 'user', %s::jsonb)""",
            (str(principal.user_id), str(row["id"]), json.dumps({"code": payload.code})),
        )
    return {"observation": dict(row), "fhir_r5": fhir_representation}


@router.post("/care-plans", status_code=201)
def create_care_plan(
    payload: CarePlanInput,
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("vitalis", principal) as conn:
        patient = conn.execute(
            "SELECT id FROM public.patient_profiles WHERE owner_id = %s AND id = %s",
            (str(principal.user_id), str(payload.patient_id)),
        ).fetchone()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found")

        row = conn.execute(
            """INSERT INTO public.care_plans
               (owner_id, patient_id, title, plan_status, next_review_at)
               VALUES (%s, %s, %s, %s, now() + (%s || ' days')::interval)
               RETURNING id, patient_id, title, plan_status, next_review_at, created_at""",
            (str(principal.user_id), str(payload.patient_id), payload.title, payload.plan_status, payload.next_review_days),
        ).fetchone()
    return {"care_plan": dict(row)}
