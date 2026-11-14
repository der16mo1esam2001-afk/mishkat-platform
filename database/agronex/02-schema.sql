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

CREATE TABLE public.farms (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 farm_code text NOT NULL, name text NOT NULL, area numeric, area_unit text DEFAULT 'ha', location geometry(Geometry,4326),
 country_code char(2), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(owner_id, farm_code),
 UNIQUE(owner_id, id)
);
CREATE TABLE public.plots (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 farm_id uuid NOT NULL,
 plot_code text NOT NULL, boundary geometry(Geometry,4326), area_ha numeric,
 soil_type text, irrigation_type text, UNIQUE(owner_id, farm_id, plot_code),
 UNIQUE(owner_id, id),
 FOREIGN KEY (owner_id, farm_id) REFERENCES public.farms(owner_id, id) ON DELETE CASCADE
);
CREATE TABLE public.crop_cycles (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 plot_id uuid NOT NULL,
 crop_code text NOT NULL, variety text, planting_date date, expected_harvest_date date,
 actual_harvest_date date, cycle_status text NOT NULL DEFAULT 'planned' CHECK (cycle_status IN ('planned','active','harvested','failed')),
 source_ref text,
 UNIQUE(owner_id, id),
 FOREIGN KEY (owner_id, plot_id) REFERENCES public.plots(owner_id, id) ON DELETE CASCADE
);
CREATE TABLE public.soil_samples (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 plot_id uuid NOT NULL,
 sampled_at timestamptz NOT NULL, parameter_code text NOT NULL, value numeric, unit text,
 lab_ref text, quality_status text NOT NULL DEFAULT 'unverified' CHECK (quality_status IN ('unverified','verified','rejected')),
 source_ref text NOT NULL,
 FOREIGN KEY (owner_id, plot_id) REFERENCES public.plots(owner_id, id) ON DELETE CASCADE
);
CREATE TABLE public.weather_observations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 observation_date date NOT NULL, parameter_code text NOT NULL, value numeric, unit text,
 latitude double precision NOT NULL, longitude double precision NOT NULL,
 source_id text NOT NULL, ingestion_run_id uuid, raw_value jsonb NOT NULL DEFAULT '{}'::jsonb,
 imported_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(owner_id, observation_date, parameter_code, latitude, longitude),
 FOREIGN KEY (owner_id, ingestion_run_id) REFERENCES public.ingestion_runs(owner_id, id) ON DELETE RESTRICT
);
CREATE TABLE public.irrigation_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 plot_id uuid NOT NULL,
 started_at timestamptz NOT NULL, duration_minutes integer CHECK (duration_minutes > 0),
 volume_m3 numeric CHECK (volume_m3 >= 0), method text, source_ref text,
 FOREIGN KEY (owner_id, plot_id) REFERENCES public.plots(owner_id, id) ON DELETE CASCADE
);
CREATE TABLE public.yield_records (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 crop_cycle_id uuid NOT NULL,
 harvested_at date NOT NULL, quantity numeric NOT NULL CHECK (quantity >= 0), unit text NOT NULL,
 quality_grade text, verified_by text, source_ref text NOT NULL,
 FOREIGN KEY (owner_id, crop_cycle_id) REFERENCES public.crop_cycles(owner_id, id) ON DELETE RESTRICT
);
CREATE TABLE public.disease_observations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL,
 crop_cycle_id uuid NOT NULL,
 observed_at timestamptz NOT NULL, suspected_condition text NOT NULL,
 model_version text, confidence numeric CHECK (confidence >= 0 AND confidence <= 1),
 expert_review_status text NOT NULL DEFAULT 'pending' CHECK (expert_review_status IN ('pending','confirmed','rejected')),
 image_ref text, source_ref text NOT NULL,
 FOREIGN KEY (owner_id, crop_cycle_id) REFERENCES public.crop_cycles(owner_id, id) ON DELETE CASCADE
);
CREATE INDEX farms_location_gix ON public.farms USING gist(location);
CREATE INDEX plots_boundary_gix ON public.plots USING gist(boundary);




ALTER TABLE public.farms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.farms FORCE ROW LEVEL SECURITY;
CREATE POLICY farms_owner_isolation ON public.farms FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.farms TO mishkat_app;

ALTER TABLE public.plots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.plots FORCE ROW LEVEL SECURITY;
CREATE POLICY plots_owner_isolation ON public.plots FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.plots TO mishkat_app;

ALTER TABLE public.crop_cycles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crop_cycles FORCE ROW LEVEL SECURITY;
CREATE POLICY crop_cycles_owner_isolation ON public.crop_cycles FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.crop_cycles TO mishkat_app;

ALTER TABLE public.soil_samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.soil_samples FORCE ROW LEVEL SECURITY;
CREATE POLICY soil_samples_owner_isolation ON public.soil_samples FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.soil_samples TO mishkat_app;

ALTER TABLE public.weather_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weather_observations FORCE ROW LEVEL SECURITY;
CREATE POLICY weather_observations_owner_isolation ON public.weather_observations FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.weather_observations TO mishkat_app;

ALTER TABLE public.irrigation_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.irrigation_events FORCE ROW LEVEL SECURITY;
CREATE POLICY irrigation_events_owner_isolation ON public.irrigation_events FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.irrigation_events TO mishkat_app;

ALTER TABLE public.yield_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yield_records FORCE ROW LEVEL SECURITY;
CREATE POLICY yield_records_owner_isolation ON public.yield_records FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.yield_records TO mishkat_app;

ALTER TABLE public.disease_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.disease_observations FORCE ROW LEVEL SECURITY;
CREATE POLICY disease_observations_owner_isolation ON public.disease_observations FOR ALL TO mishkat_app USING (owner_id = app_private.current_user_id()) WITH CHECK (owner_id = app_private.current_user_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.disease_observations TO mishkat_app;
