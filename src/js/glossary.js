/* glossary.js — infobulle au survol / au tap, panneau (feuille basse) avec la définition complète,
   sans jamais perdre la position de lecture. */
const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
const island = $('#gloss-data');
const DATA = island ? JSON.parse(island.textContent || '{}') : {};
const sheet = $('#sheet');
const scrim = $('#scrim');
const coarse = matchMedia('(pointer: coarse)').matches;
let tip = null;
let tipFor = null;
let sheetOpener = null;
let sheetPushed = false;

/* ---------- infobulle ---------- */
function hideTip() { if (tip) { tip.remove(); tip = null; } if (tipFor) { tipFor.classList.remove('is-open'); tipFor.removeAttribute('aria-describedby'); tipFor = null; } }
function showTip(el) {
  hideTip();
  const def = el.dataset.def;
  if (!def) return;
  tip = document.createElement('div');
  tip.className = 'tip'; tip.id = 'tip'; tip.setAttribute('role', 'tooltip');
  const t = document.createElement('span'); t.className = 'tt'; t.textContent = (DATA[el.dataset.term] && DATA[el.dataset.term].terme) || el.textContent;
  const d = document.createElement('span'); d.textContent = def;
  const a = document.createElement('span'); a.className = 'ta';
  const link = document.createElement('a'); link.href = el.getAttribute('href'); link.textContent = 'Définition complète →';
  link.addEventListener('click', (e) => { e.preventDefault(); openSheet(el); });
  a.appendChild(link);
  tip.append(t, d, a);
  document.body.appendChild(tip);
  el.setAttribute('aria-describedby', 'tip');
  el.classList.add('is-open');
  tipFor = el;
  const r = el.getBoundingClientRect();
  const w = tip.offsetWidth; const h = tip.offsetHeight;
  let left = r.left + window.scrollX;
  const maxLeft = window.scrollX + document.documentElement.clientWidth - w - 8;
  if (left > maxLeft) left = Math.max(8, maxLeft);
  const above = r.bottom + h + 12 > window.innerHeight && r.top - h - 8 > 60;
  tip.style.left = left + 'px';
  tip.style.top = (above ? r.top + window.scrollY - h - 6 : r.bottom + window.scrollY + 6) + 'px';
}

/* ---------- panneau ---------- */
function renderEntry(id) {
  const g = DATA[id];
  const body = $('#sheetBody');
  const foot = $('#sheetFoot');
  body.innerHTML = '';
  foot.innerHTML = '';
  const h = document.createElement('h2'); h.id = 'sheetTitle'; h.textContent = g.terme;
  body.appendChild(h);
  if (g.categorie) { const c = document.createElement('p'); c.className = 'small muted'; c.textContent = g.categorie; body.appendChild(c); }
  const s = document.createElement('p'); s.className = 'short'; s.style.fontWeight = '600'; s.textContent = g.court; body.appendChild(s);
  if (g.long) { const l = document.createElement('div'); l.innerHTML = g.long; body.appendChild(l); }
  if (g.source && (g.source.citation || g.source.texte)) {
    const src = document.createElement('p'); src.className = 'src';
    src.textContent = 'Source : ' + (g.source.citation || g.source.texte);
    if (g.source.refId) { const a = document.createElement('a'); a.href = rootPath() + 'references.html#ref-' + g.source.refId; a.textContent = ' (voir la référence)'; a.addEventListener('click', () => window.peaRemember && window.peaRemember({ term: id })); src.appendChild(a); }
    body.appendChild(src);
  }
  if (g.voirAussi && g.voirAussi.length) {
    const p = document.createElement('p'); p.className = 'small'; p.textContent = 'Voir aussi : ';
    g.voirAussi.forEach((v, i) => {
      if (!DATA[v]) return;
      const b = document.createElement('a'); b.href = '#'; b.textContent = DATA[v].terme;
      b.addEventListener('click', (e) => { e.preventDefault(); renderEntry(v); });
      if (i) p.appendChild(document.createTextNode(', '));
      p.appendChild(b);
    });
    body.appendChild(p);
  }
  (g.liens || []).forEach((l) => { const a = document.createElement('a'); a.href = l.url; a.target = '_blank'; a.rel = 'noopener'; a.textContent = l.label; foot.appendChild(a); });
  const full = document.createElement('a'); full.href = rootPath() + 'glossaire.html#' + id; full.textContent = 'Ouvrir la page glossaire';
  full.addEventListener('click', () => window.peaRemember && window.peaRemember({ term: id }));
  foot.appendChild(full);
}
function rootPath() { const q = $('#q'); return (q && q.dataset.root) || ''; }
function openSheet(el) {
  const id = el.dataset.term;
  if (!DATA[id] || !sheet) { window.peaRemember && window.peaRemember({ term: id }); location.href = el.getAttribute('href'); return; }
  hideTip();
  sheetOpener = el;
  $('#sheetKind').textContent = 'Glossaire';
  renderEntry(id);
  sheet.classList.add('open');
  scrim && scrim.classList.add('open');
  if (!sheetPushed) { history.pushState({ pea: 'sheet' }, ''); sheetPushed = true; }
  document.body.style.overflow = 'hidden';
  setTimeout(() => sheet.focus(), 50);
}
export function closeSheet(fromPop) {
  if (!sheet || !sheet.classList.contains('open')) return;
  sheet.classList.remove('open');
  scrim && scrim.classList.remove('open');
  document.body.style.overflow = '';
  if (sheetPushed && !fromPop) history.back();
  sheetPushed = false;
  if (sheetOpener) { sheetOpener.classList.add('flash'); sheetOpener.focus({ preventScroll: true }); setTimeout(() => sheetOpener && sheetOpener.classList.remove('flash'), 1300); }
  sheetOpener = null;
}
window.peaCloseSheet = closeSheet;
if (sheet) {
  $('#sheetx').addEventListener('click', () => closeSheet());
  window.addEventListener('popstate', () => { if (sheet.classList.contains('open')) { sheetPushed = false; closeSheet(true); } });
  document.addEventListener('pea:scrim', () => closeSheet());
  sheet.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { e.preventDefault(); closeSheet(); }
    if (e.key === 'Tab') {
      const f = $$('a, button, [tabindex="0"]', sheet).filter((x) => !x.hidden);
      if (!f.length) return;
      const first = f[0]; const last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); } else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });
  let y0 = null;
  sheet.addEventListener('touchstart', (e) => { y0 = e.touches[0].clientY; }, { passive: true });
  sheet.addEventListener('touchend', (e) => { if (y0 !== null && e.changedTouches[0].clientY - y0 > 90 && $('#sheetBody').scrollTop === 0) closeSheet(); y0 = null; }, { passive: true });
}

/* ---------- événements sur les termes ---------- */
document.addEventListener('mouseover', (e) => { if (coarse) return; const el = e.target.closest('a.term'); if (el && el !== tipFor) showTip(el); });
document.addEventListener('mouseout', (e) => { if (coarse) return; const el = e.target.closest('a.term'); if (el && !(e.relatedTarget && (e.relatedTarget.closest('#tip') || e.relatedTarget === el))) setTimeout(() => { if (tip && !tip.matches(':hover') && tipFor === el && !el.matches(':hover')) hideTip(); }, 120); });
document.addEventListener('focusin', (e) => { const el = e.target.closest('a.term'); if (el) showTip(el); else if (!e.target.closest('#tip')) hideTip(); });
document.addEventListener('click', (e) => {
  const el = e.target.closest('a.term');
  if (el) {
    e.preventDefault();
    if (coarse) { if (tipFor === el) openSheet(el); else showTip(el); } else { openSheet(el); }
    return;
  }
  if (!e.target.closest('#tip')) hideTip();
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') hideTip(); if (e.key === 'Enter' && e.target.matches('a.term')) { e.preventDefault(); openSheet(e.target); } });
window.addEventListener('scroll', () => { if (tip && coarse) hideTip(); }, { passive: true });
window.addEventListener('resize', hideTip);
