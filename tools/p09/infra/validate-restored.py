#!/usr/bin/env python3
"""Read disposable QA credentials only on stdin; report no tokens/passwords or response bodies."""
import json,sys,urllib.request
data=json.load(sys.stdin)
request=urllib.request.Request('http://127.0.0.1:18180/api/career',data=json.dumps({'operation':'login','username':data['username'],'password':data['password']}).encode(),
    headers={'Content-Type':'application/json','X-Forwarded-For':'127.0.0.1','X-Forwarded-Proto':'https'},method='POST')
with urllib.request.urlopen(request,timeout=15) as response: value=json.load(response)
if not value['ok'] or value['profile']['profileId']!=data['profileId'] or value['profile']['credits']!=data['credits']:
    raise RuntimeError('Restored account validation failed')
print(json.dumps({'status':'passed','restoredAccountLogin':True,'identityAndCreditsPreserved':True}))
