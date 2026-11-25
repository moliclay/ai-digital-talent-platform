"""Exercise actual ChatAI HTTP streaming against the isolated acceptance server."""
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:18080'

def request(path, body=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    return urllib.request.urlopen(urllib.request.Request(BASE + path, data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None, headers=headers), timeout=180)

def data(path, body=None, token=None):
    with request(path, body, token) as res:
        payload = json.load(res)
        assert payload['code'] == 0, payload['message']
        return payload['data']

assert data('/api/health')['env'] == 'test', 'Acceptance server required'
token = data('/api/auth/login', {'username': 'hr_zhao', 'password': '123456'})['token']
sid = data('/api/chat/sessions', {'title': 'ChatAI 合成数据验收'}, token)['id']
for question in ['查找拥有 Python 技能的人才', '那工作经验至少三年的呢？', '语义检索有大模型开发经验的人才']:
    events = []
    with request(f'/api/chat/sessions/{sid}/messages', {'question': question}, token) as res:
        assert res.headers.get_content_type() == 'text/event-stream'
        for line in res:
            if line.startswith(b'data: '):
                events.append(json.loads(line[6:]))
    print(question, [e['type'] for e in events], flush=True)
    assert events[0]['type'] == 'meta'
    assert events[-1] == {'type': 'done', 'status': 'success'}, events[-2:]
    assert any(e['type'] == 'delta' and e['text'].strip() for e in events)
    assert any(e['type'] == 'sources' and e['source_refs'] for e in events), 'Expected business references'
restored = data(f'/api/chat/sessions/{sid}', token=token)['conversations']
assert len(restored) == 3 and all(r['status'] == 'success' for r in restored)
print('PASS: real SSE, three business turns, sources and restored history', flush=True)
