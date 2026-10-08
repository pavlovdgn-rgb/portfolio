import json, os, sys, subprocess
d = json.load(open(sys.argv[1])); site = sys.argv[2]
bad = []
for url, key in d['images']:
    dest = os.path.join(site, key)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000: continue
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    r = subprocess.run(['curl', '-sL', '-m', '90', '--retry', '3', '-o', dest, '-w', '%{http_code} %{content_type}', url], capture_output=True, text=True)
    if not r.stdout.startswith('200') or 'image' not in r.stdout: bad.append((key, r.stdout))
    print(key, r.stdout, flush=True)
    import time; time.sleep(4)
print('BAD', bad)
