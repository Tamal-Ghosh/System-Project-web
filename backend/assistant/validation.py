"""Deterministic output checks supplementing model instructions."""
import json
import re
from decimal import Decimal, InvalidOperation


def validate_answer(result, context):
    answer = result.get('answer', '')
    evidence = set()
    def collect(value):
        if type(value) in (int, float):
            evidence.add(Decimal(str(value)))
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)
    collect(context)
    # Accept only explicit presentation forms derived from current case values.
    # Never use a blanket numeric tolerance (which could validate another class's score).
    for item in context.get('scores', []):
        raw=Decimal(str(item['score']))
        for places in (1,2):
            evidence.add((raw*100).quantize(Decimal(10)**-places)/100)
    for raw_value in context.get('uncertainty',{}).values():
        if type(raw_value) in (int,float):
            evidence.add(Decimal(str(raw_value)).quantize(Decimal('.001')))
    # Reference numbers are allowed only from source passages the generator cites.
    for source in context.get('knowledge_sources',[]):
        for token in re.findall(r'(?<![\w])[+-]?\d+(?:\.\d+)?%?',source.get('excerpt','')):
            evidence.add(Decimal(token.rstrip('%'))/(100 if token.endswith('%') else 1))
    list_numbers = [(match.start(1),match.end(1)) for match in re.finditer(r'(?m)^[ \t]*(?:\*\*)?(\d{1,2})[.)](?:\*\*)?[ \t]+',answer)]
    numbers = re.finditer(r'(?<![\w])[+-]?\d+(?:\.\d+)?%?', answer)
    for match in numbers:
        if any(start <= match.start() < end for start,end in list_numbers):
            continue
        token=match.group()
        number = Decimal(token.rstrip('%')) / (100 if token.endswith('%') else 1)
        if number not in evidence:
            return {'status': 'unavailable', 'answer': 'The generated answer contained an unsupported number. Please use the exact classification or uncertainty results.', 'facts_used': []}
    if re.search(r'\b(?:take|apply|prescribe)\b.{0,35}\b(?:mg|tablet|daily|cream)\b', answer, re.I):
        return {'status': 'out_of_scope', 'answer': 'Medication instructions require a clinician-authored prescription.', 'facts_used': []}
    if context.get('xai') is None and re.search(r'\b(?:heatmap|attribution)\s+(?:shows|reveals|confirms)\b', answer, re.I):
        return {'status': 'unavailable', 'answer': 'No matching XAI evidence is available for this case.', 'facts_used': []}
    return result
