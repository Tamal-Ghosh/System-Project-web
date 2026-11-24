CREATE TABLE IF NOT EXISTS assistant.class_overviews (
 class_label text NOT NULL, language text NOT NULL CHECK(language IN ('en','bn')),
 version text NOT NULL, answer text NOT NULL,
 source_ids jsonb NOT NULL, source_checksums jsonb NOT NULL,
 PRIMARY KEY(class_label,language)
);
ALTER TABLE assistant.class_overviews ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON assistant.class_overviews FROM PUBLIC,anon,authenticated;
GRANT SELECT ON assistant.class_overviews TO dermascope_chat_runtime;
DO $block$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_policies WHERE schemaname='assistant' AND tablename='class_overviews' AND policyname='backend_reference_read') THEN
  CREATE POLICY backend_reference_read ON assistant.class_overviews FOR SELECT TO dermascope_chat_runtime USING(true);
 END IF;
END $block$;
