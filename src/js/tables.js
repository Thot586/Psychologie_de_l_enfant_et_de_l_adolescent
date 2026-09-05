/* tables.js — en-tête de tableau qui reste visible tant que le tableau l'est.

   « position: sticky » ne suffit pas ici : les tableaux larges vivent dans un conteneur
   à défilement horizontal (.tw), et un tel conteneur devient le référent du collage —
   l'en-tête sort donc de l'écran avec le reste de la page. On duplique l'en-tête dans une
   barre fixe, affichée seulement pendant que le tableau traverse le haut de la fenêtre,
   alignée sur le tableau et suivant son défilement horizontal. */

const tables = [];

function headTop() {
  const top = document.querySelector('.top');
  if (!top) return 0;
  const r = top.getBoundingClientRect();
  return Math.max(0, r.bottom);      // l'en-tête du site se masque au défilement : on suit sa position réelle
}

function mesurer(t) {
  const cells = Array.from(t.source.rows[0].cells);
  t.clone.rows[0] && Array.from(t.clone.rows[0].cells).forEach((c, i) => {
    if (cells[i]) c.style.width = cells[i].getBoundingClientRect().width + 'px';
  });
  t.cloneTable.style.width = t.table.getBoundingClientRect().width + 'px';
}

function placer(t) {
  const rect = t.table.getBoundingClientRect();
  const wrap = t.wrap.getBoundingClientRect();
  const haut = headTop();
  const hauteurTete = t.source.getBoundingClientRect().height;
  const visible = rect.top < haut && rect.bottom > haut + hauteurTete + 8 && wrap.width > 0;
  if (!visible) {
    if (t.affiche) { t.bar.hidden = true; t.affiche = false; }
    return;
  }
  if (!t.affiche) { t.bar.hidden = false; t.affiche = true; mesurer(t); }
  t.bar.style.top = haut + 'px';
  t.bar.style.left = wrap.left + 'px';
  t.bar.style.width = wrap.width + 'px';
  t.cloneTable.style.transform = `translateX(${rect.left - wrap.left}px)`;
}

let planifie = false;
function rafraichir() {
  if (planifie) return;
  planifie = true;
  requestAnimationFrame(() => { planifie = false; tables.forEach(placer); });
}

function preparer(wrap) {
  const table = wrap.querySelector('table');
  const source = table && table.tHead;
  if (!source || !source.rows.length) return;

  const bar = document.createElement('div');
  bar.className = 'thead-float';
  bar.hidden = true;
  bar.setAttribute('aria-hidden', 'true');   // doublon visuel : le vrai en-tête reste seul dans l'arbre d'accessibilité
  const cloneTable = document.createElement('table');
  const clone = source.cloneNode(true);
  clone.querySelectorAll('[id]').forEach((n) => n.removeAttribute('id'));
  clone.querySelectorAll('a, button').forEach((n) => n.setAttribute('tabindex', '-1'));
  cloneTable.appendChild(clone);
  bar.appendChild(cloneTable);
  document.body.appendChild(bar);

  const t = { wrap, table, source, bar, clone, cloneTable, affiche: false };
  tables.push(t);
  wrap.addEventListener('scroll', () => { if (t.affiche) placer(t); }, { passive: true });
}

document.querySelectorAll('.tw').forEach(preparer);
if (tables.length) {
  addEventListener('scroll', rafraichir, { passive: true });
  addEventListener('resize', () => { tables.forEach((t) => { t.affiche = false; t.bar.hidden = true; }); rafraichir(); }, { passive: true });
  // la largeur des colonnes change avec la taille du texte, le niveau de lecture ou l'arrivée des polices
  const remesurer = () => { tables.forEach((t) => { t.affiche = false; t.bar.hidden = true; }); rafraichir(); };
  document.addEventListener('pea:reflow', remesurer);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(remesurer);
  new MutationObserver(remesurer).observe(document.documentElement, { attributeFilter: ['data-reading', 'data-fs'] });
  addEventListener('beforeprint', () => tables.forEach((t) => { t.bar.hidden = true; t.affiche = false; }));
  rafraichir();
}
