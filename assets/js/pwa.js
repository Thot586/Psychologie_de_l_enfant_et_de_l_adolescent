/* pwa.js — service worker (updateViaCache none), pré-chargement hors ligne sur demande,
   bandeau de mise à jour, détection du navigateur intégré, état du réseau. */
const $ = (s, c = document) => c.querySelector(s);
const banner = (o) => window.peaBanner && window.peaBanner(o);
const store = {
  get(k, d = null) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } },
};
const rootPath = () => { const q = $('#q'); return (q && q.dataset.root) || ''; };
const swUrl = new URL(rootPath() + 'sw.js', location.href);
const scope = new URL(rootPath() || './', location.href).pathname;
let reg = null;

navigator.serviceWorker.register(swUrl.href, { scope, updateViaCache: 'none' }).then((r) => {
  reg = r;
  paintOffline();
  r.addEventListener('updatefound', () => {
    const nw = r.installing;
    if (!nw) return;
    nw.addEventListener('statechange', () => {
      if (nw.state === 'installed' && navigator.serviceWorker.controller) {
        banner({ id: 'update', text: 'Une nouvelle version du site est disponible.', action: 'Actualiser', ttl: 0, onAction: () => { nw.postMessage({ type: 'SKIP_WAITING' }); } });
      }
    });
  });
}).catch(() => { /* enregistrement impossible : le site fonctionne en ligne */ });

/* Un service worker qui prend la main pour la première fois n'a rien changé à ce qui est affiché :
   recharger n'aurait servi qu'à faire clignoter la page. On ne recharge que sur un vrai remplacement. */
const avaitUnControleur = !!navigator.serviceWorker.controller;
// dès qu'un service worker contrôle l'onglet, il enregistre la page où l'on se trouve
navigator.serviceWorker.ready.then(() => {
  const envoyer = () => { if (navigator.serviceWorker.controller) navigator.serviceWorker.controller.postMessage({ type: 'CACHE_PAGE', url: location.href }); };
  if (navigator.serviceWorker.controller) envoyer();
  else navigator.serviceWorker.addEventListener('controllerchange', envoyer, { once: true });
});
let reloading = false;
navigator.serviceWorker.addEventListener('controllerchange', () => {
  if (!avaitUnControleur || reloading) return;
  reloading = true;
  if (store.get('offlineAll')) store.set('offlineStale', true);
  location.reload();
});

/* ---------- pré-chargement complet ---------- */
const btn = $('#offlineBtn');
const state = $('#offlineState');
function paintOffline() {
  if (!btn) return;
  btn.hidden = false;
  const all = store.get('offlineAll');
  if (all) { state.textContent = 'session enregistrée le ' + new Date(all).toLocaleDateString('fr-FR'); btn.textContent = 'Mettre à jour la copie'; }
  else { state.textContent = 'pages consultées seulement'; btn.textContent = 'Rendre disponible hors ligne'; }
}
if (btn) {
  btn.addEventListener('click', () => {
    if (!navigator.serviceWorker.controller) { banner({ text: 'Rechargez la page une fois, puis réessayez.', ttl: 5000 }); return; }
    if (!navigator.onLine) { banner({ text: 'Connectez-vous à Internet pour enregistrer la session.', ttl: 5000 }); return; }
    btn.disabled = true;
    state.textContent = 'téléchargement…';
    navigator.serviceWorker.controller.postMessage({ type: 'PRECACHE_ALL' });
  });
  navigator.serviceWorker.addEventListener('message', (e) => {
    const d = e.data || {};
    if (d.type === 'PRECACHE_PROGRESS') state.textContent = `téléchargement ${d.done} / ${d.total}`;
    if (d.type === 'PRECACHE_DONE') { store.set('offlineAll', Date.now()); store.set('offlineStale', false); btn.disabled = false; paintOffline(); banner({ text: 'La session complète est disponible hors ligne sur cet appareil.', ttl: 6000 }); }
  });
}
if (store.get('offlineStale')) {
  banner({ id: 'stale', text: 'Le site a été mis à jour : votre copie hors ligne est à rafraîchir.', action: 'Mettre à jour', ttl: 0, onAction: () => { btn && btn.click(); } });
}

/* ---------- réseau ---------- */
window.addEventListener('offline', () => banner({ id: 'offline', text: 'Vous êtes hors ligne : les pages déjà consultées restent disponibles.', ttl: 6000 }));
window.addEventListener('online', () => banner({ id: 'online', text: 'Connexion rétablie.', ttl: 3000 }));

/* ---------- navigateur intégré (Facebook, Instagram, Messenger) ---------- */
const ua = navigator.userAgent || '';
if (/FBAN|FBAV|Instagram|Messenger/i.test(ua) && !sessionStorage.getItem('inappSeen')) {
  try { sessionStorage.setItem('inappSeen', '1'); } catch { /* ignore */ }
  banner({ id: 'inapp', text: 'Pour garder le site hors ligne, ouvrez-le dans Chrome (menu ⋯ › Ouvrir dans le navigateur).', ttl: 12000 });
}
