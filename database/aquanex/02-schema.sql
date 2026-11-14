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

CREATE TABLE public.water_assets (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 asset_code text NOT NULL, asset_type text NOT NULL CHECK (asset_type IN ('pipeline','pump','reservoir','valve','treatment_plant','meter','other')),
 status text NOT NULL DEFAULT 'unknown' CHECK (status IN ('active','inactive','maintenance','unknown')),
 capacity_value numeric, capacity_unit text, location geometry(Geometry,4326),
 installed_at date, source_ref text, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id, asset_code),
 UNIQUE(owner_id, id)
);
CREATE TABLE public.telemetry_readings (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 asset_id uuid,
 sensor_ref text NOT NULL, metric_code text NOT NULL, value numeric, unit text NOT NULL,
 measured_at timestamptz NOT NULL, quality_flag text NOT NULL DEFAULT 'unreviewed' CHECK (quality_flag IN ('valid','suspect','invalid','unreviewed')),
 source_ref text NOT NULL, raw_record jsonb NOT NULL DEFAULT '{}'::jsonb,
 UNIQUE(owner_id, sensor_ref, metric_code, measured_at),
 FOREIGN KEY (owner_id, asset_id) REFERENCES public.water_assets(owner_id, id) ON DELETE RESTRICT
);
CREATE TABLE public.water_samples (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 sample_ref text NOT NULL, sampled_at timestamptz NOT NULL, location geometry(Geometry,4326),
 parameter_code text NOT NULL, value numeric, unit text, method text,
 laboratory_ref text, quality_status text NOT NULL DEFAULT 'pending' CHECK (quality_status IN ('pending','verified','rejected')),
 source_ref text NOT NULL, UNIQUE(owner_id, sample_ref, parameter_code)
);
CREATE TABLE public.water_alerts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 asset_id uuid,
 alert_type text NOT NULL, severity text NOT NULL CHECK (severity IN ('info','low','medium','high','critical')),
 status text NOT NULL DEFAULT 'open' CHECK (status IN ('open','acknowledged','resolved','false_positive')),
 evidence jsonb NOT NULL DEFAULT '{}'::jsonb, human_verified boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now(), resolved_at timestamptz,
 FOREIGN KEY (owner_id, asset_id) REFERENCES public.water_assets(owner_id, id) ON DELETE RESTRICT
);
CREATE TABLE public.work_orders (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 asset_id uuid NOT NULL,
 title text NOT NULL, priority text NOT NULL CHECK (priority IN ('low','normal','high','urgent')),
 status text NOT NULL DEFAULT 'open' CHECK (status IN ('open','assigned','in_progress','completed','cancelled')),
 assigned_to text, due_at timestamptz, completed_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY (owner_id, asset_id) REFERENCES public.water_assets(owner_id, id) ON DELETE RESTRICT
);
CREATE INDEX water_assets_location_gix ON public.water_assets USING gist(location);
CREATE INDEX water_telemetry_time_idx ON public.telemetry_readings(owner_id, measured_at DESC);




ALTER TABLE public.water_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.water_assets FORCE ROW LEVEL SECURITY;
CREATE POLICY water_assets_owner_isolation ON public.water_assets FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.water_assets TO mishkat_app;

ALTER TABLE public.telemetry_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telemetry_readings FORCE ROW LEVEL SECURITY;
CREATE POLICY telemetry_readings_owner_isolation ON public.telemetry_readings FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.telemetry_readings TO mishkat_app;

ALTER TABLE public.water_samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.water_samples FORCE ROW LEVEL SECURITY;
CREATE POLICY water_samples_owner_isolation ON public.water_samples FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.water_samples TO mishkat_app;

ALTER TABLE public.water_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.water_alerts FORCE ROW LEVEL SECURITY;
CREATE POLICY water_alerts_owner_isolation ON public.water_alerts FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.water_alerts TO mishkat_app;

ALTER TABLE public.work_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.work_orders FORCE ROW LEVEL SECURITY;
CREATE POLICY work_orders_owner_isolation ON public.work_orders FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.work_orders TO mishkat_app;
