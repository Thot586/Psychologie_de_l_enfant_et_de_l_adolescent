/* app.js — noyau : thème, réglages, tiroir, progression, en-tête, bandeaux, chargement conditionnel des modules.
   Aucune dépendance. Tout le contenu reste lisible sans ce script. */
const root = document.documentElement;
const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
const store = {
  get(k, d = null) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* stockage indisponible */ } },
  del(k) { try { localStorage.removeItem(k); } catch { /* ignore */ } },
};
const sstore = {
  get(k, d = null) { try { const v = sessionStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { sessionStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } },
};
const ROOT = ($('#q') && $('#q').dataset.root) || '';
const PAGE = root.dataset.page || '';
const SESSION = root.dataset.session || '';
const TYPE = root.dataset.type || '';
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ---------- bandeaux : un seul à la fois, file d'attente ---------- */
const bannerQueue = [];
let bannerBusy = false;
function showBanner({ text, action, onAction, ttl = 9000, id }) {
  if (id && bannerQueue.some((b) => b.id === id)) return;
  bannerQueue.push({ text, action, onAction, ttl, id });
  pumpBanner();
}
function pumpBanner() {
  if (bannerBusy || !bannerQueue.length) return;
  const b = bannerQueue.shift();
  const el = $('#banner');
  if (!el) return;
  bannerBusy = true;
  el.innerHTML = '';
  const span = document.createElement('span');
  span.textContent = b.text;
  el.appendChild(span);
  if (b.action) {
    const btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'btn'; btn.textContent = b.action;
    btn.addEventListener('click', () => { hide(); b.onAction && b.onAction(); });
    el.appendChild(btn);
  }
  const x = document.createElement('button');
  x.type = 'button'; x.className = 'x'; x.setAttribute('aria-label', 'Fermer'); x.textContent = '×';
  x.addEventListener('click', hide);
  el.appendChild(x);
  el.classList.add('show');
  $('#bottombar') && $('#bottombar').classList.add('is-hidden');
  const t = b.ttl ? setTimeout(hide, b.ttl) : null;
  function hide() {
    if (t) clearTimeout(t);
    el.classList.remove('show');
    $('#bottombar') && $('#bottombar').classList.remove('is-hidden');
    setTimeout(() => { bannerBusy = false; pumpBanner(); }, 300);
  }
}
window.peaBanner = showBanner;

/* ---------- thème ---------- */
const themeBtn = $('#themeBtn');
const currentTheme = () => root.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
if (themeBtn) {
  themeBtn.addEventListener('click', () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    store.set('theme', next);
    themeBtn.setAttribute('aria-label', next === 'dark' ? 'Passer en mode clair' : 'Passer en mode sombre');
  });
}

/* ---------- réglages ---------- */
const settings = $('#settings');
const settingsBtn = $('#settingsBtn');
function closeSettings() { if (settings) { settings.classList.remove('open'); settingsBtn.setAttribute('aria-expanded', 'false'); } }
if (settings && settingsBtn) {
  settingsBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const open = settings.classList.toggle('open');
    settingsBtn.setAttribute('aria-expanded', String(open));
    if (open) $('button', settings).focus();
  });
  document.addEventListener('click', (e) => { if (settings.classList.contains('open') && !e.target.closest('#settings') && !e.target.closest('#settingsBtn')) closeSettings(); });
  const paint = () => {
    $$('[data-fs]', settings).forEach((b) => b.setAttribute('aria-pressed', String((root.dataset.fs || '') === b.dataset.fs)));
    $$('[data-reading]', settings).forEach((b) => b.setAttribute('aria-pressed', String((root.dataset.reading || 'complete') === b.dataset.reading)));
  };
  paint();
  $$('[data-fs]', settings).forEach((b) => b.addEventListener('click', () => {
    if (b.dataset.fs) { root.dataset.fs = b.dataset.fs; store.set('fs', b.dataset.fs); } else { delete root.dataset.fs; store.del('fs'); }
    paint();
  }));
  $$('[data-reading]', settings).forEach((b) => b.addEventListener('click', () => {
    if (b.dataset.reading === 'essentiel') { root.dataset.reading = 'essentiel'; store.set('reading', 'essentiel'); } else { delete root.dataset.reading; store.del('reading'); }
    paint();
    showBanner({ id: 'reading', text: b.dataset.reading === 'essentiel' ? 'Lecture Essentiel : les encadrés Approfondir sont masqués sur tout le site.' : 'Lecture Complète : encadrés Approfondir affichés.', ttl: 4000 });
  }));
}
async function clearAllData() {
  try { localStorage.clear(); } catch { /* ignore */ }
  try { sessionStorage.clear(); } catch { /* ignore */ }
  if ('caches' in window) { try { const keys = await caches.keys(); await Promise.all(keys.map((k) => caches.delete(k))); } catch { /* ignore */ } }
  delete root.dataset.theme; delete root.dataset.fs; delete root.dataset.reading;
  paintProgress();
  showBanner({ text: 'Vos données sur cet appareil ont été effacées (progression, réglages, copie hors ligne).', ttl: 6000 });
}
$$('#clearData, [data-clear-data]').forEach((b) => b.addEventListener('click', () => { if (confirm('Effacer la progression, les réglages et la copie hors ligne enregistrés sur cet appareil ?')) clearAllData(); }));

/* ---------- tiroir (rail) ---------- */
const rail = $('#rail');
const scrim = $('#scrim');
const menuBtn = $('#menuBtn');
let railPushed = false;
function openRail() {
  if (!rail) return;
  rail.classList.add('open'); scrim && scrim.classList.add('open');
  menuBtn && menuBtn.setAttribute('aria-expanded', 'true');
  if (!railPushed) { history.pushState({ pea: 'rail' }, ''); railPushed = true; }
  const cur = $('.rail a.cur', rail) || $('a', rail);
  cur && cur.focus({ preventScroll: true });
}
function closeRail(fromPop) {
  if (!rail || !rail.classList.contains('open')) return;
  rail.classList.remove('open'); scrim && scrim.classList.remove('open');
  menuBtn && menuBtn.setAttribute('aria-expanded', 'false');
  if (railPushed && !fromPop) history.back();
  railPushed = false;
  menuBtn && menuBtn.focus({ preventScroll: true });
}
menuBtn && menuBtn.addEventListener('click', () => (rail.classList.contains('open') ? closeRail() : openRail()));
$('#bbMenu') && $('#bbMenu').addEventListener('click', () => (rail && rail.classList.contains('open') ? closeRail() : openRail()));
scrim && scrim.addEventListener('click', () => { closeRail(); document.dispatchEvent(new CustomEvent('pea:scrim')); });
window.addEventListener('popstate', () => { if (rail && rail.classList.contains('open')) { railPushed = false; closeRail(true); } });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { closeRail(); closeSettings(); } });

/* ---------- progression ---------- */
const VISITED_KEY = 'visited:' + SESSION;
function paintProgress() {
  if (!SESSION) return;
  const visited = new Set(store.get(VISITED_KEY, []));
  const links = $$('.rail a.mod, .toc-step a[data-page]');
  let n = 0;
  links.forEach((a) => {
    const done = visited.has(a.dataset.page) && !a.classList.contains('cur');
    a.classList.toggle('done', done);
  });
  $$('.rail a.mod').forEach((a) => { if (visited.has(a.dataset.page)) n += 1; });
  const total = $$('.rail a.mod').length;
  const fill = $('#pfill');
  if (fill && total) fill.style.width = Math.round((n / total) * 100) + '%';
  const pd = $('#pdone');
  if (pd) pd.textContent = n + (n > 1 ? ' modules consultés' : ' module consulté') + (total ? ' sur ' + total : '');
}
if (SESSION && TYPE === 'module') {
  const visited = new Set(store.get(VISITED_KEY, []));
  const out = SESSION + '/' + PAGE + '.html';
  if (!visited.has(out)) { visited.add(out); store.set(VISITED_KEY, Array.from(visited)); }
}
paintProgress();
if (TYPE === 'module' || TYPE === 'page' || TYPE === 'session-index') {
  const save = () => store.set('last', { url: location.pathname + location.hash, title: document.title.split(' · ')[0], y: window.scrollY, at: Date.now() });
  window.addEventListener('pagehide', save);
  let t; window.addEventListener('scroll', () => { clearTimeout(t); t = setTimeout(save, 800); }, { passive: true });
}
const resume = $('[data-resume]');
if (resume) {
  const last = store.get('last');
  if (last && last.url) {
    const a = document.createElement('a');
    a.href = last.url; a.textContent = last.title || 'votre dernière page';
    resume.hidden = false;
    resume.querySelector('span').replaceWith(a);
  }
}

/* ---------- en-tête et barre basse masqués au défilement ; retour en haut ; TOC active ---------- */
const top = $('#top');
const bottombar = $('#bottombar');
const totop = $('#totop');
let lastY = window.scrollY;
let ticking = false;
window.addEventListener('scroll', () => {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => {
    const y = window.scrollY;
    const mobile = window.innerWidth < 1024;
    if (mobile && Math.abs(y - lastY) > 12) {
      const down = y > lastY && y > 80;
      top && top.classList.toggle('is-hidden', down && !$('.results.open'));
      bottombar && !$('.banner.show') && bottombar.classList.toggle('is-hidden', down);
      lastY = y;
    } else if (!mobile) {
      top && top.classList.remove('is-hidden');
    }
    totop && totop.classList.toggle('show', y > 700);
    ticking = false;
  });
}, { passive: true });
const toTop = () => window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' });
totop && totop.addEventListener('click', toTop);
$('#bbTop') && $('#bbTop').addEventListener('click', toTop);

const tocLinks = $$('.rail-toc a');
if (tocLinks.length && 'IntersectionObserver' in window) {
  const map = new Map(tocLinks.map((a) => [a.getAttribute('href').slice(1), a]));
  const heads = Array.from(map.keys()).map((id) => document.getElementById(id)).filter(Boolean);
  let active = null;
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => { if (en.isIntersecting) { active && active.classList.remove('active'); active = map.get(en.target.id); active && active.classList.add('active'); } });
  }, { rootMargin: '-56px 0px -70% 0px', threshold: 0 });
  heads.forEach((h) => io.observe(h));
}

/* ---------- surlignage de l'ancre visée ---------- */
function flashHash() {
  const id = decodeURIComponent(location.hash.slice(1));
  if (!id) return;
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('flash-anchor'); void el.offsetWidth; el.classList.add('flash-anchor');
  setTimeout(() => el.classList.remove('flash-anchor'), 2200);
}
window.addEventListener('hashchange', flashHash);
if (location.hash) setTimeout(flashHash, 200);

/* ---------- retour à la lecture (pages glossaire et bibliographie) ---------- */
const backbar = $('#backbar');
if (backbar) {
  const params = new URLSearchParams(location.search);
  const ret = sstore.get('readingReturn');
  const from = params.get('de') || (ret && ret.url);
  if (from) {
    const a = $('#backlink');
    a.href = from;
    a.textContent = '← Retour à votre lecture' + (ret && ret.title ? ' : ' + ret.title : '');
    backbar.hidden = false;
    a.addEventListener('click', (e) => {
      if (ret && ret.url && (ret.url === from || from.indexOf(ret.url.split('#')[0]) >= 0)) {
        e.preventDefault();
        sstore.set('readingRestore', { y: ret.y, term: ret.term, ref: ret.ref });
        location.href = ret.url;
      }
    });
    $('#backx').addEventListener('click', () => { backbar.hidden = true; });
  }
}
const restore = sstore.get('readingRestore');
if (restore) {
  try { sessionStorage.removeItem('readingRestore'); } catch { /* ignore */ }
  window.addEventListener('load', () => {
    if (typeof restore.y === 'number') window.scrollTo({ top: restore.y, behavior: 'auto' });
    const sel = restore.term ? `a.term[data-term="${restore.term}"]` : restore.ref ? `a.cite[data-ref="${restore.ref}"]` : null;
    const el = sel && $(sel);
    if (el) { el.classList.add('flash'); el.focus({ preventScroll: true }); setTimeout(() => el.classList.remove('flash'), 1400); }
  });
}
window.peaRemember = (extra) => sstore.set('readingReturn', { url: location.pathname + location.hash, title: document.title.split(' · ')[0], y: window.scrollY, ...extra });

/* ---------- lettre active du glossaire ---------- */
const glnav = $('.gl-nav');
if (glnav && 'IntersectionObserver' in window) {
  const letters = $$('.gl-letter');
  const links = new Map($$('a', glnav).map((a) => [a.getAttribute('href').slice(1), a]));
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => { if (en.isIntersecting) { $$('a.active', glnav).forEach((a) => a.classList.remove('active')); const l = links.get(en.target.id); l && l.classList.add('active'); } });
  }, { rootMargin: '-56px 0px -80% 0px' });
  letters.forEach((h) => io.observe(h));
}

/* ---------- filtre de la bibliographie ---------- */
const reflist = $('#reflist');
if (reflist) {
  const items = $$('li', reflist);
  let type = '';
  let q = '';
  const norm = (s) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const apply = () => { items.forEach((li) => { li.hidden = (type && li.dataset.type !== type) || (q && !li.dataset.search.includes(q)); }); };
  $$('[data-ref-filter] .chip').forEach((b) => b.addEventListener('click', () => { type = b.dataset.type; $$('[data-ref-filter] .chip').forEach((c) => c.setAttribute('aria-pressed', String(c === b))); apply(); }));
  const rq = $('#refq');
  rq && rq.addEventListener('input', () => { q = norm(rq.value.trim()); apply(); });
}

/* ---------- chargement conditionnel ---------- */
const script = $('script[src*="app.js"]');
const V = script ? (script.src.split('v=')[1] || '') : '';
const imp = (name) => import(`./${name}.js${V ? '?v=' + V : ''}`).catch((e) => console.warn('module ' + name, e));
if ($('a.term') || $('#gloss-data')) imp('glossary');
if ($('a.cite')) imp('cite');
if ($('.qz')) imp('quiz');
if ($('.wiz[data-start]')) imp('wizard');
if ($('[data-sort], [data-sim], [data-compare], [data-radar], [data-engagement], .agebar')) imp('interactives');
const q = $('#q');
if (q) {
  let loaded = false;
  const go = () => { if (!loaded) { loaded = true; imp('search'); } };
  q.addEventListener('focus', go, { once: true });
  q.addEventListener('input', go, { once: true });
  document.addEventListener('keydown', (e) => { if (e.key === '/' && !e.target.closest('input, textarea')) { e.preventDefault(); q.focus(); } });
}
if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) imp('pwa');
