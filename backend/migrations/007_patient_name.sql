ALTER TABLE public.doctor_assessments
    ADD COLUMN IF NOT EXISTS patient_name text;

ALTER TABLE public.doctor_assessments
    DROP CONSTRAINT IF EXISTS doctor_assessments_patient_name_check;

ALTER TABLE public.doctor_assessments
    ADD CONSTRAINT doctor_assessments_patient_name_check
    CHECK (patient_name IS NULL OR char_length(btrim(patient_name)) BETWEEN 2 AND 120);

ALTER TABLE public.prescriptions
    ADD COLUMN IF NOT EXISTS patient_name text;

ALTER TABLE public.prescriptions
    DROP CONSTRAINT IF EXISTS prescriptions_patient_name_check;

ALTER TABLE public.prescriptions
    ADD CONSTRAINT prescriptions_patient_name_check
    CHECK (patient_name IS NULL OR char_length(btrim(patient_name)) BETWEEN 2 AND 120);

COMMENT ON COLUMN public.doctor_assessments.patient_name IS
    'Patient display name captured for clinician-facing records and reports.';
COMMENT ON COLUMN public.prescriptions.patient_name IS
    'Patient display name snapshot used in the prescription document.';
