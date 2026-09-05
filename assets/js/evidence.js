/* evidence.js — la pastille de niveau de preuve rappelle ce qu'elle veut dire, au clic.

   Les six définitions viennent de data/niveaux-preuve.json, posé par le build dans un îlot JSON :
   la légende de la page et ce rappel disent donc exactement la même chose.
   Sans ce script, la pastille reste un simple libellé, et la légende complète figure sur la page
   « Méthode et limites » — rien n'est perdu. */

const ilot = document.getElementById('ev-data');
const NIVEAUX = ilot ? JSON.parse(ilot.textContent || '{}') : {};
const METHODE = (ilot && ilot.dataset.methode) || '';
let bulle = null;

function classeNiveau(el) {
  return Array.from(el.classList).find((c) => c.startsWith('ev-') && NIVEAUX[c]);
}

function fermer() {
  if (!bulle) return;
  const ouvrant = document.querySelector('.ev[aria-expanded="true"]');
  if (ouvrant) ouvrant.setAttribute('aria-expanded', 'false');
  bulle.remove();
  bulle = null;
  removeEventListener('keydown', surTouche);
}

function surTouche(e) { if (e.key === 'Escape') { const o = document.querySelector('.ev[aria-expanded="true"]'); fermer(); if (o) o.focus(); } }

function ouvrir(el) {
  const cle = classeNiveau(el);
  if (!cle) return;
  fermer();
  const n = NIVEAUX[cle];
  bulle = document.createElement('div');
  bulle.className = 'tip ev-tip';
  bulle.setAttribute('role', 'dialog');
  bulle.setAttribute('aria-label', `Niveau de preuve : ${n.label}`);
  bulle.innerHTML = `<p class="ev-tip-t"><span class="ev ${cle}">${n.label}</span></p><p class="ev-tip-d"></p>`
    + (METHODE ? `<p class="ev-tip-l"><a href="${METHODE}#niveaux">Les six niveaux, et pourquoi</a></p>` : '');
  bulle.querySelector('.ev-tip-d').textContent = n.def;
  document.body.appendChild(bulle);

  const r = el.getBoundingClientRect();
  const larg = bulle.offsetWidth;
  const gauche = Math.min(Math.max(8, r.left + r.width / 2 - larg / 2), innerWidth - larg - 8);
  const dessous = r.bottom + 8 + bulle.offsetHeight < innerHeight;
  bulle.style.left = `${gauche + scrollX}px`;
  bulle.style.top = `${(dessous ? r.bottom + 8 : r.top - bulle.offsetHeight - 8) + scrollY}px`;
  el.setAttribute('aria-expanded', 'true');
  addEventListener('keydown', surTouche);
}

document.addEventListener('click', (e) => {
  const el = e.target.closest('.ev');
  if (!el || !classeNiveau(el) || el.closest('.legend, .ev-tip')) { if (!e.target.closest('.ev-tip')) fermer(); return; }
  e.preventDefault();
  e.stopPropagation();
  if (el.getAttribute('aria-expanded') === 'true') { fermer(); return; }
  ouvrir(el);
});
addEventListener('scroll', fermer, { passive: true });
addEventListener('resize', fermer, { passive: true });

// une pastille devient un bouton : atteignable au clavier, annoncée comme telle
document.querySelectorAll('.ev').forEach((el) => {
  if (!classeNiveau(el) || el.closest('.legend')) return;
  el.setAttribute('tabindex', '0');
  el.setAttribute('role', 'button');
  el.setAttribute('aria-expanded', 'false');
  el.title = 'Ce que signifie ce niveau';
  el.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); if (el.getAttribute('aria-expanded') === 'true') fermer(); else ouvrir(el); }
  });
});
