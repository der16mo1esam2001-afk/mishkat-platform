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

CREATE TABLE public.energy_sites (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 site_code text NOT NULL, name text NOT NULL, site_type text NOT NULL CHECK (site_type IN ('building','factory','solar_plant','wind_plant','grid_asset','other')),
 latitude double precision, longitude double precision, country_code char(2), source_ref text,
 created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(owner_id, site_code),
 UNIQUE(owner_id, id)
);
CREATE TABLE public.meters (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 site_id uuid NOT NULL,
 meter_code text NOT NULL, meter_type text NOT NULL, unit text NOT NULL,
 commissioning_date date, source_ref text, UNIQUE(owner_id, meter_code),
 UNIQUE(owner_id, id),
 FOREIGN KEY (owner_id, site_id) REFERENCES public.energy_sites(owner_id, id) ON DELETE CASCADE
);
CREATE TABLE public.meter_readings (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 meter_id uuid NOT NULL,
 measured_at timestamptz NOT NULL, value numeric NOT NULL, unit text NOT NULL,
 interval_seconds integer CHECK (interval_seconds > 0), quality_flag text NOT NULL DEFAULT 'unreviewed' CHECK (quality_flag IN ('valid','suspect','invalid','unreviewed')),
 source_ref text NOT NULL, raw_record jsonb NOT NULL DEFAULT '{}'::jsonb,
 UNIQUE(owner_id, meter_id, measured_at),
 FOREIGN KEY (owner_id, meter_id) REFERENCES public.meters(owner_id, id) ON DELETE CASCADE
);
CREATE TABLE public.resource_observations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 observation_date date NOT NULL, parameter_code text NOT NULL, value numeric, unit text,
 latitude double precision NOT NULL, longitude double precision NOT NULL,
 source_id text NOT NULL, ingestion_run_id uuid, raw_value jsonb NOT NULL DEFAULT '{}'::jsonb,
 imported_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id, observation_date, parameter_code, latitude, longitude),
 FOREIGN KEY (owner_id, ingestion_run_id) REFERENCES public.ingestion_runs(owner_id, id) ON DELETE RESTRICT
);
CREATE TABLE public.generation_records (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 site_id uuid NOT NULL,
 period_start timestamptz NOT NULL, period_end timestamptz NOT NULL,
 energy_value numeric NOT NULL CHECK (energy_value >= 0), unit text NOT NULL,
 generation_source text NOT NULL, source_ref text NOT NULL,
 CHECK (period_end > period_start),
 FOREIGN KEY (owner_id, site_id) REFERENCES public.energy_sites(owner_id, id) ON DELETE RESTRICT
);
CREATE TABLE public.forecasts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 site_id uuid,
 target_metric text NOT NULL, horizon_start timestamptz NOT NULL, horizon_end timestamptz NOT NULL,
 predicted_value numeric NOT NULL, unit text NOT NULL, lower_bound numeric, upper_bound numeric,
 model_name text NOT NULL, model_version text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 CHECK (horizon_end > horizon_start), CHECK (lower_bound IS NULL OR upper_bound IS NULL OR lower_bound <= upper_bound),
 FOREIGN KEY (owner_id, site_id) REFERENCES public.energy_sites(owner_id, id) ON DELETE RESTRICT
);
CREATE TABLE public.anomalies (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 site_id uuid,
 anomaly_type text NOT NULL, severity text NOT NULL CHECK (severity IN ('info','low','medium','high','critical')),
 detected_at timestamptz NOT NULL, status text NOT NULL DEFAULT 'open' CHECK (status IN ('open','reviewed','resolved','false_positive')),
 human_reviewed boolean NOT NULL DEFAULT false, evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
 FOREIGN KEY (owner_id, site_id) REFERENCES public.energy_sites(owner_id, id) ON DELETE RESTRICT
);
CREATE INDEX meter_readings_time_idx ON public.meter_readings(owner_id, measured_at DESC);




ALTER TABLE public.energy_sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.energy_sites FORCE ROW LEVEL SECURITY;
CREATE POLICY energy_sites_owner_isolation ON public.energy_sites FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.energy_sites TO mishkat_app;

ALTER TABLE public.meters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meters FORCE ROW LEVEL SECURITY;
CREATE POLICY meters_owner_isolation ON public.meters FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.meters TO mishkat_app;

ALTER TABLE public.meter_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meter_readings FORCE ROW LEVEL SECURITY;
CREATE POLICY meter_readings_owner_isolation ON public.meter_readings FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.meter_readings TO mishkat_app;

ALTER TABLE public.resource_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resource_observations FORCE ROW LEVEL SECURITY;
CREATE POLICY resource_observations_owner_isolation ON public.resource_observations FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.resource_observations TO mishkat_app;

ALTER TABLE public.generation_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generation_records FORCE ROW LEVEL SECURITY;
CREATE POLICY generation_records_owner_isolation ON public.generation_records FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.generation_records TO mishkat_app;

ALTER TABLE public.forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.forecasts FORCE ROW LEVEL SECURITY;
CREATE POLICY forecasts_owner_isolation ON public.forecasts FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.forecasts TO mishkat_app;

ALTER TABLE public.anomalies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.anomalies FORCE ROW LEVEL SECURITY;
CREATE POLICY anomalies_owner_isolation ON public.anomalies FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.anomalies TO mishkat_app;
