import json
import urllib.request
import urllib.error

url = 'http://127.0.0.1:8001/api/chat'
message = 'Bana bir dişçi randevusu ayarla'
body = json.dumps({'message': message}).encode('utf-8')
req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        text = resp.read().decode('utf-8')
        print(text)
except urllib.error.HTTPError as e:
    print('HTTP ERROR', e.code)
    print(e.read().decode('utf-8', errors='replace'))
except Exception as exc:
    import traceback
    traceback.print_exc()
