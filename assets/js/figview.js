/* figview.js — voir une figure en plein écran, la grossir et s'y déplacer.

   Le dessin est un SVG : l'agrandir ne le floute pas, on peut donc pousser loin sans perte.
   On clone le SVG plutôt que de le déplacer, pour que la page garde le sien pendant l'affichage.
   Fermeture : le bouton, Échap, ou le bouton retour d'Android — l'ouverture pose une entrée
   d'historique, comme le panneau du glossaire, pour que le geste habituel referme la vue. */

const PALIERS = [1, 1.5, 2, 3, 4, 6];
const MIN = PALIERS[0];
const MAX = PALIERS[PALIERS.length - 1];
let vue = null;
let etat = null;

function construire() {
  const d = document.createElement('div');
  d.className = 'figview';
  d.hidden = true;
  d.setAttribute('role', 'dialog');
  d.setAttribute('aria-modal', 'true');
  d.setAttribute('aria-label', 'Figure en plein écran');
  d.innerHTML = `<div class="fv-bar">
      <p class="fv-title" id="fv-title"></p>
      <button type="button" class="fv-moins" aria-label="Réduire">−</button>
      <span class="fv-niveau" aria-live="polite"></span>
      <button type="button" class="fv-plus" aria-label="Grossir">+</button>
      <button type="button" class="fv-close" aria-label="Fermer le plein écran">✕</button>
    </div>
    <div class="fv-stage" tabindex="0"><p class="fv-astuce" hidden>Tournez votre téléphone : cette figure est plus large que haute.</p></div>
    <p class="fv-note"></p>`;
  d.setAttribute('aria-labelledby', 'fv-title');
  document.body.appendChild(d);
  d.querySelector('.fv-close').addEventListener('click', fermer);
  d.querySelector('.fv-plus').addEventListener('click', () => zoom(1));
  d.querySelector('.fv-moins').addEventListener('click', () => zoom(-1));
  d.addEventListener('click', (e) => { if (e.target === d) fermer(); });
  return d;
}

function peindre() {
  const ajuste = etat.z <= MIN + 0.001;
  vue.style.setProperty('--fv-z', etat.z);
  vue.classList.toggle('fv-fit', ajuste);   // au repos la figure entière est visible, hauteur comprise
  vue.querySelector('.fv-niveau').textContent = ajuste ? 'entière' : `${Math.round(etat.z * 100)} %`;
  vue.querySelector('.fv-moins').disabled = ajuste;
  vue.querySelector('.fv-plus').disabled = etat.z >= MAX - 0.001;
  vue.querySelector('.fv-stage').style.cursor = ajuste ? 'zoom-in' : 'grab';
}

function poser(z, ancre) {
  z = Math.min(MAX, Math.max(MIN, z));
  if (Math.abs(z - etat.z) < 0.001) return;
  const scene = vue.querySelector('.fv-stage');
  // on garde sous les yeux le point visé : sa position relative dans le contenu ne bouge pas
  const r = scene.getBoundingClientRect();
  const cx = ancre ? ancre.x - r.left : r.width / 2;
  const cy = ancre ? ancre.y - r.top : r.height / 2;
  const px = (scene.scrollLeft + cx) / Math.max(1, scene.scrollWidth);
  const py = (scene.scrollTop + cy) / Math.max(1, scene.scrollHeight);
  etat.z = z;
  peindre();
  requestAnimationFrame(() => {
    scene.scrollLeft = px * scene.scrollWidth - cx;
    scene.scrollTop = py * scene.scrollHeight - cy;
  });
}

// les boutons avancent d'un palier ; le pincement, lui, est continu
function zoom(sens, ancre) {
  const suivant = sens > 0 ? PALIERS.find((p) => p > etat.z + 0.001) : [...PALIERS].reverse().find((p) => p < etat.z - 0.001);
  poser(suivant === undefined ? (sens > 0 ? MAX : MIN) : suivant, ancre);
}

function clavier(e) {
  if (!vue || vue.hidden) return;
  if (e.key === 'Escape') { e.preventDefault(); fermer(); }
  else if (e.key === '+' || e.key === '=') { e.preventDefault(); zoom(1); }
  else if (e.key === '-') { e.preventDefault(); zoom(-1); }
  else if (e.key === 'Tab') {
    const cibles = Array.from(vue.querySelectorAll('button:not([disabled]), .fv-stage'));
    const i = cibles.indexOf(document.activeElement);
    const suiv = e.shiftKey ? (i <= 0 ? cibles.length - 1 : i - 1) : (i === cibles.length - 1 ? 0 : i + 1);
    e.preventDefault();
    cibles[suiv].focus();
  }
}

/* Une figure large tient mal dans un écran tenu à la verticale. Là où le navigateur
   l'autorise — Android, en plein écran système — on demande la rotation ; ailleurs (iOS
   ne l'expose pas) on se contente de le dire, la vue suivant de toute façon l'appareil. */
function paysage(svg) {
  const vb = (svg.getAttribute('viewBox') || '').split(/[\s,]+/).map(Number);
  const large = vb.length === 4 && vb[2] > vb[3] * 1.25;
  if (!large || innerWidth > innerHeight || innerWidth > 900) return false;
  const el = vue;
  const plein = el.requestFullscreen || el.webkitRequestFullscreen;
  if (plein && screen.orientation && screen.orientation.lock) {
    plein.call(el).then(() => screen.orientation.lock('landscape')).then(() => { etat.tourne = true; }).catch(() => { indice(); });
  } else {
    indice();
  }
  return true;
}
function indice() { if (vue) { const a = vue.querySelector('.fv-astuce'); a.hidden = false; setTimeout(() => { a.hidden = true; }, 5000); } }

function ouvrir(figure) {
  const svg = figure.querySelector('.fig-box svg');
  if (!svg) return;
  if (!vue) vue = construire();
  etat = { z: 1, depuis: document.activeElement, tourne: false };

  const n = figure.dataset.figN;
  const titre = (figure.querySelector('.fig-t') || {}).textContent || '';
  vue.querySelector('.fv-title').innerHTML = (n ? `<b>Figure ${n}.</b> ` : '') + (titre ? titre.replace(/[<>&]/g, '') : '');
  const note = figure.querySelector('.fig-note');
  const zoneNote = vue.querySelector('.fv-note');
  zoneNote.textContent = note ? note.textContent.trim() : '';
  zoneNote.hidden = !zoneNote.textContent;

  const scene = vue.querySelector('.fv-stage');
  const astuce = scene.querySelector('.fv-astuce');
  scene.innerHTML = '';
  scene.appendChild(astuce);
  const copie = svg.cloneNode(true);
  copie.removeAttribute('id');
  copie.querySelectorAll('[id]').forEach((x) => x.removeAttribute('id'));
  copie.removeAttribute('aria-labelledby');
  copie.setAttribute('role', 'img');
  copie.setAttribute('aria-label', (titre || 'Figure') + '. ' + zoneNote.textContent);
  scene.appendChild(copie);

  vue.hidden = false;
  document.body.classList.add('fv-open');
  peindre();
  scene.focus();
  paysage(svg);
  addEventListener('keydown', clavier);
  // le bouton retour d'Android referme la vue au lieu de quitter la page
  history.pushState({ figview: true }, '');
  addEventListener('popstate', surRetour);
}

function surRetour() { if (vue && !vue.hidden) fermer(true); }

function fermer(depuisHistorique) {
  if (!vue || vue.hidden) return;
  vue.hidden = true;
  const sv = vue.querySelector('.fv-stage svg');
  if (sv) sv.remove();
  document.body.classList.remove('fv-open');
  removeEventListener('keydown', clavier);
  removeEventListener('popstate', surRetour);
  if (etat && etat.tourne) { try { screen.orientation.unlock(); } catch { /* non supporté */ } }
  if (document.fullscreenElement) { try { document.exitFullscreen(); } catch { /* ignore */ } }
  vue.querySelector('.fv-astuce').hidden = true;
  if (!depuisHistorique && history.state && history.state.figview) history.back();
  if (etat && etat.depuis && etat.depuis.focus) etat.depuis.focus();
  etat = null;
}

document.addEventListener('click', (e) => {
  const bouton = e.target.closest('.fig-zoom');
  const boite = bouton ? null : e.target.closest('figure.fig .fig-box');
  if (!bouton && !boite) return;
  // un lien ou un bouton dans la figure garde son rôle
  if (!bouton && e.target.closest('a, button')) return;
  e.preventDefault();
  ouvrir((bouton || boite).closest('figure.fig'));
});

// molette avec Ctrl, comme partout ailleurs
document.addEventListener('wheel', (e) => {
  if (!vue || vue.hidden || !e.ctrlKey) return;
  e.preventDefault();
  zoom(e.deltaY < 0 ? 1 : -1, { x: e.clientX, y: e.clientY });
}, { passive: false });

// double tap ou double clic : un cran de plus, et retour au départ au sommet
document.addEventListener('dblclick', (e) => {
  if (!vue || vue.hidden || !e.target.closest('.fv-stage')) return;
  e.preventDefault();
  if (etat.z >= MAX - 0.001) poser(MIN); else zoom(1, { x: e.clientX, y: e.clientY });
});

/* pincement à deux doigts : le geste attendu sur une image, en continu */
let pince = null;
const ecart = (t1, t2) => Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
document.addEventListener('touchstart', (e) => {
  if (!vue || vue.hidden || e.touches.length !== 2 || !e.target.closest('.fv-stage')) return;
  pince = { d: ecart(e.touches[0], e.touches[1]), z: etat.z };
}, { passive: true });
document.addEventListener('touchmove', (e) => {
  if (!pince || e.touches.length !== 2) return;
  e.preventDefault();
  const d = ecart(e.touches[0], e.touches[1]);
  poser(pince.z * (d / Math.max(1, pince.d)), {
    x: (e.touches[0].clientX + e.touches[1].clientX) / 2,
    y: (e.touches[0].clientY + e.touches[1].clientY) / 2,
  });
}, { passive: false });
document.addEventListener('touchend', () => { if (pince) pince = null; }, { passive: true });
