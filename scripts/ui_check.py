"""Contrôle des comportements d'interface qui ne se voient pas dans le HTML produit.

  1. le thème choisi survit-il au changement de page, au rechargement et à un second onglet ;
  2. la taille du texte et le niveau de lecture survivent-ils de même ;
  3. le clic sur une figure ouvre-t-il le plein écran, le zoom agit-il, la fermeture rend-elle la main ;
  4. le clic sur une pastille de niveau de preuve affiche-t-il sa définition ;
  5. capture de quelques figures, en clair et en sombre, pour l'œil.

Usage : python scripts/ui_check.py [dossier_de_captures]
Code de sortie 1 si un contrôle échoue.
"""
from __future__ import annotations

import base64
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
    except Exception:  # noqa: BLE001
        pass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pwa_offline_test import CHROME, PORT, WS, evaluate  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SERVE_PORT = 8771
BASE_PATH = json.loads((ROOT / 'src' / 'site.json').read_text(encoding='utf-8'))['site']['base_path'].rstrip('/') + '/'
BASE = f'http://localhost:{SERVE_PORT}{BASE_PATH}'
SORTIE = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
MOD = 'harcelement-scolaire/01-grandir.html'
AUTRE = 'harcelement-scolaire/04-harcelement-ou-conflit.html'

resultats = []


def dit(nom, ok, detail=''):
    resultats.append(ok)
    print(f"  {'OK   ' if ok else 'ÉCHEC'} {nom}{('  — ' + str(detail)) if detail else ''}")


def va(ws, url, attente=2.4):
    ws.call('Page.navigate', url=url)
    time.sleep(attente)


def main():
    if not CHROME:
        print('Chrome introuvable')
        return 2
    server = subprocess.Popen([sys.executable, str(ROOT / 'scripts' / 'serve.py'), str(SERVE_PORT)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    prof = pathlib.Path(tempfile.mkdtemp(prefix='pea-ui-'))
    proc = subprocess.Popen([CHROME, '--headless=new', f'--remote-debugging-port={PORT}', f'--user-data-dir={prof}',
                             '--no-first-run', '--disable-gpu', '--hide-scrollbars', 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        ws.call('Emulation.setDeviceMetricsOverride', width=390, height=844, deviceScaleFactor=2, mobile=True)
        # système en sombre : un choix explicite « clair » doit donc tenir contre le système
        ws.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': 'dark'}])

        print('\n1. Le thème choisi tient-il ?')
        va(ws, BASE + MOD)
        depart = evaluate(ws, 'document.documentElement.dataset.theme || "(système)"')
        evaluate(ws, 'document.getElementById("themeBtn").click()')
        time.sleep(0.4)
        apres = evaluate(ws, 'document.documentElement.dataset.theme || ""')
        brut = evaluate(ws, 'localStorage.getItem("theme")')
        dit('le clic change le thème', apres == 'light', f'{depart} → {apres}')
        dit('la valeur stockée est lisible telle quelle', brut == 'light', f'localStorage.theme = {brut!r}')
        va(ws, BASE + AUTRE)
        dit('le choix survit au changement de page', evaluate(ws, 'document.documentElement.dataset.theme') == 'light')
        va(ws, BASE + AUTRE)
        dit('le choix survit au rechargement', evaluate(ws, 'document.documentElement.dataset.theme') == 'light')
        couleur = evaluate(ws, '(document.querySelector(\'meta[name="theme-color"]:not([media])\')||{}).content || ""')
        dit('la barre du navigateur suit le choix', couleur.upper().startswith('#F'), f'theme-color = {couleur}')

        print('\n2. Les autres réglages tiennent-ils ?')
        evaluate(ws, '''(() => { const b = document.querySelector('[data-fs="xl"]'); if (b) b.click(); })()''')
        time.sleep(0.3)
        dit('la taille du texte est stockée en clair', evaluate(ws, 'localStorage.getItem("fs")') == 'xl')
        va(ws, BASE + MOD)
        dit('la taille du texte survit au changement de page', evaluate(ws, 'document.documentElement.dataset.fs') == 'xl')
        evaluate(ws, '''(() => { const b = document.querySelector('[data-reading="essentiel"]'); if (b) b.click(); })()''')
        time.sleep(0.3)
        va(ws, BASE + AUTRE)
        dit('le niveau de lecture survit au changement de page', evaluate(ws, 'document.documentElement.dataset.reading') == 'essentiel')
        evaluate(ws, 'localStorage.clear()')

        print('\n3. La figure s’ouvre-t-elle en plein écran ?')
        va(ws, BASE + MOD, 3.0)
        num = evaluate(ws, '(document.querySelector("figure.fig .fig-n")||{}).textContent || ""')
        dit('la figure porte un numéro', num.startswith('Figure'), num)
        titre = evaluate(ws, '(document.querySelector("figure.fig .fig-t")||{}).textContent || ""')
        dit('la figure porte un titre', bool(titre), titre[:52])
        note = evaluate(ws, '(document.querySelector("figure.fig .fig-note-l")||{}).textContent || ""')
        dit('la note est étiquetée', note.strip() == 'Note.', note)
        evaluate(ws, 'document.querySelector("figure.fig .fig-box").click()')
        time.sleep(0.6)
        ouvert = evaluate(ws, '''JSON.stringify({ouvert: !!document.querySelector('.figview:not([hidden])'),
            svg: !!document.querySelector('.figview .fv-stage svg'), titre: (document.querySelector('.fv-title')||{}).textContent||''})''')
        d = json.loads(ouvert)
        dit('le plein écran s’ouvre avec le dessin', d['ouvert'] and d['svg'], d['titre'][:52])
        evaluate(ws, 'document.querySelector(".fv-plus").click()')
        time.sleep(0.4)
        z = evaluate(ws, 'getComputedStyle(document.querySelector(".figview")).getPropertyValue("--fv-z").trim()')
        dit('le bouton grossit le dessin', z and float(z) > 1, f'facteur {z}')
        evaluate(ws, 'document.querySelector(".fv-close").click()')
        time.sleep(0.5)
        dit('le bouton de fermeture referme', evaluate(ws, '!!document.querySelector(".figview[hidden]")'))

        print('\n4. La pastille de niveau de preuve s’explique-t-elle ?')
        evaluate(ws, '''(() => { const e = document.querySelector('main .ev[role="button"]'); if (e) e.click(); })()''')
        time.sleep(0.4)
        bulle = evaluate(ws, '(document.querySelector(".ev-tip .ev-tip-d")||{}).textContent || ""')
        dit('la définition s’affiche au clic', len(bulle) > 30, bulle[:64])

        if SORTIE:
            SORTIE.mkdir(parents=True, exist_ok=True)
            print('\n5. Captures')
            ws.call('Emulation.setDeviceMetricsOverride', width=980, height=1400, deviceScaleFactor=1, mobile=False)
            for theme in ('light', 'dark'):
                va(ws, BASE + MOD, 1.6)
                evaluate(ws, f'document.documentElement.dataset.theme = "{theme}"')
                # la figure est amenée en haut de la fenêtre : le découpage reste dans l'écran
                evaluate(ws, '''(() => { const f = document.querySelector('figure.fig');
                    scrollTo(0, f.getBoundingClientRect().top + scrollY - 70); })()''')
                time.sleep(1.4)
                box = json.loads(evaluate(ws, '''(() => { const r = document.querySelector('figure.fig').getBoundingClientRect();
                    return JSON.stringify({x: Math.max(0, r.left - 4), y: Math.max(0, r.top - 4),
                                           w: Math.min(innerWidth, r.width + 8), h: Math.min(innerHeight - Math.max(0, r.top - 4), r.height + 8)}); })()'''))
                shot = ws.call('Page.captureScreenshot', format='png',
                               clip={'x': box['x'], 'y': box['y'], 'width': box['w'], 'height': box['h'], 'scale': 1})
                (SORTIE / f'frise-{theme}.png').write_bytes(base64.b64decode(shot['data']))
                print(f'  frise-{theme}.png')
    finally:
        proc.kill()
        server.kill()
        time.sleep(0.5)
        shutil.rmtree(prof, ignore_errors=True)

    rates = resultats.count(False)
    print(f"\nVERDICT : {len(resultats) - rates}/{len(resultats)} contrôles passés")
    return 1 if rates else 0


if __name__ == '__main__':
    sys.exit(main())
