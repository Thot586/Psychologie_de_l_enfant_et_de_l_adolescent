/* interactives.js — tri des situations, simulateur d'entretien, barre d'âges, engagement, radar. */
const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
const store = {
  get(k, d = null) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } },
};

/* ---------- tri des situations ---------- */
$$('[data-sort]').forEach((box) => {
  $$('.item', box).forEach((item) => {
    const a = Number(item.dataset.a);
    const btns = $$('.opts button', item);
    btns.forEach((b) => b.addEventListener('click', () => {
      btns.forEach((x) => { x.disabled = true; });
      btns[a].classList.add('ok');
      if (Number(b.dataset.i) !== a) b.classList.add('ko');
      $$('.segs div', item).forEach((d, i) => setTimeout(() => d.classList.add(d.dataset.on === 'true' ? 'on' : 'off'), 120 * i));
      $('.why', item).classList.add('show');
    }));
  });
});

/* ---------- simulateur d'entretien ---------- */
$$('[data-sim]').forEach((sim) => {
  const turns = $$('.wnode[data-turn]', sim);
  const reset = $('[data-sim-reset]', sim);
  let i = 0;
  let good = 0;
  sim.classList.add('js');
  function show(n) {
    turns.forEach((t) => t.classList.remove('cur'));
    const t = turns[n];
    if (!t) return;
    t.classList.add('cur');
    if (t.dataset.turn === 'end') {
      const out = $('.wout', t);
      const total = turns.length - 1;
      out.innerHTML = `<b>Bilan : ${good} réponse${good > 1 ? 's' : ''} qui ouvrent la parole sur ${total}.</b> ` + out.dataset.text;
    }
    reset.hidden = n === 0;
  }
  turns.forEach((t, n) => {
    if (t.dataset.turn === 'end') { const out = $('.wout', t); out.dataset.text = out.innerHTML; return; }
    $$('button[data-c]', t).forEach((b) => b.addEventListener('click', () => {
      $$('button[data-c]', t).forEach((x) => { x.disabled = true; });
      const r = $(`[data-r="${b.dataset.c}"]`, t);
      r.hidden = false;
      if (b.dataset.good === 'true') { good += 1; b.classList.add('ok'); } else { b.classList.add('ko'); }
      const next = document.createElement('button'); next.type = 'button'; next.className = 'btn s'; next.textContent = n + 1 < turns.length - 1 ? 'Tour suivant →' : 'Voir le bilan →';
      next.style.marginTop = '8px';
      next.addEventListener('click', () => { i = n + 1; show(i); });
      r.appendChild(next);
      next.focus({ preventScroll: true });
    }));
  });
  reset.addEventListener('click', () => {
    i = 0; good = 0;
    turns.forEach((t) => { $$('button[data-c]', t).forEach((x) => { x.disabled = false; x.classList.remove('ok', 'ko'); }); $$('[data-r]', t).forEach((r) => { r.hidden = true; const n = $('.btn', r); n && n.remove(); }); });
    show(0);
  });
  show(0);
});

/* ---------- barre d'âges : ancre active ---------- */
const agebar = $('.agebar');
if (agebar && 'IntersectionObserver' in window) {
  const links = $$('a', agebar);
  const map = new Map(links.map((a) => [a.getAttribute('href').slice(1), a]));
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => { if (en.isIntersecting) { links.forEach((l) => l.classList.remove('active')); const l = map.get(en.target.id); l && l.classList.add('active'); } });
  }, { rootMargin: '-120px 0px -60% 0px' });
  map.forEach((_, id) => { const el = document.getElementById(id); el && io.observe(el); });
}

/* ---------- engagement personnel (page Consolider) ---------- */
$$('[data-engagement]').forEach((ta) => {
  const key = 'engagement:' + ta.dataset.engagement;
  ta.value = store.get(key, '') || '';
  let t;
  ta.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => store.set(key, ta.value), 400); });
});

/* ---------- radar des résultats ---------- */
$$('[data-radar]').forEach((box) => {
  box.addEventListener('pea:radar', (e) => {
    const rows = e.detail;
    const n = rows.length; const R = 90; const cx = 120; const cy = 120;
    const pt = (i, r) => { const a = -Math.PI / 2 + (2 * Math.PI * i) / n; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
    let svg = `<svg viewBox="0 0 240 240" role="img" aria-label="Résultats par étape"><title>Résultats par étape</title>`;
    [0.25, 0.5, 0.75, 1].forEach((k) => { svg += `<polygon class="grid" points="${rows.map((_, i) => pt(i, R * k).join(',')).join(' ')}"/>`; });
    rows.forEach((_, i) => { const [x, y] = pt(i, R); svg += `<line class="grid" x1="${cx}" y1="${cy}" x2="${x}" y2="${y}"/>`; });
    const pts = rows.map((r, i) => pt(i, R * (r.t ? r.c / r.t : 0)));
    svg += `<polygon class="f1 area" points="${pts.map((p) => p.join(',')).join(' ')}"/><polyline class="ci" points="${pts.concat([pts[0]]).map((p) => p.join(',')).join(' ')}"/>`;
    rows.forEach((r, i) => { const [x, y] = pt(i, R + 16); svg += `<text class="t-sm" x="${x}" y="${y}" text-anchor="middle" dominant-baseline="middle">${r.key}</text>`; });
    svg += '</svg>';
    box.innerHTML = svg;
    box.classList.add('fig');
  });
});
