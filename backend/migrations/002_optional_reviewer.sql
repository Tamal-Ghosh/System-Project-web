ALTER TABLE public.doctor_assessments
    ALTER COLUMN reviewer_name DROP NOT NULL;

ALTER TABLE public.doctor_assessments
    DROP CONSTRAINT IF EXISTS doctor_assessments_reviewer_name_check;

ALTER TABLE public.doctor_assessments
    ADD CONSTRAINT doctor_assessments_reviewer_name_check
    CHECK (reviewer_name IS NULL OR char_length(reviewer_name) BETWEEN 2 AND 120);

COMMENT ON COLUMN public.doctor_assessments.reviewer_user_id IS
    'Populated from the authenticated doctor account when authentication is enabled.';
