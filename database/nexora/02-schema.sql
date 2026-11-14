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

CREATE TABLE public.learner_profiles (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 display_name text, locale text NOT NULL DEFAULT 'ar-EG', age_band text,
 accessibility_preferences jsonb NOT NULL DEFAULT '{}'::jsonb,
 consent_status text NOT NULL DEFAULT 'pending' CHECK (consent_status IN ('pending','granted','withdrawn')),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id),
 UNIQUE(owner_id, id)
);
CREATE TABLE public.learning_goals (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 learner_id uuid NOT NULL,
 title text NOT NULL, domain text NOT NULL, target_date date, status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','paused','cancelled')),
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY (owner_id, learner_id) REFERENCES public.learner_profiles(owner_id, id) ON DELETE CASCADE
);
CREATE TABLE public.learning_resources (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 title text NOT NULL, creator text, resource_type text NOT NULL,
 language_code text, source_url text NOT NULL, license_name text,
 license_url text, rights_verified boolean NOT NULL DEFAULT false,
 source_publisher text, publication_year integer,
 metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id, id)
);
CREATE TABLE public.learning_paths (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 learner_id uuid NOT NULL,
 title text NOT NULL, domain text NOT NULL, objective text NOT NULL,
 status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','completed','paused')),
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id, id),
 FOREIGN KEY (owner_id, learner_id) REFERENCES public.learner_profiles(owner_id, id) ON DELETE CASCADE
);
CREATE TABLE public.learning_units (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 path_id uuid NOT NULL,
 resource_id uuid,
 title text NOT NULL, sequence_no integer NOT NULL CHECK (sequence_no > 0),
 activity_type text NOT NULL, estimated_minutes integer CHECK (estimated_minutes > 0),
 UNIQUE(owner_id, path_id, sequence_no),
 FOREIGN KEY (owner_id, path_id) REFERENCES public.learning_paths(owner_id, id) ON DELETE CASCADE,
 FOREIGN KEY (owner_id, resource_id) REFERENCES public.learning_resources(owner_id, id) ON DELETE RESTRICT
);
CREATE TABLE public.assessments (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 path_id uuid,
 title text NOT NULL, assessment_type text NOT NULL CHECK (assessment_type IN ('diagnostic','formative','summative','retention')),
 blueprint jsonb NOT NULL DEFAULT '{}'::jsonb, rubric_version text,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id, id),
 FOREIGN KEY (owner_id, path_id) REFERENCES public.learning_paths(owner_id, id) ON DELETE RESTRICT
);
CREATE TABLE public.assessment_attempts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 assessment_id uuid NOT NULL,
 learner_id uuid NOT NULL,
 score numeric, max_score numeric, answers jsonb NOT NULL DEFAULT '{}'::jsonb,
 started_at timestamptz NOT NULL DEFAULT now(), submitted_at timestamptz,
 grading_version text, CHECK (score IS NULL OR max_score IS NULL OR (score >= 0 AND score <= max_score)),
 UNIQUE(owner_id, id),
 FOREIGN KEY (owner_id, assessment_id) REFERENCES public.assessments(owner_id, id) ON DELETE CASCADE,
 FOREIGN KEY (owner_id, learner_id) REFERENCES public.learner_profiles(owner_id, id) ON DELETE CASCADE
);
CREATE TABLE public.mastery_records (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 learner_id uuid NOT NULL,
 competency_code text NOT NULL, mastery_estimate numeric CHECK (mastery_estimate BETWEEN 0 AND 1),
 evidence_attempt_id uuid,
 method text NOT NULL, observed_at timestamptz NOT NULL DEFAULT now(),
 uncertainty numeric CHECK (uncertainty IS NULL OR uncertainty BETWEEN 0 AND 1),
 FOREIGN KEY (owner_id, learner_id) REFERENCES public.learner_profiles(owner_id, id) ON DELETE CASCADE,
 FOREIGN KEY (owner_id, evidence_attempt_id) REFERENCES public.assessment_attempts(owner_id, id) ON DELETE RESTRICT
);
CREATE INDEX mastery_learner_skill_idx ON public.mastery_records(owner_id, learner_id, competency_code, observed_at DESC);




ALTER TABLE public.learner_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learner_profiles FORCE ROW LEVEL SECURITY;
CREATE POLICY learner_profiles_owner_isolation ON public.learner_profiles FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.learner_profiles TO mishkat_app;

ALTER TABLE public.learning_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_goals FORCE ROW LEVEL SECURITY;
CREATE POLICY learning_goals_owner_isolation ON public.learning_goals FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.learning_goals TO mishkat_app;

ALTER TABLE public.learning_resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_resources FORCE ROW LEVEL SECURITY;
CREATE POLICY learning_resources_owner_isolation ON public.learning_resources FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.learning_resources TO mishkat_app;

ALTER TABLE public.learning_paths ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_paths FORCE ROW LEVEL SECURITY;
CREATE POLICY learning_paths_owner_isolation ON public.learning_paths FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.learning_paths TO mishkat_app;

ALTER TABLE public.learning_units ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_units FORCE ROW LEVEL SECURITY;
CREATE POLICY learning_units_owner_isolation ON public.learning_units FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.learning_units TO mishkat_app;

ALTER TABLE public.assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessments FORCE ROW LEVEL SECURITY;
CREATE POLICY assessments_owner_isolation ON public.assessments FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.assessments TO mishkat_app;

ALTER TABLE public.assessment_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_attempts FORCE ROW LEVEL SECURITY;
CREATE POLICY assessment_attempts_owner_isolation ON public.assessment_attempts FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.assessment_attempts TO mishkat_app;

ALTER TABLE public.mastery_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mastery_records FORCE ROW LEVEL SECURITY;
CREATE POLICY mastery_records_owner_isolation ON public.mastery_records FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.mastery_records TO mishkat_app;
