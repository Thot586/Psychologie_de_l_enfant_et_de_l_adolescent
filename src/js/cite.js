/* cite.js — popover de citation (référence complète, source, bibliographie) ; feuille basse sur petit écran. */
const $ = (s, c = document) => c.querySelector(s);
const island = $('#refs-data');
const DATA = island ? JSON.parse(island.textContent || '{}') : {};
const pop = $('#pop');
const sheet = $('#sheet');
const scrim = $('#scrim');
const rootPath = () => { const q = $('#q'); return (q && q.dataset.root) || ''; };
let target = null;
let sheetPushed = false;

function closePop() { if (pop) pop.classList.remove('open'); target = null; }
function openSheet(key, el) {
  const r = DATA[key];
  $('#sheetKind').textContent = 'Référence';
  const body = $('#sheetBody'); const foot = $('#sheetFoot');
  body.innerHTML = ''; foot.innerHTML = '';
  const h = document.createElement('h2'); h.id = 'sheetTitle'; h.textContent = r.short; body.appendChild(h);
  const p = document.createElement('p'); p.innerHTML = r.apa; body.appendChild(p);
  if (r.url) { const a = document.createElement('a'); a.href = r.url; a.target = '_blank'; a.rel = 'noopener'; a.textContent = 'Ouvrir la source'; foot.appendChild(a); }
  const b = document.createElement('a'); b.href = rootPath() + 'references.html#ref-' + key; b.textContent = 'Voir dans la bibliographie';
  b.addEventListener('click', () => window.peaRemember && window.peaRemember({ ref: key }));
  foot.appendChild(b);
  sheet.classList.add('open'); scrim && scrim.classList.add('open');
  document.body.style.overflow = 'hidden';
  if (!sheetPushed) { history.pushState({ pea: 'sheet' }, ''); sheetPushed = true; }
  const close = (fromPop) => {
    sheet.classList.remove('open'); scrim && scrim.classList.remove('open'); document.body.style.overflow = '';
    if (sheetPushed && !fromPop) history.back();
    sheetPushed = false;
    el.focus({ preventScroll: true });
    $('#sheetx').removeEventListener('click', onX);
    window.removeEventListener('popstate', onPop);
    document.removeEventListener('pea:scrim', onX);
  };
  const onX = () => close(false);
  const onPop = () => { if (sheet.classList.contains('open')) { sheetPushed = false; close(true); } };
  $('#sheetx').addEventListener('click', onX);
  window.addEventListener('popstate', onPop);
  document.addEventListener('pea:scrim', onX);
  setTimeout(() => sheet.focus(), 50);
}
function openPop(el) {
  const key = el.dataset.ref;
  const r = DATA[key];
  if (!r) return;
  if (window.innerWidth < 480 && sheet) { openSheet(key, el); return; }
  $('#popb').innerHTML = r.apa;
  const src = $('#popsrc');
  if (r.url) { src.style.display = ''; src.href = r.url; } else { src.style.display = 'none'; }
  const bib = $('#popbib');
  bib.href = rootPath() + 'references.html#ref-' + key;
  bib.onclick = () => window.peaRemember && window.peaRemember({ ref: key });
  pop.classList.add('open');
  target = el;
  const rect = el.getBoundingClientRect();
  const pw = pop.offsetWidth; const ph = pop.offsetHeight;
  let left = rect.left + window.scrollX;
  const maxLeft = window.scrollX + document.documentElement.clientWidth - pw - 12;
  if (left > maxLeft) left = Math.max(12, maxLeft);
  let top = rect.bottom + window.scrollY + 8;
  if (rect.bottom + ph + 16 > window.innerHeight && rect.top - ph - 8 > 60) top = rect.top + window.scrollY - ph - 8;
  pop.style.left = left + 'px'; pop.style.top = top + 'px';
  $('#popx').focus({ preventScroll: true });
}
document.addEventListener('click', (e) => {
  const c = e.target.closest('a.cite');
  if (c && DATA[c.dataset.ref]) { e.preventDefault(); if (target === c) closePop(); else openPop(c); return; }
  if (pop && pop.classList.contains('open') && !e.target.closest('#pop')) closePop();
});
$('#popx') && $('#popx').addEventListener('click', () => { const t = target; closePop(); t && t.focus(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && pop && pop.classList.contains('open')) { const t = target; closePop(); t && t.focus(); } });
window.addEventListener('resize', closePop);
