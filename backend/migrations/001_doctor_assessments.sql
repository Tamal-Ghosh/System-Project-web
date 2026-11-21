CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.doctor_assessments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id uuid NOT NULL,
    model_version text NOT NULL CHECK (char_length(model_version) BETWEEN 1 AND 160),
    leading_class text NOT NULL CHECK (char_length(leading_class) BETWEEN 1 AND 80),
    model_scores jsonb NOT NULL CHECK (jsonb_typeof(model_scores) = 'array'),
    patient_metadata jsonb NOT NULL CHECK (jsonb_typeof(patient_metadata) = 'object'),
    decision text NOT NULL CHECK (decision IN ('agree', 'disagree', 'unsure')),
    confidence smallint NOT NULL CHECK (confidence BETWEEN 1 AND 5),
    suspected_diagnosis text CHECK (suspected_diagnosis IS NULL OR char_length(suspected_diagnosis) <= 200),
    differential_diagnoses text[] NOT NULL DEFAULT '{}',
    clinical_note text CHECK (clinical_note IS NULL OR char_length(clinical_note) <= 2000),
    next_action text NOT NULL CHECK (next_action IN (
        'routine_follow_up', 'dermatology_referral', 'biopsy_consideration',
        'additional_assessment', 'other'
    )),
    reviewer_user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    reviewer_name text CHECK (reviewer_name IS NULL OR char_length(reviewer_name) BETWEEN 2 AND 120),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (cardinality(differential_diagnoses) <= 5)
);

CREATE INDEX IF NOT EXISTS doctor_assessments_created_at_idx
    ON public.doctor_assessments (created_at DESC);
CREATE INDEX IF NOT EXISTS doctor_assessments_analysis_id_idx
    ON public.doctor_assessments (analysis_id);

ALTER TABLE public.doctor_assessments ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.doctor_assessments IS
    'Immutable clinician review snapshots. Browser Data API access is denied until explicit auth policies are added.';
