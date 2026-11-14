from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from ...database import db_hub
from ...security import Principal, get_current_principal

router = APIRouter(prefix="/nexora", tags=["nexora-knowledge"])

NEXORA_CONSENT_POLICY_VERSION = "2026-11-14-v1"


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


class AssessmentInput(BaseModel):
    path_id: UUID | None = None
    title: str = Field(min_length=3, max_length=160)
    assessment_type: Literal["diagnostic", "formative", "summative", "retention"] = "diagnostic"
    rubric_version: str = Field(default="v1.0", max_length=32)


class MasteryRecordInput(BaseModel):
    competency_code: str = Field(min_length=2, max_length=64)
    mastery_estimate: float = Field(ge=0.0, le=1.0)
    method: Literal["rubric_evaluation", "bayesian_knowledge_tracing", "item_response_theory"] = "rubric_evaluation"
    uncertainty: float | None = Field(default=0.1, ge=0.0, le=1.0)


@router.get("/consent-policy")
def nexora_consent_policy(principal: Principal = Depends(get_current_principal)):
    return {
        "policy_version": NEXORA_CONSENT_POLICY_VERSION,
        "scope": "adult_only_learning_profile_pilot",
        "data_fields": ["display_name", "locale", "learning_goals", "learning_path_records", "assessments", "mastery"],
        "not_collected_by_this_pilot": ["government_id", "date_of_birth", "biometric_data", "school_records", "clinical_data"],
        "purpose": "Create a learner-owned profile and save learning goals, path descriptions, and mastery records in the isolated NEXORA database.",
        "ai_processing": "No external AI provider is connected by this pilot endpoint; no learner text is sent to a third-party LLM.",
        "withdrawal": "Consent can be withdrawn. New goal/path writes will then be blocked. Data deletion is supported via the delete endpoint.",
        "age_gate": "Adult self-attestation only; not an identity or age verification process. Do not register minors in this pilot.",
    }


@router.get("/profile")
def get_nexora_profile(principal: Principal = Depends(get_current_principal)):
    with db_hub.user_connection("nexora", principal) as conn:
        row = conn.execute(
            """SELECT id, display_name, locale, age_band, accessibility_preferences,
                      consent_status, created_at, updated_at
               FROM public.learner_profiles WHERE owner_id=%s""",
            (str(principal.user_id),),
        ).fetchone()
    return {"profile": dict(row) if row else None, "scope": "adult_pilot_only"}


@router.put("/profile")
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
            (str(principal.user_id), str(row["id"]), json.dumps({"locale": payload.locale, "consent": "granted", "age_gate": "adult_self_attested"})),
        )
    return {"profile": dict(row), "scope": "adult_pilot_only", "note": "Age is self-attested for this pilot; this is not an identity or age-verification service."}


@router.post("/profile/revoke-consent")
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


@router.delete("/profile/purge-data")
def purge_nexora_data(principal: Principal = Depends(get_current_principal)):
    """Permanent data deletion under Right to Be Forgotten."""
    with db_hub.user_connection("nexora", principal) as conn:
        profile = conn.execute(
            "SELECT id FROM public.learner_profiles WHERE owner_id=%s",
            (str(principal.user_id),),
        ).fetchone()
        if not profile:
            raise HTTPException(status_code=404, detail="Learner profile not found")

        # Delete dependent tenant-owned records
        conn.execute("DELETE FROM public.learning_goals WHERE owner_id=%s", (str(principal.user_id),))
        conn.execute("DELETE FROM public.learning_paths WHERE owner_id=%s", (str(principal.user_id),))
        conn.execute("DELETE FROM public.mastery_records WHERE owner_id=%s", (str(principal.user_id),))
        conn.execute("DELETE FROM public.learner_consents WHERE owner_id=%s", (str(principal.user_id),))
        conn.execute("DELETE FROM public.learner_profiles WHERE owner_id=%s", (str(principal.user_id),))

        conn.execute(
            """INSERT INTO public.audit_events
               (owner_id, event_type, entity_type, entity_id, actor_type, details)
               VALUES (%s, 'learner_data_purged', 'learner_profile', %s, 'user', %s::jsonb)""",
            (str(principal.user_id), str(profile["id"]), json.dumps({"action": "right_to_erasure_completed"})),
        )
    return {"status": "purged", "message": "All NEXORA learner data and goals have been permanently deleted."}


@router.get("/goals")
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


@router.post("/goals", status_code=201)
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
            (str(principal.user_id), str(row["id"]), json.dumps({"domain": payload.domain})),
        )
    return {"goal": dict(row)}


@router.patch("/goals/{goal_id}")
def update_nexora_goal(
    goal_id: UUID,
    status: Literal["active", "completed", "paused", "cancelled"],
    principal: Principal = Depends(get_current_principal),
):
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
            (str(principal.user_id), str(row["id"]), json.dumps({"status": status})),
        )
    return {"goal": dict(row)}


@router.get("/paths")
def list_nexora_paths(principal: Principal = Depends(get_current_principal)):
    with db_hub.user_connection("nexora", principal) as conn:
        rows = conn.execute(
            """SELECT id, title, domain, objective, status, created_at
               FROM public.learning_paths WHERE owner_id=%s ORDER BY created_at DESC""",
            (str(principal.user_id),),
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@router.post("/paths", status_code=201)
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
            (str(principal.user_id), str(row["id"]), json.dumps({"domain": payload.domain})),
        )
    return {"path": dict(row), "note": "This creates a learner-owned path record. It does not generate AI curriculum or licensed learning content."}


@router.post("/mastery", status_code=201)
def record_mastery(
    payload: MasteryRecordInput,
    principal: Principal = Depends(get_current_principal),
):
    with db_hub.user_connection("nexora", principal) as conn:
        profile = conn.execute(
            "SELECT id, consent_status FROM public.learner_profiles WHERE owner_id=%s",
            (str(principal.user_id),),
        ).fetchone()
        if not profile or profile["consent_status"] != "granted":
            raise HTTPException(status_code=409, detail="Learner consent required before recording mastery records.")

        row = conn.execute(
            """INSERT INTO public.mastery_records
               (owner_id, learner_id, competency_code, mastery_estimate, method, uncertainty, observed_at)
               VALUES (%s, %s, %s, %s, %s, %s, now())
               RETURNING id, competency_code, mastery_estimate, method, uncertainty, observed_at""",
            (str(principal.user_id), str(profile["id"]), payload.competency_code, payload.mastery_estimate, payload.method, payload.uncertainty),
        ).fetchone()
    return {"mastery": dict(row)}


@router.get("/export")
def export_nexora_data(principal: Principal = Depends(get_current_principal)):
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
