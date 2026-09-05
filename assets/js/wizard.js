/* wizard.js — transforme l'arbre statique de l'assistant de repérage en parcours pas à pas. */
const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
$$('.wiz[data-start]').forEach((wiz) => {
  const nodes = new Map($$('.wnode', wiz).map((n) => [n.dataset.node, n]));
  const trail = $('#wtrail', wiz) || $('.wtrail', wiz);
  const reset = $('#wreset', wiz) || $('.wtools button', wiz);
  let path = [];
  wiz.classList.add('js');
  function show(key) {
    nodes.forEach((n) => n.classList.remove('cur'));
    const n = nodes.get(key);
    if (!n) return;
    n.classList.add('cur');
    const first = $('a, button', n);
    if (first) first.focus({ preventScroll: true });
    reset.hidden = path.length === 0;
  }
  nodes.forEach((n) => {
    $$('a[data-next]', n).forEach((a) => a.addEventListener('click', (e) => {
      e.preventDefault();
      const q = ($('.wq', n) || {}).textContent || '';
      path.push(q.replace(/^\d+\.\s*/, '').split(' :')[0] + ' → ' + a.textContent.trim());
      trail.textContent = path.join(' · ');
      show(a.dataset.next);
      wiz.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }));
  });
  reset.addEventListener('click', () => { path = []; trail.textContent = ''; show(wiz.dataset.start); });
  show(wiz.dataset.start);
});
