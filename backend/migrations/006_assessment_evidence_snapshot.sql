ALTER TABLE public.doctor_assessments
    ADD COLUMN IF NOT EXISTS image_snapshot text,
    ADD COLUMN IF NOT EXISTS uncertainty jsonb,
    ADD COLUMN IF NOT EXISTS ensemble jsonb,
    ADD COLUMN IF NOT EXISTS input_policy text,
    ADD COLUMN IF NOT EXISTS tta boolean,
    ADD COLUMN IF NOT EXISTS limitations text[] NOT NULL DEFAULT '{}';

ALTER TABLE public.doctor_assessments
    DROP CONSTRAINT IF EXISTS doctor_assessments_image_snapshot_check;

ALTER TABLE public.doctor_assessments
    ADD CONSTRAINT doctor_assessments_image_snapshot_check
    CHECK (
        image_snapshot IS NULL OR (
            char_length(image_snapshot) <= 1500000
            AND image_snapshot ~ '^data:image/(jpeg|png|webp);base64,'
        )
    );

COMMENT ON COLUMN public.doctor_assessments.image_snapshot IS
    'Reduced-resolution image snapshot used in the immutable doctor report.';
COMMENT ON COLUMN public.doctor_assessments.uncertainty IS
    'Per-analysis entropy and top-two margin snapshot from the deployed model.';
COMMENT ON COLUMN public.doctor_assessments.ensemble IS
    'Per-analysis ensemble member count and agreement snapshot.';
