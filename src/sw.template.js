/* Service worker · généré par scripts/build.py · version __BUILD_ID__
   Coquille et données : cache d'abord. Pages HTML : réseau d'abord, avec délai de garde
   de 3 s seulement si une copie en cache existe ; repli hors-ligne.html sinon.
   Toutes les URL sont relatives à la portée d'enregistrement (self.registration.scope). */
const VERSION = '__BUILD_ID__';
const SHELL = 'pea-shell-' + VERSION;
const PAGES = 'pea-pages-' + VERSION;
const PRECACHE = __PRECACHE__;
const ALL_PAGES = __ALL_PAGES__;
const SCOPE = self.registration.scope;
const abs = (p) => new URL(p, SCOPE).href;

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL).then((c) => c.addAll(PRECACHE.map(abs)))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k.startsWith('pea-') && !k.endsWith(VERSION)).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('message', (event) => {
  const d = event.data || {};
  if (d.type === 'SKIP_WAITING') self.skipWaiting();
  if (d.type === 'PRECACHE_ALL') {
    event.waitUntil((async () => {
      const c = await caches.open(PAGES);
      let done = 0;
      for (const p of ALL_PAGES) {
        try { const r = await fetch(abs(p), { cache: 'no-cache' }); if (r.ok) await c.put(abs(p), r); } catch (e) { /* réseau absent */ }
        done += 1;
        if (event.source) event.source.postMessage({ type: 'PRECACHE_PROGRESS', done, total: ALL_PAGES.length });
      }
      if (event.source) event.source.postMessage({ type: 'PRECACHE_DONE', total: ALL_PAGES.length });
    })());
  }
});

const isHTML = (req) => req.mode === 'navigate' || (req.headers.get('accept') || '').includes('text/html');

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (isHTML(req)) {
    event.respondWith(networkFirstHTML(req));
    return;
  }
  event.respondWith(cacheFirst(req));
});

async function cacheFirst(req) {
  const cached = await caches.match(req, { ignoreSearch: true });
  if (cached) return cached;
  try {
    const res = await fetch(req);
    if (res.ok) { const c = await caches.open(SHELL); c.put(req, res.clone()); }
    return res;
  } catch (e) {
    return new Response('', { status: 504, statusText: 'hors ligne' });
  }
}

async function networkFirstHTML(req) {
  const cached = await caches.match(req, { ignoreSearch: true });
  const fetchPromise = fetch(req).then(async (res) => {
    if (res.ok) { const c = await caches.open(PAGES); c.put(req, res.clone()); }
    return res;
  });
  if (cached) {
    const guard = new Promise((resolve) => setTimeout(() => resolve(cached), 3000));
    try { return await Promise.race([fetchPromise, guard]); } catch (e) { return cached; }
  }
  try { return await fetchPromise; } catch (e) {
    const off = await caches.match(abs('hors-ligne.html'));
    return off || new Response('<h1>Hors ligne</h1>', { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
  }
}
