import tempfile
from pathlib import Path
import unittest
from assistant.ingestion import LocalKnowledgeStore, Source
from assistant.retrieval import HybridRetriever


class Embedder:
    model = 'test-only'
    def embed(self, texts):
        return [[1., 0.] if 'uncertainty' in text else [0., 1.] for text in texts]
    def embed_query(self, text):
        return self.embed([text])[0]


class RetrievalTests(unittest.TestCase):
    def test_approved_only_and_relevant_ranking(self):
        with tempfile.TemporaryDirectory() as directory:
            store = LocalKnowledgeStore(Path(directory)/'test.sqlite')
            retriever = HybridRetriever(store, Embedder())
            path = Path(directory)/'source.md'
            path.write_text('# Uncertainty\nuncertainty entropy margin\n# Image\nimage crop dimensions', encoding='utf-8')
            identity = store.ingest(path, Source('Synthetic', 'v1', 'urn:test', 'test', 'test'), Embedder())
            self.assertEqual(retriever.search('uncertainty'), [])
            store.approve(identity, 'test reviewer')
            hits = retriever.search('uncertainty')
            self.assertEqual(hits[0]['heading'], 'Uncertainty')
            self.assertIn('chunk_id', hits[0])
            retriever.embedder.model = 'different'
            with self.assertRaises(ValueError):
                retriever.search('uncertainty')

    def test_wrong_model_card_is_not_retrieved_for_new_model(self):
        with tempfile.TemporaryDirectory() as directory:
            store=LocalKnowledgeStore(Path(directory)/'test.sqlite')
            path=Path(directory)/'source.md'
            path.write_text('# Old technical card\nuncertainty old model internals',encoding='utf-8')
            old=store.ingest(path,Source('Old model','e38-test','urn:old','test','model_card'),Embedder())
            store.approve(old,'test reviewer')
            path.write_text('# General reference\nuncertainty interpretation',encoding='utf-8')
            general=store.ingest(path,Source('General','v1','urn:general','test','class_reference'),Embedder())
            store.approve(general,'test reviewer')
            hits=HybridRetriever(store,Embedder()).search('uncertainty',model_version='e55-test')
            self.assertEqual([hit['heading'] for hit in hits],['General reference'])
            self.assertEqual(hits[0]['source']['source_url'],'urn:general')

    def test_citations_preserve_original_source_links(self):
        with tempfile.TemporaryDirectory() as folder:
            store=LocalKnowledgeStore(Path(folder)/'test.sqlite');path=Path(folder)/'source.md'
            path.write_text('# Source section\nuncertainty reference https://example.org/reference',encoding='utf-8')
            identity=store.ingest(path,Source('Reference','v1','urn:summary','test','class_reference'),Embedder())
            store.approve(identity,'test reviewer')
            hit=HybridRetriever(store,Embedder()).search('uncertainty')[0]
            self.assertEqual(hit['reference_urls'],['https://example.org/reference'])


class DiseaseFilteringTests(unittest.TestCase):
    def test_clinical_query_excludes_wrong_class_and_model_card(self):
        import json
        class Store:
            def approved_chunks(self):
                return [(key,json.dumps({'heading':heading,'content':'clinical overview', 'start':0,'end':17,
                         'source':{'document_type':kind,'version':'v1','source_url':'https://example.org/'+key}}),'[0,1]','test-only')
                        for key,heading,kind in [('bcc','BCC overview','clinical_class_summary'),('mel','MEL overview','clinical_class_summary'),('card','BCC model','model_card')]]
        hits=HybridRetriever(Store(),Embedder()).search('BCC clinical overview',3,'v1','disease','BCC')
        self.assertEqual([hit['chunk_id'] for hit in hits],['bcc'])
