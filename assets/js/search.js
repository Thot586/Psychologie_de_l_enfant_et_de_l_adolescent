/* search.js — recherche plein texte sur tout le site (index JSON chargé à la première recherche),
   repli sur la page courante si l'index est indisponible. */
const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
const q = $('#q');
const box = $('#search');
const results = $('#results');
const clr = $('#qclr');
const ROOT = q.dataset.root || '';
const norm = (s) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[’']/g, "'");
let index = null;
let loading = null;
let hits = [];
let active = -1;

async function ensureIndex() {
  if (index) return index;
  if (!loading) {
    loading = fetch(q.dataset.index).then((r) => (r.ok ? r.json() : Promise.reject(r.status))).then((data) => {
      // index groupé par page puis section : on l'aplatit en blocs { p, t, s, sh, x, n }
      index = data.flatMap((pg) => pg.secs.flatMap((sec) => sec.x.map((x) => ({ p: pg.p, t: pg.t, s: sec.s, sh: sec.sh, x, n: norm(x + ' ' + pg.t + ' ' + (sec.sh || '')) }))));
      return index;
    }).catch(() => {
      index = $$('main p, main li, main td, main h2, main h3, main h4').map((el) => {
        const sec = el.closest('section') && el.closest('section').querySelector('h2');
        return { p: location.pathname.split('/').slice(-2).join('/'), t: document.title.split(' · ')[0], s: el.id || (el.closest('[id]') && el.closest('[id]').id) || '', sh: sec ? sec.textContent : '', x: el.textContent.trim(), n: norm(el.textContent), local: true };
      });
      window.peaBanner && window.peaBanner({ id: 'searchlocal', text: 'Index de recherche indisponible hors ligne : recherche limitée à cette page.', ttl: 5000 });
      return index;
    });
  }
  return loading;
}
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function snippet(item, words) {
  const t = item.x; const n = norm(t);
  let pos = -1;
  for (const w of words) { const p = n.indexOf(w); if (p >= 0 && (pos < 0 || p < pos)) pos = p; }
  const start = Math.max(0, pos - 70); const end = Math.min(t.length, pos + 110);
  let s = esc((start > 0 ? '… ' : '') + t.slice(start, end) + (end < t.length ? ' …' : ''));
  words.forEach((w) => { if (w.length < 2) return; const re = new RegExp('(' + w.split('').map((ch) => ({ a: '[aàáâä]', e: '[eèéêë]', i: '[iìíîï]', o: '[oòóôö]', u: '[uùúûü]', c: '[cç]', "'": "['’]" }[ch] || ch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))).join('') + ')', 'gi'); s = s.replace(re, '<mark>$1</mark>'); });
  return s;
}
function close() { results.classList.remove('open'); active = -1; }
function pageHref(item) { return (item.local ? '' : ROOT) + item.p + (item.s ? '#' + item.s : ''); }
async function run() {
  const raw = q.value.trim();
  box.classList.toggle('has', raw.length > 0);
  if (raw.length < 2) { close(); return; }
  await ensureIndex();
  const words = norm(raw).split(/\s+/).filter(Boolean);
  const scored = [];
  for (const it of index) {
    if (!words.every((w) => it.n.includes(w))) continue;
    let score = 0;
    words.forEach((w) => { if (norm(it.t).includes(w)) score += 3; if (it.sh && norm(it.sh).includes(w)) score += 2; score += 1; });
    scored.push([score, it]);
  }
  scored.sort((a, b) => b[0] - a[0]);
  hits = scored.slice(0, 40).map((x) => x[1]);
  active = -1;
  if (!hits.length) { results.innerHTML = `<div class="empty">Aucun résultat pour « ${esc(raw)} ». Essayez un autre mot : un nom d'auteur, un chiffre, un terme du glossaire.</div>`; results.classList.add('open'); return; }
  let html = `<div class="rh">${hits.length} résultat${hits.length > 1 ? 's' : ''}${scored.length > 40 ? ' (40 premiers affichés)' : ''}</div>`;
  hits.forEach((it, i) => { html += `<a class="r" role="option" href="${esc(pageHref(it))}" data-i="${i}"><span class="sec">${esc(it.t)}${it.sh ? ' › ' + esc(it.sh) : ''}</span><span class="sn">${snippet(it, words)}</span></a>`; });
  results.innerHTML = html;
  results.classList.add('open');
}
let t;
q.addEventListener('input', () => { clearTimeout(t); t = setTimeout(run, 140); });
q.addEventListener('focus', () => { if (q.value.trim().length >= 2) run(); });
q.addEventListener('keydown', (e) => {
  const items = $$('.r', results);
  if (e.key === 'ArrowDown' && items.length) { e.preventDefault(); active = Math.min(items.length - 1, active + 1); items[active].focus(); }
  else if (e.key === 'Enter' && items.length) { e.preventDefault(); items[Math.max(0, active)].click(); }
  else if (e.key === 'Escape') { if (q.value) { q.value = ''; box.classList.remove('has'); } close(); q.blur(); }
});
results.addEventListener('keydown', (e) => {
  const items = $$('.r', results); const cur = items.indexOf(document.activeElement);
  if (e.key === 'ArrowDown') { e.preventDefault(); (items[cur + 1] || items[0]).focus(); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); if (cur <= 0) q.focus(); else items[cur - 1].focus(); }
  else if (e.key === 'Escape') { close(); q.focus(); }
});
results.addEventListener('click', () => setTimeout(close, 50));
clr.addEventListener('click', () => { q.value = ''; box.classList.remove('has'); close(); q.focus(); });
document.addEventListener('click', (e) => { if (!e.target.closest('#search')) close(); });
if (q.value.trim().length >= 2) run();
