/* Service worker · généré par scripts/build.py · version 2026-09-05.2249
   Coquille et données : cache d'abord. Pages HTML : réseau d'abord, avec délai de garde
   de 3 s seulement si une copie en cache existe ; repli hors-ligne.html sinon.
   Toutes les URL sont relatives à la portée d'enregistrement (self.registration.scope). */
const VERSION = '2026-09-05.2249';
const SHELL = 'pea-shell-' + VERSION;
const PAGES = 'pea-pages-' + VERSION;
const PRECACHE = ["./", "index.html", "hors-ligne.html", "assets/css/styles.css", "manifest.webmanifest", "data/search-index.json", "assets/icons/favicon.svg", "assets/js/app.js", "assets/js/cite.js", "assets/js/evidence.js", "assets/js/figview.js", "assets/js/glossary.js", "assets/js/interactives.js", "assets/js/pwa.js", "assets/js/quiz.js", "assets/js/search.js", "assets/js/tables.js", "assets/js/wizard.js", "assets/fonts/literata-italic-latin-ext.woff2", "assets/fonts/literata-italic-latin.woff2", "assets/fonts/literata-normal-latin-ext.woff2", "assets/fonts/literata-normal-latin.woff2", "assets/fonts/public-sans-italic-latin-ext.woff2", "assets/fonts/public-sans-italic-latin.woff2", "assets/fonts/public-sans-normal-latin-ext.woff2", "assets/fonts/public-sans-normal-latin.woff2", "harcelement-scolaire/index.html", "glossaire.html", "references.html"];
const ALL_PAGES = ["harcelement-scolaire/01-grandir.html", "harcelement-scolaire/02-besoins-emotions-corps.html", "harcelement-scolaire/03-traumatisme-et-resilience.html", "harcelement-scolaire/04-harcelement-ou-conflit.html", "harcelement-scolaire/05-nommer-la-violence-madagascar.html", "harcelement-scolaire/06-selon-l-age.html", "harcelement-scolaire/07-chiffres-et-solidite.html", "harcelement-scolaire/08-consequences.html", "harcelement-scolaire/09-qui-est-expose.html", "harcelement-scolaire/10-ecrans-et-vie-en-ligne.html", "harcelement-scolaire/11-reperer.html", "harcelement-scolaire/12-parler-et-ecouter.html", "harcelement-scolaire/13-mon-enfant-est-concerne.html", "harcelement-scolaire/14-demander-de-l-aide.html", "harcelement-scolaire/15-prevenir-ce-qui-marche.html", "harcelement-scolaire/16-kit-de-sensibilisation.html", "harcelement-scolaire/17-ressources.html", "harcelement-scolaire/18-consolider.html", "harcelement-scolaire/methode-et-limites.html", "harcelement-scolaire/ethique-et-confidentialite.html"];
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
  // Les ressources versionnées (?v=BUILD_ID) doivent correspondre EXACTEMENT : sans cela, tant que
  // le nouveau service worker n'a pas pris la main, une page fraîche recevait l'ancienne feuille de
  // styles — figures sans couleur, boutons hors gabarit. Le repli « au plus proche » ne sert qu'hors ligne.
  const versionnee = new URL(req.url).searchParams.has('v');
  const cached = await caches.match(req, { ignoreSearch: !versionnee });
  if (cached) return cached;
  try {
    const res = await fetch(req);
    if (res.ok) { const c = await caches.open(SHELL); c.put(req, res.clone()); }
    return res;
  } catch (e) {
    if (versionnee) {
      const proche = await caches.match(req, { ignoreSearch: true });
      if (proche) return proche;
    }
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
