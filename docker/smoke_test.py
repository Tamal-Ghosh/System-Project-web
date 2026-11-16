"""Real HTTP inference smoke; use synthetic pixels, never assert a diagnosis."""
import io
import json
import math
import os
import urllib.request
from PIL import Image

base=os.getenv('SMOKE_BASE_URL','http://127.0.0.1:8000').rstrip('/')
with urllib.request.urlopen(base+'/health',timeout=30) as response:
    assert json.load(response)['status']=='ready'
image=Image.new('RGB',(80,64))
image.putdata([((x*3)%256,(y*4)%256,((x+y)*2)%256) for y in range(64) for x in range(80)])
stream=io.BytesIO(); image.save(stream,format='PNG')
boundary='dermascope-smoke-boundary'
parts=[]
for key,value in [('age','40'),('sex','female'),('site','trunk')]:
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="smoke.png"\r\nContent-Type: image/png\r\n\r\n'.encode()+stream.getvalue()+b'\r\n')
parts.append(f'--{boundary}--\r\n'.encode())
request=urllib.request.Request(base+'/api/v1/analyses',data=b''.join(parts),headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
with urllib.request.urlopen(request,timeout=300) as response:
    result=json.load(response)
assert len(result['scores'])==11
assert result['ensemble']['member_count']==5
assert result['metadata']['site']=='trunk'
assert all(math.isfinite(row['score']) for row in result['scores'])
assert abs(sum(row['score'] for row in result['scores'])-1)<1e-5
print(json.dumps({k:result[k] for k in ['model_version','elapsed_ms','input_policy']},indent=2))
print('PASS: real five-fold HTTP prediction; this is not an accuracy test.')
