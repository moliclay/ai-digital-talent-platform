"""Verify actual client disconnect releases an isolated chat session."""
import json
import time
import urllib.request

BASE = 'http://127.0.0.1:18080'

def request(path, body=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    return urllib.request.urlopen(urllib.request.Request(BASE + path, data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None, headers=headers), timeout=120)

def data(path, body=None, token=None):
    with request(path, body, token) as response:
        payload = json.load(response)
        assert payload['code'] == 0, payload
        return payload['data']

assert data('/api/health')['env'] == 'test'
token = data('/api/auth/login', {'username':'hr_zhao','password':'123456'})['token']
sid = data('/api/chat/sessions', {'title':'取消验收'}, token)['id']
path = f'/api/chat/sessions/{sid}'
with request(path+'/messages', {'question':'查询有 Python 技能的人才'}, token) as response:
    line = response.readline()
    assert json.loads(line[6:])['type'] == 'meta'
    response.readline()
# Normal HTTP disconnect after the meta event.
for _ in range(60):
    turns = data(path, token=token)['conversations']
    if turns and turns[-1]['status'] not in ('pending', 'streaming'):
        break
    time.sleep(0.5)
assert turns[-1]['status'] == 'cancelled', turns[-1]['status']
with request(path+'/messages', {'question':'查询有 Python 技能的人才'}, token) as response:
    frames = [json.loads(line[6:]) for line in response if line.startswith(b'data: ')]
assert frames[-1]['status'] == 'success', frames[-1]
print('PASS: real cancellation persisted and same session accepts next turn')
