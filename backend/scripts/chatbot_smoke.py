"""Opt-in local end-to-end smoke test with a generated nonclinical image."""
import io
import os
import time
from PIL import Image
import httpx


def main():
    stream = io.BytesIO()
    Image.new('RGB', (224,224), (120,90,80)).save(stream, format='PNG')
    with httpx.Client(base_url=os.getenv('SMOKE_BASE_URL', 'http://127.0.0.1:5180'), timeout=180) as client:
        started = time.perf_counter()
        response = client.post('/api/v1/analyses', data={'age':'40','sex':'unknown','site':'unknown'}, files={'image':('synthetic.png',stream.getvalue(),'image/png')})
        if response.status_code == 422:
            response = client.post('/api/v1/analyses', data={'age':'40','sex':'male','site':'unknown'}, files={'image':('synthetic.png',stream.getvalue(),'image/png')})
        response.raise_for_status()
        result = response.json()
        headers = {'X-Case-Token':result['assistant_access_token']}
        body = {'analysis_id':result['analysis_id'],'question':'what is the prediction'}
        t = time.perf_counter()
        direct = client.post('/api/v1/chat/query', json=body, headers=headers)
        direct.raise_for_status()
        assert result['leading_class'] in direct.json()['answer']
        print('Direct case answer seconds:',round(time.perf_counter()-t,2))
        denied = client.post('/api/v1/chat/query',json=body)
        assert denied.status_code == 403
        feedback = client.post('/api/v1/chat/feedback',json={'analysis_id':result['analysis_id'],'message_id':direct.json()['message_id'],'rating':'helpful'},headers=headers)
        feedback.raise_for_status()
        history = client.get('/api/v1/chat/history/'+result['analysis_id'],headers=headers)
        history.raise_for_status()
        assert len(history.json()) == 1
        technical = client.post('/api/v1/chat/query',json={**body,'question':'What are the limitations of this model and its calibration?'},headers=headers)
        technical.raise_for_status()
        assert technical.json()['citations']
        print('Knowledge answer status:',technical.json()['status'])
        print('Sources retrieved:',len(technical.json()['citations']))
        print('End-to-end seconds:',round(time.perf_counter()-started,2))


if __name__ == '__main__':
    main()
