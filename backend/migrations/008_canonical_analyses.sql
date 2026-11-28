-- Backend-owned development snapshots. No browser-facing RLS policies are granted.
CREATE TABLE IF NOT EXISTS public.analyses (
    id uuid PRIMARY KEY,
    owner_user_id uuid REFERENCES auth.users(id),
    model_version text NOT NULL,
    input_hash text NOT NULL CHECK (input_hash ~ '^[0-9a-f]{64}$'),
    response_snapshot jsonb NOT NULL CHECK (jsonb_typeof(response_snapshot) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.analysis_explanations (
    id uuid PRIMARY KEY,
    analysis_id uuid NOT NULL REFERENCES public.analyses(id),
    model_version text NOT NULL,
    input_hash text NOT NULL CHECK (input_hash ~ '^[0-9a-f]{64}$'),
    evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS analysis_explanations_analysis_idx
    ON public.analysis_explanations (analysis_id, created_at DESC);
ALTER TABLE public.analysis_explanations ENABLE ROW LEVEL SECURITY;
