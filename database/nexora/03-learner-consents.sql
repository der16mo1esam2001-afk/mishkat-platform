-- Immutable learner-consent history for the first adult-only NEXORA pilot.
-- This migration is idempotent and must be applied to existing NEXORA volumes.
CREATE TABLE IF NOT EXISTS public.learner_consents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL,
  learner_id uuid NOT NULL,
  consent_type text NOT NULL CHECK (consent_type IN ('learning_profile_storage')),
  policy_version text NOT NULL CHECK (char_length(policy_version) BETWEEN 1 AND 40),
  granted boolean NOT NULL,
  locale text NOT NULL DEFAULT 'ar-EG',
  recorded_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(owner_id, id),
  FOREIGN KEY (owner_id, learner_id)
    REFERENCES public.learner_profiles(owner_id, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS learner_consents_owner_learner_time_idx
  ON public.learner_consents(owner_id, learner_id, recorded_at DESC);
ALTER TABLE public.learner_consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learner_consents FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS learner_consents_owner_isolation ON public.learner_consents;
CREATE POLICY learner_consents_owner_isolation ON public.learner_consents
  FOR SELECT TO mishkat_app
  USING (owner_id = app_private.current_user_id());
DROP POLICY IF EXISTS learner_consents_insert_own ON public.learner_consents;
CREATE POLICY learner_consents_insert_own ON public.learner_consents
  FOR INSERT TO mishkat_app
  WITH CHECK (owner_id = app_private.current_user_id());
REVOKE ALL ON public.learner_consents FROM PUBLIC;
GRANT SELECT, INSERT ON public.learner_consents TO mishkat_app;
