const { chromium } = require('/Users/alex/Documents/Claude_environ_EGTM/design-system/react/node_modules/playwright');
const fs = require('fs'), path = require('path');
const SITE = process.argv[2], OUT = process.argv[3], SHOTS = (process.argv[4]||'').split(',').filter(Boolean);
const files = [];
(function walk(d){ for (const f of fs.readdirSync(d)) { const p = path.join(d,f); if (fs.statSync(p).isDirectory()) walk(p); else if (p.endsWith('.html')) files.push(p); } })(SITE);
(async () => {
  const b = await chromium.launch();
  const problems = [];
  for (const scheme of ['light']) {
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: scheme });
  const p = await ctx.newPage();
  const failed = [];
  p.on('requestfailed', r => { if (r.url().startsWith('file:')) failed.push(r.url()); });
  p.on('console', m => { if (m.type()==='error') problems.push('console '+m.text()); });
  for (const f of files) {
    const rel = path.relative(SITE, f);
    await p.goto('file://' + f, { waitUntil: 'load' });
    // force lazy images to load
    await p.evaluate(async () => { document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading='eager'); document.querySelectorAll('details').forEach(d=>d.open=true); });
    await p.waitForFunction(() => [...document.images].every(i => i.complete), null, { timeout: 60000 }).catch(()=>problems.push(rel+': images timeout'));
    const res = await p.evaluate(() => {
      const broken = [...document.images].filter(i => !i.naturalWidth).map(i => i.getAttribute('src'));
      const links = [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href'));
      const vids = [...document.querySelectorAll('video source')].map(s => s.getAttribute('src'));
      const overflow = document.documentElement.scrollWidth > window.innerWidth;
      const notion = links.filter(h => /notion\.(so|site|com)/.test(h));
      return { broken, links, vids, overflow, notion, imgs: document.images.length };
    });
    for (const s of res.broken) problems.push(`${rel}: broken img ${s}`);
    for (const h of res.notion) problems.push(`${rel}: notion link left ${h}`);
    for (const h of [...res.links, ...res.vids, ...res.broken]) {
      if (/^(https?:|mailto:|tel:|#)/.test(h)) continue;
      const target = path.resolve(path.dirname(f), h.split('#')[0]);
      if (!fs.existsSync(target)) problems.push(`${rel}: missing local ${h}`);
      const hash = h.split('#')[1];
      if (hash) { /* anchors checked below */ }
    }
    const anchors = await p.evaluate(() => [...document.querySelectorAll('a[href^="#"]')].filter(a => !document.getElementById(decodeURIComponent(a.getAttribute('href').slice(1)))).map(a=>a.getAttribute('href')));
    for (const a of anchors) problems.push(`${rel}: dead anchor ${a}`);
    console.log(rel, 'imgs', res.imgs, 'links', res.links.length, 'ext', res.links.filter(h=>/^https?:/.test(h)).join(' '));
  }
  for (const u of failed) problems.push('requestfailed ' + u);
  await ctx.close();
  }
  // screenshots
  for (const [w, h, tag] of [[1440, 900, '1440'], [390, 844, '390']]) {
    for (const scheme of ['light', 'dark']) {
      if (scheme === 'dark' && w !== 1440) continue;
      const ctx = await b.newContext({ viewport: { width: w, height: h }, colorScheme: scheme, deviceScaleFactor: 1 });
      const p = await ctx.newPage();
      for (const s of SHOTS) {
        await p.goto('file://' + path.join(SITE, s), { waitUntil: 'load' });
        await p.evaluate(() => document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading='eager'));
        await p.waitForFunction(() => [...document.images].every(i => i.complete), null, { timeout: 60000 }).catch(()=>{});
        const ov = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        if (ov > 0) problems.push(`${s} @${w}: horizontal overflow ${ov}px`);
        const name = s.replace(/\//g, '_').replace('.html', '') + `-${tag}-${scheme}`;
        await p.screenshot({ path: path.join(OUT, name + '.png'), fullPage: false });
        await p.screenshot({ path: path.join(OUT, name + '-full.png'), fullPage: true });
      }
      await ctx.close();
    }
  }
  await b.close();
  console.log('PROBLEMS', problems.length); problems.forEach(x => console.log(' -', x));
})();
