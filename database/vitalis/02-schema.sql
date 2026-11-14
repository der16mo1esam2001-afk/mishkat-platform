-- Common ownership, audit and row-level isolation layer.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS app_private;
REVOKE ALL ON SCHEMA app_private FROM PUBLIC;
GRANT USAGE ON SCHEMA app_private TO mishkat_app;
GRANT USAGE ON SCHEMA public TO mishkat_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM mishkat_app;

CREATE OR REPLACE FUNCTION app_private.current_user_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('mishkat.user_id', true), '')::uuid
$$;
REVOKE ALL ON FUNCTION app_private.current_user_id() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app_private.current_user_id() TO mishkat_app;

CREATE TABLE IF NOT EXISTS public.audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL,
  event_type text NOT NULL CHECK (char_length(event_type) BETWEEN 1 AND 100),
  entity_type text NOT NULL CHECK (char_length(entity_type) BETWEEN 1 AND 100),
  entity_id text,
  actor_type text NOT NULL DEFAULT 'user' CHECK (actor_type IN ('user','system','integration')),
  source_id text,
  correlation_id uuid,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS audit_events_owner_time_idx ON public.audit_events(owner_id, occurred_at DESC);
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_events FORCE ROW LEVEL SECURITY;
CREATE POLICY audit_events_select_own ON public.audit_events FOR SELECT TO mishkat_app
  USING (owner_id = app_private.current_user_id());
CREATE POLICY audit_events_insert_own ON public.audit_events FOR INSERT TO mishkat_app
  WITH CHECK (owner_id = app_private.current_user_id());

GRANT SELECT, INSERT ON public.audit_events TO mishkat_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO mishkat_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO mishkat_app;

-- Provenance for every imported source run and registry for evaluated models.
CREATE TABLE IF NOT EXISTS public.ingestion_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL,
  source_id text NOT NULL,
  target_dataset text NOT NULL,
  status text NOT NULL CHECK (status IN ('queued','running','completed','failed','partial')),
  requested_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  finished_at timestamptz,
  records_received integer NOT NULL DEFAULT 0 CHECK (records_received >= 0),
  records_saved integer NOT NULL DEFAULT 0 CHECK (records_saved >= 0),
  request_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  license_snapshot text,
  error_code text,
  CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
);
CREATE INDEX IF NOT EXISTS ingestion_runs_owner_time_idx ON public.ingestion_runs(owner_id, requested_at DESC);
ALTER TABLE public.ingestion_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingestion_runs FORCE ROW LEVEL SECURITY;
CREATE POLICY ingestion_runs_owner_isolation ON public.ingestion_runs FOR ALL TO mishkat_app
  USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.ingestion_runs TO mishkat_app;

CREATE TABLE IF NOT EXISTS public.model_registry (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL,
  model_key text NOT NULL,
  model_version text NOT NULL,
  use_case text NOT NULL,
  model_type text NOT NULL,
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','evaluating','validated','suspended','retired')),
  training_data_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  evaluation_metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  known_limitations text,
  approved_by text,
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(owner_id, model_key, model_version)
);
CREATE INDEX IF NOT EXISTS model_registry_owner_key_idx ON public.model_registry(owner_id, model_key);
ALTER TABLE public.model_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_registry FORCE ROW LEVEL SECURITY;
CREATE POLICY model_registry_owner_isolation ON public.model_registry FOR ALL TO mishkat_app
  USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.model_registry TO mishkat_app;

CREATE TABLE public.patient_profiles (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 pseudonymous_ref text NOT NULL, age_band text, sex_code text,
 consent_status text NOT NULL DEFAULT 'pending' CHECK (consent_status IN ('pending','granted','withdrawn','expired')),
 data_classification text NOT NULL DEFAULT 'sensitive' CHECK (data_classification IN ('sensitive','restricted')),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id, pseudonymous_ref),
 UNIQUE(owner_id, id)
);
CREATE TABLE public.encounters (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 patient_id uuid NOT NULL,
 encounter_ref text NOT NULL, started_at timestamptz NOT NULL, ended_at timestamptz,
 care_setting text, status text NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','in_progress','completed','cancelled')),
 source_ref text, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(owner_id, encounter_ref),
 UNIQUE(owner_id, id),
 FOREIGN KEY (owner_id, patient_id) REFERENCES public.patient_profiles(owner_id, id) ON DELETE RESTRICT
);
CREATE TABLE public.clinical_observations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 patient_id uuid NOT NULL,
 encounter_id uuid,
 code_system text NOT NULL, code text NOT NULL, display text, value_numeric numeric,
 value_text text, unit text, effective_at timestamptz NOT NULL,
 source_ref text NOT NULL, fhir_resource_id text,
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK (value_numeric IS NOT NULL OR value_text IS NOT NULL),
 FOREIGN KEY (owner_id, patient_id) REFERENCES public.patient_profiles(owner_id, id) ON DELETE RESTRICT,
 FOREIGN KEY (owner_id, encounter_id) REFERENCES public.encounters(owner_id, id) ON DELETE RESTRICT
);
CREATE TABLE public.care_plans (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 patient_id uuid NOT NULL,
 title text NOT NULL, plan_status text NOT NULL CHECK (plan_status IN ('draft','active','on_hold','completed','cancelled')),
 reviewed_by text, reviewed_at timestamptz, next_review_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY (owner_id, patient_id) REFERENCES public.patient_profiles(owner_id, id) ON DELETE RESTRICT
);
CREATE TABLE public.consent_records (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 patient_id uuid NOT NULL,
 purpose text NOT NULL, policy_version text NOT NULL,
 status text NOT NULL CHECK (status IN ('granted','withdrawn','expired')),
 recorded_at timestamptz NOT NULL DEFAULT now(), evidence_ref text,
 FOREIGN KEY (owner_id, patient_id) REFERENCES public.patient_profiles(owner_id, id) ON DELETE RESTRICT
);
CREATE INDEX clinical_observations_patient_time_idx ON public.clinical_observations(owner_id, patient_id, effective_at DESC);




ALTER TABLE public.patient_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.patient_profiles FORCE ROW LEVEL SECURITY;
CREATE POLICY patient_profiles_owner_isolation ON public.patient_profiles FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.patient_profiles TO mishkat_app;

ALTER TABLE public.encounters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.encounters FORCE ROW LEVEL SECURITY;
CREATE POLICY encounters_owner_isolation ON public.encounters FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.encounters TO mishkat_app;

ALTER TABLE public.clinical_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clinical_observations FORCE ROW LEVEL SECURITY;
CREATE POLICY clinical_observations_owner_isolation ON public.clinical_observations FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.clinical_observations TO mishkat_app;

ALTER TABLE public.care_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.care_plans FORCE ROW LEVEL SECURITY;
CREATE POLICY care_plans_owner_isolation ON public.care_plans FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.care_plans TO mishkat_app;

ALTER TABLE public.consent_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consent_records FORCE ROW LEVEL SECURITY;
CREATE POLICY consent_records_owner_isolation ON public.consent_records FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.consent_records TO mishkat_app;
