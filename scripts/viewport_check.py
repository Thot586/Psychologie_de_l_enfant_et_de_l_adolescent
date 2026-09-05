"""Contrôle des largeurs d'écran dans un Chrome headless indépendant (protocole DevTools, bibliothèque standard) :
pour chaque largeur (280, 320, 360, 375, 768 px, puis 360 px avec texte à 200 %), charge quelques pages et vérifie
qu'aucun défilement horizontal du document n'apparaît (scrollWidth ≤ largeur) et que l'en-tête tient dans la fenêtre.

Usage : python scripts/viewport_check.py [http://localhost:8765/Psychologie_de_l_enfant_et_de_l_adolescent/]
Code de sortie 1 si un débordement est constaté.
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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pwa_offline_test import CHROME, PORT, WS, evaluate  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SERVE_PORT = 8767
BASE_PATH = json.loads((ROOT / 'src' / 'site.json').read_text(encoding='utf-8'))['site']['base_path'].rstrip('/') + '/'
BASE = (sys.argv[1].rstrip('/') + '/') if len(sys.argv) > 1 else f'http://localhost:{SERVE_PORT}{BASE_PATH}'
PAGES = ['index.html', 'harcelement-scolaire/index.html', 'harcelement-scolaire/06-selon-l-age.html', 'harcelement-scolaire/14-demander-de-l-aide.html',
         'harcelement-scolaire/16-kit-de-sensibilisation.html', 'glossaire.html', 'references.html']
WIDTHS = [(280, 100), (320, 100), (360, 100), (375, 100), (768, 100), (360, 200)]
MEASURE = '''(() => { const de = document.documentElement; const top = document.querySelector('.top');
  const wide = []; for (const el of document.querySelectorAll('body *')) { const cs = getComputedStyle(el); if (cs.position === 'fixed' || cs.display === 'none') continue;
    const r = el.getBoundingClientRect(); if (r.right > de.clientWidth + 1 && (el.parentElement && getComputedStyle(el.parentElement).overflowX === 'visible') && !el.closest('[style*="overflow"], .tbl, .figwrap, pre, table')) wide.push(el.tagName + '.' + (el.className || '').toString().slice(0, 20) + ' r=' + Math.round(r.right)); }
  return JSON.stringify({ inner: innerWidth, client: de.clientWidth, scroll: de.scrollWidth, top: top ? Math.round(top.getBoundingClientRect().width) : null, wide: wide.slice(0, 5) }); })()'''


def main():
    if not CHROME:
        print('Chrome introuvable'); return 2
    server = None
    if len(sys.argv) < 2:
        server = subprocess.Popen([sys.executable, str(ROOT / 'scripts' / 'serve.py'), str(SERVE_PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
    prof = pathlib.Path(tempfile.mkdtemp(prefix='pea-vp-'))
    proc = subprocess.Popen([CHROME, '--headless=new', f'--remote-debugging-port={PORT}', f'--user-data-dir={prof}', '--no-first-run', '--disable-gpu', 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    bad = 0
    try:
        for _ in range(40):
            try:
                targets = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json')); break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        page = next(t for t in targets if t['type'] == 'page')
        ws = WS(page['webSocketDebuggerUrl'])
        ws.call('Page.enable'); ws.call('Runtime.enable')
        for width, zoom in WIDTHS:
            ws.call('Emulation.setDeviceMetricsOverride', width=width, height=740, deviceScaleFactor=2, mobile=True)
            for p in PAGES:
                ws.call('Page.navigate', url=BASE + p)
                time.sleep(2.2)
                if zoom != 100:
                    evaluate(ws, f'document.documentElement.style.fontSize="{zoom}%"')
                    time.sleep(0.4)
                m = json.loads(evaluate(ws, MEASURE))
                over = m['scroll'] - m['client']
                flag = 'DÉBORDEMENT' if over > 1 or (m['top'] and m['top'] > m['client'] + 1) else 'ok'
                if flag != 'ok':
                    bad += 1
                print(f'{width:4d}px texte {zoom:3d}%  {p:52s} client={m["client"]:4d} scroll={m["scroll"]:4d} en-tête={m["top"]}  {flag}  {m["wide"] if flag != "ok" else ""}')
    finally:
        proc.kill()
        if server:
            server.kill()
        time.sleep(0.5)
        shutil.rmtree(prof, ignore_errors=True)
    print('débordements :', bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
