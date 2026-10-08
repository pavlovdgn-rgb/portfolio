# Notion (public recordMap JSON) -> static HTML for content/portfolio-site
import json, os, re, sys, html, urllib.parse, subprocess

RAW = sys.argv[1]
SITE = sys.argv[2]
DOWNLOAD = '--no-download' not in sys.argv
SPACE = 'c06d2023-0931-457f-9c2b-571d8141949d'
PROXY = 'https://pavlovdesign.notion.site/image/'

def nid(x): return x.replace('-', '')
def dash(i):
    i = nid(i); return f'{i[:8]}-{i[8:12]}-{i[12:16]}-{i[16:20]}-{i[20:]}'

# page id -> (output path, image dir, short name, parent page id)
PAGES = {
    '3f30f94b6c528183bb47ed7dc3dc8ecc': ('index.html', 'home', None),
    '3e30f94b6c5281e79e7cf3b23070e4fd': ('cases/bilet-beru.html', 'bilet-beru', '3f30f94b6c528183bb47ed7dc3dc8ecc'),
    '3e30f94b6c528172aa28e10c14df3116': ('cases/bilet-beru/market-research.html', 'bilet-beru/market-research', '3e30f94b6c5281e79e7cf3b23070e4fd'),
    '3e30f94b6c5281d5b695c0a5cbb4e11d': ('cases/bilet-beru/competitors.html', 'bilet-beru/competitors', '3e30f94b6c5281e79e7cf3b23070e4fd'),
    '3e30f94b6c52811a8514c31d6366a923': ('cases/bilet-beru/persona-jtbd-cjm.html', 'bilet-beru/persona-jtbd-cjm', '3e30f94b6c5281e79e7cf3b23070e4fd'),
    '3e30f94b6c52811f9597e61e735a957c': ('cases/bilet-beru/usability-testing.html', 'bilet-beru/usability-testing', '3e30f94b6c5281e79e7cf3b23070e4fd'),
    '3e30f94b6c528118814ed34950a5ee9b': ('cases/bilet-beru/design-system.html', 'bilet-beru/design-system', '3e30f94b6c5281e79e7cf3b23070e4fd'),
    '3f30f94b6c5281059d34f6ea2e67f7d1': ('cases/geovizor.html', 'geovizor', '3f30f94b6c528183bb47ed7dc3dc8ecc'),
    '3f30f94b6c52816ca01bf8e16d204125': ('cases/geovizor/roles-research.html', 'geovizor/roles-research', '3f30f94b6c5281059d34f6ea2e67f7d1'),
    '3f30f94b6c52815d9abcfc626c8a217b': ('cases/geovizor/competitors.html', 'geovizor/competitors', '3f30f94b6c5281059d34f6ea2e67f7d1'),
    '3f30f94b6c5281389ecbf8665571bb09': ('cases/geovizor/cjm-userflow.html', 'geovizor/cjm-userflow', '3f30f94b6c5281059d34f6ea2e67f7d1'),
    '3f30f94b6c5281ee8f06c13122c982b0': ('cases/geovizor/ia-sitemap.html', 'geovizor/ia-sitemap', '3f30f94b6c5281059d34f6ea2e67f7d1'),
    '3f30f94b6c52816ba4f2f1b9e68d6277': ('cases/geovizor/design-system.html', 'geovizor/design-system', '3f30f94b6c5281059d34f6ea2e67f7d1'),
    '3f30f94b6c5281dd97e6d17b8b2b53eb': ('cases/geovizor/usability.html', 'geovizor/usability', '3f30f94b6c5281059d34f6ea2e67f7d1'),
    '3f30f94b6c5281b3b8c8d55bad1c2122': ('cases/afisha.html', 'afisha', '3f30f94b6c528183bb47ed7dc3dc8ecc'),
}
INDEX = '3f30f94b6c528183bb47ed7dc3dc8ecc'
GEO = '3f30f94b6c5281059d34f6ea2e67f7d1'
# friendly names for images whose Notion file name is not readable / collides
RENAME = {
    '905f35f4a4224ba9813cb93a7bce28dd': 'afisha-preview.png',
    '555d4456aa744554...': None,
}
INDEX_IMG_NAMES = {  # preview images on the home page
    '6c1cb6bd47054591969efb5298c97186': 'bilet-beru-preview.png',
    '555d4456aa744554 99e507df6e02e5cf'.replace(' ', ''): 'geovizor-preview.png',
    '905f35f4a4224ba9813cb93a7bce28dd': 'afisha-preview.png',
    'b4f0337de20d4bffb9b63e254b1c191f': 'pavlov-photo.png',
}
LOCAL_VIDEO = {  # Notion external video -> local file (first source) + keep external as fallback
    'https://s3.twcstorage.ru/1e57ae7f-d44e-4eeb-b989-746d4a5fd828/flow1-light.mp4': 'assets/video/geovizor-flow1.mp4',
}
NOTION_VIDEO_DIR = 'assets/video'

DESCR = {
    INDEX: 'Павлов Алексей — продуктовый UX/UI дизайнер. Подборка продуктовых кейсов: от исследования и формулировки гипотезы до прототипа, тестирования и плана следующей итерации.',
}

blocks = {}
for pid in PAGES:
    blocks.update(json.load(open(os.path.join(RAW, pid + '.json'))))

def B(i): return blocks.get(dash(i)) or blocks.get(i)

def page_title(pid):
    v = B(pid)
    t = v.get('properties', {}).get('title')
    return ''.join(s[0] for s in t) if t else ''

def page_icon(pid):
    return (B(pid).get('format') or {}).get('page_icon', '')

downloads = []  # (url, dest)
used_names = {}

def rel(cur_path, target_path):
    r = os.path.relpath(target_path, os.path.dirname(cur_path) or '.')
    return r

def map_link(url, cur):
    m = re.search(r'(?:notion\.(?:so|site|com)[^\s]*?)([0-9a-f]{32})', url.replace('-', ''))
    if m and m.group(1) in PAGES:
        frag = ''
        return rel(cur, PAGES[m.group(1)][0]) + frag
    return url

def esc(s): return html.escape(s, quote=True)

COLOR = lambda c: c.replace('_background', '_bg').replace('teal', 'green')

def rich(t, cur):
    out = []
    for seg in t or []:
        text = seg[0]
        decs = seg[1] if len(seg) > 1 else []
        if text == '‣':
            for d in decs:
                if d[0] == 'p':
                    pid = nid(d[1])
                    if pid in PAGES:
                        out.append(f'<a class="n-mention" href="{esc(rel(cur, PAGES[pid][0]))}"><span class="n-mention-icon">{page_icon(pid)}</span><span class="n-mention-title">{esc(page_title(pid))}</span></a>')
                    else:
                        out.append('<span class="n-mention">[страница]</span>')
            continue
        h = esc(text).replace('\n', '<br>')
        link = None
        for d in decs:
            k = d[0]
            if k == 'b': h = f'<strong>{h}</strong>'
            elif k == 'i': h = f'<em>{h}</em>'
            elif k == 's': h = f'<s>{h}</s>'
            elif k == '_': h = f'<u>{h}</u>'
            elif k == 'c': h = f'<code>{h}</code>'
            elif k == 'h': h = f'<span class="c-{COLOR(d[1])}">{h}</span>'
            elif k == 'a': link = d[1]
        if link:
            href = map_link(link, cur)
            ext = href.startswith('http')
            attrs = ' target="_blank" rel="noopener"' if ext else ''
            h = f'<a class="n-link" href="{esc(href)}"{attrs}>{h}</a>'
        out.append(h)
    return ''.join(out)

def plain(t):
    return ''.join(s[0] for s in (t or []) if s[0] != '‣')

def title_of(v):
    return (v.get('properties') or {}).get('title')

def bcolor(v):
    c = (v.get('format') or {}).get('block_color')
    return f' c-{COLOR(c)}' if c and c != 'default' else ''

def slugify(s):
    s = s.lower()
    s = re.sub(r'[^0-9a-zа-яё]+', '-', s).strip('-')
    return s[:60] or 'h'

class Ctx:
    def __init__(self, pid):
        self.pid = pid; self.cur = PAGES[pid][0]; self.imgdir = PAGES[pid][1]
        self.headings = []; self.ids = set(); self.first_img = None

def collect_headings(pid, ctx):
    def walk(i):
        v = B(i)
        if not v: return
        if v['type'] in ('header', 'sub_header', 'sub_sub_header'):
            txt = plain(title_of(v))
            base = slugify(txt); hid = base; n = 2
            while hid in ctx.ids: hid = f'{base}-{n}'; n += 1
            ctx.ids.add(hid)
            ctx.headings.append((v['id'], {'header': 1, 'sub_header': 2, 'sub_sub_header': 3}[v['type']], txt, hid))
        if v['type'] in ('page', 'collection_view_page') and nid(v['id']) != pid: return
        for c in v.get('content') or []: walk(c)
    walk(pid)
    ctx.hid = {h[0]: h[3] for h in ctx.headings}

def img_src(v, ctx):
    src = (v.get('properties') or {}).get('source', [['']])[0][0]
    bid = nid(v['id'])
    if src.startswith('attachment:'):
        fname = src.split(':', 2)[2]
        name = INDEX_IMG_NAMES.get(bid) if ctx.pid == INDEX else None
        name = name or fname
        name = re.sub(r'[^A-Za-z0-9._-]+', '-', name)
        d = f'assets/img/{ctx.imgdir}'
        key = f'{d}/{name}'
        if key in used_names and used_names[key] != bid:
            stem, ext = os.path.splitext(name); k = 2
            while f'{d}/{stem}-{k}{ext}' in used_names: k += 1
            key = f'{d}/{stem}-{k}{ext}'
        used_names[key] = bid
        url = PROXY + urllib.parse.quote(src, safe='') + f'?table=block&id={dash(bid)}&spaceId={SPACE}&cache=v2'
        downloads.append((url, key))
        return key
    return src

def render_children(ids, ctx):
    out = []; i = 0
    ids = ids or []
    while i < len(ids):
        v = B(ids[i])
        if not v or not v.get('alive', True): i += 1; continue
        t = v['type']
        if t in ('bulleted_list', 'numbered_list'):
            tag = 'ul' if t == 'bulleted_list' else 'ol'
            items = []
            while i < len(ids) and B(ids[i]) and B(ids[i])['type'] == t:
                items.append(B(ids[i])); i += 1
            lis = ''.join(f'<li class="n-li{bcolor(it)}">{rich(title_of(it), ctx.cur)}{render_children(it.get("content"), ctx)}</li>' for it in items)
            out.append(f'<{tag} class="n-list n-{t}">{lis}</{tag}>')
            continue
        out.append(render_block(v, ctx)); i += 1
    return ''.join(out)

def render_table(v, ctx):
    f = v.get('format') or {}
    order = f.get('table_block_column_order') or []
    colfmt = f.get('table_block_column_format') or {}
    hrow = f.get('table_block_column_header'); hcol = f.get('table_block_row_header')
    fit = f.get('table_width') or True
    cols = []
    for c in order:
        cf = colfmt.get(c) or {}
        st = f' style="width:{cf["width"]}px"' if cf.get('width') else ''
        cc = f' class="c-{COLOR(cf["color"])}"' if cf.get('color') else ''
        cols.append(f'<col{st}{cc}>')
    rows = []
    for ri, r in enumerate(v.get('content') or []):
        rv = B(r)
        if not rv: continue
        props = rv.get('properties') or {}
        rc = bcolor(rv)
        cells = []
        for ci, c in enumerate(order):
            is_h = (hrow and ri == 0) or (hcol and ci == 0)
            cf = colfmt.get(c) or {}
            ccls = f' c-{COLOR(cf["color"])}' if cf.get('color') and not is_h else ''
            tag = 'th' if is_h else 'td'
            scope = ''
            if is_h: scope = ' scope="col"' if (hrow and ri == 0) else ' scope="row"'
            cells.append(f'<{tag}{scope} class="n-cell{ccls}">{rich(props.get(c), ctx.cur)}</{tag}>')
        rows.append(f'<tr class="n-tr{rc}">{"".join(cells)}</tr>')
    return f'<div class="n-table-wrap"><table class="n-table"><colgroup>{"".join(cols)}</colgroup><tbody>{"".join(rows)}</tbody></table></div>'

def render_block(v, ctx):
    t = v['type']; f = v.get('format') or {}
    T = title_of(v); bc = bcolor(v)
    kids = lambda: render_children(v.get('content'), ctx)
    if t == 'text':
        if not T and not v.get('content'):
            return '<div class="n-empty"></div>'
        return f'<p class="n-text{bc}">{rich(T, ctx.cur)}</p>' + (f'<div class="n-indent">{kids()}</div>' if v.get('content') else '')
    if t in ('header', 'sub_header', 'sub_sub_header'):
        tag = {'header': 'h2', 'sub_header': 'h3', 'sub_sub_header': 'h4'}[t]
        cls = {'header': 'n-h1', 'sub_header': 'n-h2', 'sub_sub_header': 'n-h3'}[t]
        if ctx.pid == INDEX: tag = {'header': 'h1', 'sub_header': 'h2', 'sub_sub_header': 'h3'}[t]
        return f'<{tag} id="{ctx.hid.get(v["id"], "")}" class="{cls}{bc}">{rich(T, ctx.cur)}</{tag}>'
    if t == 'divider':
        return '<hr class="n-divider">'
    if t == 'quote':
        return f'<blockquote class="n-quote{bc}">{rich(T, ctx.cur)}{kids()}</blockquote>'
    if t == 'callout':
        icon = f.get('page_icon', '')
        body = (f'<p class="n-text">{rich(T, ctx.cur)}</p>' if T else '') + kids()
        return f'<div class="n-callout{bc}"><div class="n-callout-icon" aria-hidden="true">{icon}</div><div class="n-callout-body">{body}</div></div>'
    if t == 'toggle':
        return f'<details class="n-toggle{bc}"><summary>{rich(T, ctx.cur)}</summary><div class="n-toggle-body">{kids()}</div></details>'
    if t == 'column_list':
        cols = [B(c) for c in v.get('content') or [] if B(c)]
        n = len(cols)
        parts = []
        for c in cols:
            ratio = (c.get('format') or {}).get('column_ratio') or (1 / n)
            parts.append(f'<div class="n-column" style="--r:{ratio:.4f}">{render_children(c.get("content"), ctx)}</div>')
        return f'<div class="n-columns" style="--n:{n}">{"".join(parts)}</div>'
    if t == 'image':
        src = img_src(v, ctx)
        cap = (v.get('properties') or {}).get('caption')
        alt = plain(cap) if cap else ''
        if not alt:
            alt = page_title(ctx.pid) if ctx.pid != INDEX else ''
            if ctx.pid == INDEX:
                alt = {'pavlov-photo': 'Павлов Алексей', 'bilet-beru-preview': 'Билет Беру — обложка кейса', 'geovizor-preview': 'ГЕОВИЗОР — обложка кейса', 'afisha-preview': '«Глобальная афиша» — обложка кейса'}.get(os.path.splitext(os.path.basename(src))[0], '')
        if ctx.first_img is None: ctx.first_img = src
        w = f.get('block_width')
        style = f' style="max-width:{int(w)}px"' if w and not ctx.pid == INDEX else ''
        capt = f'<figcaption>{rich(cap, ctx.cur)}</figcaption>' if cap else ''
        loading = '' if ctx.first_img == src else ' loading="lazy"'
        return f'<figure class="n-image"{style}><img src="{esc(rel(ctx.cur, src))}" alt="{esc(alt)}"{loading} decoding="async">{capt}</figure>'
    if t == 'video':
        src = (v.get('properties') or {}).get('source', [['']])[0][0]
        cap = (v.get('properties') or {}).get('caption')
        capt = f'<figcaption>{rich(cap, ctx.cur)}</figcaption>' if cap else ''
        sources = []
        if src.startswith('attachment:'):
            fname = src.split(':', 2)[2]
            stem = PAGES[ctx.pid][1].split('/')[0]
            local = f'{NOTION_VIDEO_DIR}/{stem}-{fname}'
            VIDEO_ATTACH.append((v, local))
            sources.append((rel(ctx.cur, local), 'video/mp4'))
        elif src in LOCAL_VIDEO:
            sources.append((rel(ctx.cur, LOCAL_VIDEO[src]), 'video/mp4'))
            sources.append((src, 'video/mp4'))
        else:
            sources.append((src, 'video/webm' if src.endswith('.webm') else 'video/mp4'))
        s = ''.join(f'<source src="{esc(u)}" type="{ty}">' for u, ty in sources)
        return f'<figure class="n-video"><video controls preload="metadata" playsinline>{s}</video>{capt}</figure>'
    if t == 'table':
        return render_table(v, ctx)
    if t == 'table_of_contents':
        items = ''.join(f'<li class="toc-l{lvl}"><a href="#{hid}">{esc(txt)}</a></li>' for _, lvl, txt, hid in ctx.headings)
        return f'<nav class="n-toc{bc}" aria-label="Оглавление"><ul>{items}</ul></nav>'
    if t == 'page':
        pid = nid(v['id'])
        if pid in PAGES:
            return f'<a class="n-page-link" href="{esc(rel(ctx.cur, PAGES[pid][0]))}"><span class="n-page-icon">{page_icon(pid) or "📄"}</span><span class="n-page-title">{esc(page_title(pid))}</span></a>'
        return ''
    if t == 'tab':
        tabs = [B(c) for c in v.get('content') or [] if B(c)]
        name = 'tabs-' + nid(v['id'])[:8]
        heads = []; panels = []
        for k, tb in enumerate(tabs):
            tid = f'{name}-{k}'
            chk = ' checked' if k == 0 else ''
            heads.append(f'<input type="radio" name="{name}" id="{tid}" class="n-tab-input"{chk}><label for="{tid}" class="n-tab-label"><span aria-hidden="true">{(tb.get("format") or {}).get("page_icon", "")}</span> {rich(title_of(tb), ctx.cur)}</label>')
            panels.append(f'<div class="n-tab-panel">{render_children(tb.get("content"), ctx)}</div>')
        return f'<div class="n-tabs" style="--tabs:{len(tabs)}">{"".join(heads)}<div class="n-tab-panels">{"".join(panels)}</div></div>'
    if t == 'collection_view_page':
        return ''  # linked Notion database (internal) - not exported
    return f'<!-- unsupported block {t} -->'

VIDEO_ATTACH = []

ICON_SVG = lambda e: "data:image/svg+xml," + urllib.parse.quote(f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>{e}</text></svg>")

def head(pid, ctx, title, descr, ogimg):
    cur = ctx.cur
    css = rel(cur, 'assets/css/style.css')
    fav = f'<link rel="icon" href="{esc(ICON_SVG(page_icon(pid)))}">' if page_icon(pid) else f'<link rel="icon" type="image/png" href="{esc(rel(cur, "assets/img/favicon.png"))}">'
    og = f'<meta property="og:image" content="{esc(rel(cur, ogimg))}">' if ogimg else ''
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(descr)}">
<meta name="color-scheme" content="light dark">
{fav}
<link rel="apple-touch-icon" href="{esc(rel(cur, 'assets/img/favicon.png'))}">
<meta property="og:type" content="{'website' if pid == INDEX else 'article'}">
<meta property="og:locale" content="ru_RU">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(descr)}">
{og}
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="{esc(css)}">
</head>
'''

def crumbs(pid, ctx):
    chain = []; p = pid
    while p:
        chain.append(p); p = PAGES[p][2]
    chain.reverse()
    parts = []
    for k, p in enumerate(chain):
        name = 'Кейсы' if p == INDEX else page_title(p)
        icon = '' if p == INDEX else f'<span class="crumb-icon" aria-hidden="true">{page_icon(p)}</span>'
        if p == pid:
            parts.append(f'<span class="crumb crumb-current" aria-current="page">{icon}{esc(name)}</span>')
        else:
            parts.append(f'<a class="crumb" href="{esc(rel(ctx.cur, PAGES[p][0]))}">{icon}{esc(name)}</a>')
    return '<span class="crumb-sep">/</span>'.join(parts)

def build(pid):
    ctx = Ctx(pid)
    collect_headings(pid, ctx)
    body = render_children(B(pid).get('content'), ctx)
    title = page_title(pid)
    if pid == INDEX:
        doc_title = 'Павлов Алексей — продуктовый UX/UI дизайнер · Кейсы'
        descr = DESCR[INDEX]
        og = 'assets/img/home/social-preview.png'
        hdr = ''
        cls = 'page-index'
    else:
        doc_title = title + ' — Павлов Алексей'
        par = PAGES[pid][2]
        coroto = None
        props = B(pid).get('properties') or {}
        # case pages: «Коротко» (database property) is the short description
        for k, val in props.items():
            if k != 'title' and isinstance(val, list) and val and isinstance(val[0], list) and len(plain(val)) > 60:
                coroto = plain(val); break
        if not coroto:
            first = next((plain(title_of(B(c))) for c in B(pid).get('content') or [] if B(c) and B(c)['type'] in ('text', 'callout') and len(plain(title_of(B(c)) or [])) > 60), '')
            if not first:
                # callout with children
                for c in B(pid).get('content') or []:
                    cv = B(c)
                    if cv and cv['type'] == 'callout':
                        for cc in cv.get('content') or []:
                            if B(cc) and len(plain(title_of(B(cc)))) > 60: first = plain(title_of(B(cc))); break
                    if first: break
            coroto = f'{title}. ' + (first or '') if par != INDEX else first
        descr = re.sub(r'\s+', ' ', coroto).strip()
        if len(descr) > 300: descr = descr[:297].rsplit(' ', 1)[0] + '…'
        og = ctx.first_img
        hdr = f'<header class="page-header"><div class="page-icon" aria-hidden="true">{page_icon(pid)}</div><h1 class="page-title">{esc(title)}</h1></header>'
        cls = 'page-case' if par == INDEX else 'page-artifact'
    html_doc = head(pid, ctx, doc_title, descr, og) + f'''<body class="{cls}">
<div class="topbar"><nav class="crumbs" aria-label="Навигация">{crumbs(pid, ctx)}</nav></div>
<main class="page">
{hdr}
<article class="page-content">
{body}
</article>
</main>
</body>
</html>
'''
    out = os.path.join(SITE, ctx.cur)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w').write(html_doc)
    return ctx

for pid in PAGES:
    build(pid)

# social preview of the home page (Notion "social media image")
sm = (B(INDEX).get('format') or {}).get('social_media_image_preview_url')
if sm:
    downloads.append((PROXY + urllib.parse.quote(sm, safe='') + f'?table=block&id={dash(INDEX)}&spaceId={SPACE}&cache=v2', 'assets/img/home/social-preview.png'))

json.dump({'images': downloads, 'videos': [[nid(v['id']), (v.get('properties') or {}).get('source', [['']])[0][0], local] for v, local in VIDEO_ATTACH]},
          open(os.path.join(RAW, '..', 'downloads.json'), 'w'), ensure_ascii=False, indent=1)
print('pages', len(PAGES), 'images', len(downloads), 'notion videos', len(VIDEO_ATTACH))
