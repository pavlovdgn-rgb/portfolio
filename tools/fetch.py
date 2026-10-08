import json, sys, urllib.request, time, os
BASE='https://pavlovdesign.notion.site/api/v3/'
OUT=sys.argv[1]
def dash(i):
    i=i.replace('-','')
    return f'{i[:8]}-{i[8:12]}-{i[12:16]}-{i[16:20]}-{i[20:]}'
def post(ep, body):
    for a in range(4):
        try:
            r=urllib.request.Request(BASE+ep, data=json.dumps(body).encode(), headers={'content-type':'application/json','user-agent':'Mozilla/5.0'})
            return json.load(urllib.request.urlopen(r, timeout=40))
        except Exception as e:
            print('retry',ep,e); time.sleep(2)
    raise SystemExit('fail '+ep)
def val(x):
    x=x.get('value',x); return x.get('value',x) if isinstance(x,dict) and 'value' in x and isinstance(x['value'],dict) else x
PAGES=sys.argv[2:]
for pid in PAGES:
    pid=dash(pid)
    blocks={}
    d=post('loadCachedPageChunkV2',{"page":{"id":pid},"limit":500,"cursor":{"stack":[]},"verticalColumns":False})
    for k,x in d['recordMap'].get('block',{}).items(): blocks[k]=val(x)
    # fill missing
    while True:
        need=[]
        stack=[pid]; seen=set()
        while stack:
            b=stack.pop()
            if b in seen: continue
            seen.add(b)
            if b not in blocks: need.append(b); continue
            v=blocks[b]
            if v['type'] in ('page','collection_view_page','collection_view') and b!=pid: continue
            stack+= v.get('content',[]) or []
        if not need: break
        print(pid,'missing',len(need))
        for i in range(0,len(need),100):
            r=post('syncRecordValuesMain',{"requests":[{"pointer":{"table":"block","id":n},"version":-1} for n in need[i:i+100]]})
            got=r.get('recordMap',{}).get('block',{})
            if not got: raise SystemExit('no records '+json.dumps(r)[:300])
            for k,x in got.items(): blocks[k]=val(x)
    json.dump(blocks, open(os.path.join(OUT,pid.replace('-','')+'.json'),'w'), ensure_ascii=False)
    print(pid, len(blocks))
