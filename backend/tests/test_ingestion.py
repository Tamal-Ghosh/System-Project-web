import tempfile
from pathlib import Path
import unittest
from assistant.ingestion import LocalKnowledgeStore, Source, section_chunks


class TestEmbedder:
    model = 'test-only-v1'
    def embed(self, texts):
        return [[1., 0.] for text in texts]


class IngestionTests(unittest.TestCase):
    def test_parent_and_offsets(self):
        chunks = section_chunks('# First\none two three four five\n# Second\nsix seven', 3, 1)
        self.assertEqual([c['heading'] for c in chunks], ['First', 'First', 'Second'])
        for chunk in chunks:
            self.assertEqual(chunk['parent_text'][chunk['start']:chunk['end']], chunk['content'])

    def test_approval_idempotency_and_immutable_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.md'
            path.write_text('# Model\nSynthetic test evidence', encoding='utf-8')
            store = LocalKnowledgeStore(Path(directory) / 'knowledge.sqlite')
            source = Source('Test', 'v1', 'urn:test:model', 'test-only', 'model_card')
            identity = store.ingest(path, source, TestEmbedder())
            self.assertEqual(store.approved_chunks(), [])
            self.assertEqual(store.ingest(path, source, TestEmbedder()), identity)
            store.approve(identity, 'test reviewer')
            self.assertEqual(len(store.approved_chunks()), 1)
            path.write_text('Changed content', encoding='utf-8')
            with self.assertRaises(ValueError):
                store.ingest(path, source, TestEmbedder())

    def test_invalid_vectors_leave_no_document(self):
        class Broken(TestEmbedder):
            def embed(self, texts):
                return [[float('nan')]]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.txt'
            path.write_text('Synthetic evidence', encoding='utf-8')
            store = LocalKnowledgeStore(Path(directory) / 'knowledge.sqlite')
            with self.assertRaises(ValueError):
                store.ingest(path, Source('Test', 'v1', 'urn:test', 'test', 'test'), Broken())
            self.assertEqual(store.approved_chunks(), [])
