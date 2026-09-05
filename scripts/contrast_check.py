"""Contraste réellement rendu, mesuré dans un Chrome headless, en clair et en sombre.

Ne lit pas le CSS : interroge la page peinte. Pour chaque élément qui porte du texte, on
prend la couleur calculée, on remonte les ancêtres jusqu'au premier fond non transparent,
et on applique la formule de luminance relative de WCAG 2.1.

Seuils WCAG 2.1 AA : 4,5:1 pour le texte courant, 3:1 pour le grand texte (24 px, ou
18,66 px en gras) et pour les composants d'interface.

Usage : python scripts/contrast_check.py [base_url] [--tout]
Code de sortie 1 s'il reste un échec.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

for flux in (sys.stdout, sys.stderr):
    try:
        flux.reconfigure(encoding='utf-8', errors='replace')
    except Exception:  # noqa: BLE001  (console sans reconfiguration possible)
        pass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pwa_offline_test import CHROME, PORT, WS, evaluate  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SERVE_PORT = 8768
BASE_PATH = json.loads((ROOT / 'src' / 'site.json').read_text(encoding='utf-8'))['site']['base_path'].rstrip('/') + '/'
BASE = (sys.argv[1].rstrip('/') + '/') if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else f'http://localhost:{SERVE_PORT}{BASE_PATH}'
TOUT = '--tout' in sys.argv

PAGES = ['index.html', 'harcelement-scolaire/index.html', 'harcelement-scolaire/04-harcelement-ou-conflit.html',
         'harcelement-scolaire/07-chiffres-et-solidite.html', 'harcelement-scolaire/14-demander-de-l-aide.html',
         'harcelement-scolaire/17-ressources.html', 'harcelement-scolaire/methode-et-limites.html',
         'glossaire.html', 'references.html']

# Mesure exécutée dans la page. Retourne un échec par signature (rôle, couleur, fond), pas par élément.
MESURE = r'''(() => {
  const lum = (c) => { const f = c.map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]; };
  // Chrome rend soit « rgb(30, 36, 51) » soit « color(srgb 0.11 0.12 0.15 / 0.92) », dont les canaux vont de 0 à 1
  const rgb = (s) => {
    const m = (s || '').match(/-?[\d.]+/g);
    if (!m) return null;
    const v = m.slice(0, 4).map(Number);
    if (/^color\(/.test(s)) { v[0] *= 255; v[1] *= 255; v[2] *= 255; }
    return v;
  };
  const over = (fg, bg) => { const a = fg.length > 3 ? fg[3] : 1; return [0, 1, 2].map((i) => fg[i] * a + bg[i] * (1 - a)); };
  const ratio = (a, b) => { const l1 = lum(a), l2 = lum(b); return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); };
  const hex = (c) => '#' + c.slice(0, 3).map((v) => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase();

  // fond effectif : on empile les fonds semi-transparents jusqu'à un fond opaque
  const fondDe = (el) => {
    const pile = [];
    for (let n = el; n; n = n.parentElement) {
      const c = rgb(getComputedStyle(n).backgroundColor);
      if (!c) continue;
      const a = c.length > 3 ? c[3] : 1;
      if (a === 0) continue;
      pile.push(c);
      if (a === 1) break;
    }
    let bg = [255, 255, 255];
    for (let i = pile.length - 1; i >= 0; i--) bg = over(pile[i], bg);
    bg.pile = pile;
    return bg;
  };

  const visible = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };

  const role = (el) => {
    const t = el.tagName.toLowerCase();
    const dans = (s) => el.closest(s) ? s : '';
    const cadre = dans('thead') || dans('.thead-float') || dans('table') || dans('aside.deep') || dans('.qz') ||
                  dans('.foot') || dans('.top') || dans('.rail') || dans('figure') || dans('.kf') || dans('.box') || '';
    const cls = (el.className && el.className.toString ? el.className.toString() : '').trim().split(/\s+/).filter(Boolean).slice(0, 2).join('.');
    return (cadre ? cadre + ' ' : '') + t + (cls ? '.' + cls : '');
  };

  const res = {};
  for (const el of document.querySelectorAll('body *')) {
    if (!el.childNodes.length) continue;
    let texte = '';
    for (const n of el.childNodes) if (n.nodeType === 3) texte += n.nodeValue;
    texte = texte.trim();
    if (!texte) continue;
    if (!visible(el)) continue;
    const cs = getComputedStyle(el);
    const fg0 = rgb(cs.color);
    if (!fg0) continue;
    const bg = fondDe(el);
    const fg = over(fg0, bg);
    const px = parseFloat(cs.fontSize);
    const gras = parseInt(cs.fontWeight, 10) >= 700;
    const grand = px >= 24 || (gras && px >= 18.66);
    const seuil = grand ? 3 : 4.5;
    const r = ratio(fg, bg);
    const cle = role(el) + '|' + hex(fg) + '|' + hex(bg) + '|' + Math.round(px) + (gras ? 'g' : '');
    if (!res[cle] || res[cle].r > r) {
      res[cle] = { role: role(el), fg: hex(fg), bg: hex(bg), px: Math.round(px * 10) / 10, gras, seuil,
                   r: Math.round(r * 100) / 100, ok: r >= seuil, ex: texte.slice(0, 48),
                   pile: (bg.pile || []).map((c) => hex(c) + (c.length > 3 && c[3] < 1 ? '@' + c[3] : '')).join(' < ') };
    }
  }
  return JSON.stringify(Object.values(res));
})()'''


def main():
    if not CHROME:
        print('Chrome introuvable')
        return 2
    server = None
    if len(sys.argv) < 2 or sys.argv[1].startswith('--'):
        server = subprocess.Popen([sys.executable, str(ROOT / 'scripts' / 'serve.py'), str(SERVE_PORT)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
    prof = pathlib.Path(tempfile.mkdtemp(prefix='pea-ct-'))
    proc = subprocess.Popen([CHROME, '--headless=new', f'--remote-debugging-port={PORT}', f'--user-data-dir={prof}',
                             '--no-first-run', '--disable-gpu', '--hide-scrollbars', 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    echecs, limites, mesures = {}, {}, 0
    try:
        targets = None
        for _ in range(40):
            try:
                targets = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json'))
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        page = next(t for t in targets if t['type'] == 'page')
        ws = WS(page['webSocketDebuggerUrl'])
        ws.call('Page.enable')
        ws.call('Runtime.enable')
        ws.call('Emulation.setDeviceMetricsOverride', width=1280, height=900, deviceScaleFactor=1, mobile=False)
        for theme in ('light', 'dark'):
            ws.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': theme}])
            for p in PAGES:
                ws.call('Page.navigate', url=BASE + p)
                time.sleep(2.2)
                # on mesure aussi le choix explicite : il doit donner exactement le même résultat
                evaluate(ws, f'document.documentElement.dataset.theme = "{theme}"')
                time.sleep(0.3)
                brut = evaluate(ws, MESURE)
                for e in json.loads(brut or '[]'):
                    mesures += 1
                    cle = (theme, e['role'], e['fg'], e['bg'], e['px'], e['gras'])
                    cible = echecs if not e['ok'] else (limites if e['r'] < e['seuil'] + 0.5 else None)
                    if cible is not None and (cle not in cible or cible[cle]['pages'][0] != p):
                        cible.setdefault(cle, {**e, 'theme': theme, 'pages': []})['pages'].append(p)
    finally:
        proc.kill()
        if server:
            server.kill()
        time.sleep(0.5)
        shutil.rmtree(prof, ignore_errors=True)

    def montre(titre, d):
        print(f'\n{titre} ({len(d)})')
        for (theme, role, fg, bg, px, gras), e in sorted(d.items(), key=lambda kv: kv[1]['r']):
            autres = len(e['pages']) - 1
            suite = f' et {autres} autre(s)' if autres else ''
            poids = 'gras' if gras else ''
            print(f"  {theme:5} {e['r']:5.2f}:1  (seuil {e['seuil']}) {fg} sur {bg}  {px:g}px {poids:4}  {role}")
            print(f"        « {e['ex']} »  — {e['pages'][0]}{suite}")
            if e.get('pile'):
                print(f"        fonds empilés : {e['pile']}")

    print(f'{mesures} combinaisons texte/fond mesurées sur {len(PAGES)} pages, en clair et en sombre')
    montre('ÉCHECS WCAG AA', echecs)
    if TOUT or limites:
        montre('limites (passent de moins de 0,5)', limites)
    if not echecs:
        print('\nVERDICT : OK — tout le texte rendu atteint le seuil AA dans les deux thèmes.')
    return 1 if echecs else 0


if __name__ == '__main__':
    sys.exit(main())
