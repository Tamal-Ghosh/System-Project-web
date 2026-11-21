ALTER TABLE public.doctor_assessments
    ADD COLUMN IF NOT EXISTS patient_id text;

ALTER TABLE public.doctor_assessments
    DROP CONSTRAINT IF EXISTS doctor_assessments_patient_id_check;

ALTER TABLE public.doctor_assessments
    ADD CONSTRAINT doctor_assessments_patient_id_check
    CHECK (patient_id IS NULL OR patient_id ~ '^[A-Za-z0-9][A-Za-z0-9_-]{2,39}$');

CREATE INDEX IF NOT EXISTS doctor_assessments_patient_id_created_idx
    ON public.doctor_assessments (patient_id, created_at DESC);

COMMENT ON COLUMN public.doctor_assessments.patient_id IS
    'External or system-generated patient identifier used to group assessed cases and reports.';
