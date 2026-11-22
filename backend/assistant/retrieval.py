"""Small-corpus local hybrid retrieval with cosine similarity and BM25/RRF."""
import json
import math
import re
from collections import Counter


def tokens(text):
    return re.findall(r'\w+', text.casefold())


class HybridRetriever:
    def __init__(self, store, embedder):
        self.store, self.embedder = store, embedder

    def search(self, question, limit=5, model_version=None, intent=None, class_label=None):
        if not question.strip() or not 1 <= limit <= 10:
            raise ValueError('Question and a limit between 1 and 10 are required')
        rows = self.store.approved_chunks()
        if not rows:
            return []
        if any(row[3] != self.embedder.model for row in rows):
            raise ValueError('Knowledge embedding model mismatch; rebuild the index')
        query = self.embedder.embed_query(question)
        documents = [(row[0], json.loads(row[1]), json.loads(row[2])) for row in rows]
        if model_version is not None:
            documents = [(identity, payload, vector) for identity, payload, vector in documents
                         if payload.get('source', {}).get('document_type') != 'model_card'
                         or payload.get('source', {}).get('version') == model_version]
        if intent == 'disease' and class_label:
            documents = [(identity,payload,vector) for identity,payload,vector in documents
                         if payload.get('source',{}).get('document_type') != 'model_card'
                         and re.search(r'(?<!\w)'+re.escape(class_label)+r'(?!\w)',payload['heading'],re.I)]
        if intent == 'disease':
            rich = [item for item in documents if item[1].get('source',{}).get('document_type')=='clinical_class_summary']
            if rich:documents=rich
        if not documents:
            return []
        if any(len(vector) != len(query) for _, _, vector in documents):
            raise ValueError('Knowledge embedding dimension mismatch')
        counts = [Counter(tokens(payload['content'])) for _, payload, _ in documents]
        lengths = [sum(count.values()) for count in counts]
        average = sum(lengths) / len(lengths) or 1
        terms = set(tokens(question))
        lexical, dense = {}, {}
        query_norm = math.sqrt(sum(x*x for x in query))
        if not query_norm:
            raise ValueError('Zero query vector')
        for index, (identity, payload, vector) in enumerate(documents):
            norm = math.sqrt(sum(x*x for x in vector))
            dense[identity] = sum(a*b for a,b in zip(query, vector)) / (query_norm * norm) if norm else 0
            score = 0
            for term in terms:
                frequency = counts[index][term]
                occurrence = sum(term in count for count in counts)
                idf = math.log(1 + (len(counts)-occurrence+.5)/(occurrence+.5))
                score += idf * frequency * 2.2 / (frequency + 1.2*(.25+.75*lengths[index]/average))
            lexical[identity] = score
        fused = Counter()
        for values in (dense, lexical):
            ranked = sorted((key for key in values if values[key] > 0), key=lambda key: (-values[key], key))[:15]
            for rank, identity in enumerate(ranked, 1):
                fused[identity] += 1 / (60 + rank)
        lookup = {identity: payload for identity, payload, _ in documents}
        results, seen = [], set()
        for identity, score in fused.most_common():
            payload = lookup[identity]
            if payload['content'] in seen:
                continue
            seen.add(payload['content'])
            results.append({'chunk_id': identity, 'heading': payload['heading'],
                            'excerpt': payload['content'], 'start': payload['start'],
                            'end': payload['end'], 'retrieval_score': score, 'source': payload.get('source', {}),
                            'reference_urls': ([payload['source']['source_url'] + '?version=' + payload['source']['version']] if payload.get('source',{}).get('document_type') == 'model_card' and payload.get('source',{}).get('source_url') == '/api/v1/model/reference' else list(dict.fromkeys(url.rstrip('.,;') for url in re.findall(r'https://[^\s)>]+', payload['content']))))})
            if len(results) == limit:
                break
        return results
