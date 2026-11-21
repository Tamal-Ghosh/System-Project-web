ALTER TABLE public.prescriptions
    ADD COLUMN IF NOT EXISTS analysis_id uuid,
    ADD COLUMN IF NOT EXISTS model_version text,
    ADD COLUMN IF NOT EXISTS leading_class text,
    ADD COLUMN IF NOT EXISTS patient_metadata jsonb;

UPDATE public.prescriptions AS prescription
SET analysis_id = assessment.analysis_id,
    model_version = assessment.model_version,
    leading_class = assessment.leading_class,
    patient_metadata = assessment.patient_metadata
FROM public.doctor_assessments AS assessment
WHERE prescription.assessment_id = assessment.id
  AND prescription.analysis_id IS NULL;

ALTER TABLE public.prescriptions
    ALTER COLUMN assessment_id DROP NOT NULL,
    ALTER COLUMN analysis_id SET NOT NULL,
    ALTER COLUMN model_version SET NOT NULL,
    ALTER COLUMN leading_class SET NOT NULL,
    ALTER COLUMN patient_metadata SET NOT NULL;

ALTER TABLE public.prescriptions
    DROP CONSTRAINT IF EXISTS prescriptions_assessment_id_fkey;

ALTER TABLE public.prescriptions
    ADD CONSTRAINT prescriptions_assessment_id_fkey
    FOREIGN KEY (assessment_id) REFERENCES public.doctor_assessments(id) ON DELETE SET NULL;

CREATE UNIQUE INDEX IF NOT EXISTS prescriptions_analysis_id_unique
    ON public.prescriptions (analysis_id);

COMMENT ON TABLE public.prescriptions IS
    'Clinician-authored prescriptions linked to a patient and model analysis; doctor assessment is optional.';
