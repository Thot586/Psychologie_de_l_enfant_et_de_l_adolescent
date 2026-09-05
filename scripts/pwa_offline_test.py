"""Test hors ligne de la PWA dans un Chrome headless indépendant (protocole DevTools, bibliothèque standard).

  1. lance Chrome headless avec un profil vierge et un port de débogage ;
  2. ouvre une page de module, attend l'installation et l'activation du service worker ;
  3. coupe le réseau (Network.emulateNetworkConditions offline) ;
  4. charge une page pré-cachée, une page consultée, une page jamais consultée ;
  5. affiche les titres obtenus : les deux premières doivent être servies, la troisième doit être « hors-ligne.html ».

Usage : python scripts/pwa_offline_test.py [http://localhost:8765/Psychologie_de_l_enfant_et_de_l_adolescent/]
Code de sortie 1 si le service worker ne sert pas les pages attendues.
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SERVE_PORT = 8766  # serveur dédié au test : on l'arrête pour la phase hors ligne (les requêtes du service worker ignorent l'émulation réseau de la page)
BASE_PATH = json.loads((ROOT / 'src' / 'site.json').read_text(encoding='utf-8'))['site']['base_path'].rstrip('/') + '/'
BASE = (sys.argv[1].rstrip('/') + '/') if len(sys.argv) > 1 else f'http://localhost:{SERVE_PORT}{BASE_PATH}'
CHROME = next((p for p in [r'C:\Program Files\Google\Chrome\Application\chrome.exe', r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                           '/usr/bin/google-chrome', '/usr/bin/chromium'] if os.path.exists(p)), None)
PORT = 9333


class WS:
    """Client WebSocket minimal (masquage client, trames texte, sans extension)."""

    def __init__(self, url):
        host, rest = url.split('://', 1)[1].split('/', 1)
        h, p = host.split(':')
        self.s = socket.create_connection((h, int(p)), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f'GET /{rest} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                        f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            buf += self.s.recv(4096)
        self.rest = buf.split(b'\r\n\r\n', 1)[1]
        self.n = 0

    def send(self, method, **params):
        self.n += 1
        data = json.dumps({'id': self.n, 'method': method, 'params': params}).encode()
        head = bytearray([0x81])
        ln = len(data)
        if ln < 126:
            head.append(0x80 | ln)
        elif ln < 65536:
            head.append(0x80 | 126); head += struct.pack('>H', ln)
        else:
            head.append(0x80 | 127); head += struct.pack('>Q', ln)
        mask = os.urandom(4)
        self.s.sendall(bytes(head) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))
        return self.n

    def _read_exact(self, n):
        while len(self.rest) < n:
            chunk = self.s.recv(65536)
            if not chunk:
                raise ConnectionError('socket fermé')
            self.rest += chunk
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def recv(self):
        b1, b2 = self._read_exact(2)
        ln = b2 & 0x7F
        if ln == 126:
            ln = struct.unpack('>H', self._read_exact(2))[0]
        elif ln == 127:
            ln = struct.unpack('>Q', self._read_exact(8))[0]
        payload = self._read_exact(ln)
        if (b1 & 0x0F) == 0x8:
            raise ConnectionError('close')
        return json.loads(payload.decode()) if (b1 & 0x0F) == 0x1 else None

    def call(self, method, **params):
        i = self.send(method, **params)
        while True:
            m = self.recv()
            if m and m.get('id') == i:
                if 'error' in m:
                    raise RuntimeError(m['error'])
                return m.get('result', {})


def evaluate(ws, expr):
    r = ws.call('Runtime.evaluate', expression=expr, awaitPromise=True, returnByValue=True)
    return r.get('result', {}).get('value')


def navigate(ws, url, wait=4.0):
    ws.call('Page.navigate', url=url)
    time.sleep(wait)
    return evaluate(ws, 'JSON.stringify({title: document.title, h1: (document.querySelector("h1")||{}).textContent||"", url: location.pathname})')


def main():
    if not CHROME:
        print('Chrome introuvable'); return 2
    prof = pathlib.Path(tempfile.mkdtemp(prefix='pea-pwa-'))
    server = None
    if len(sys.argv) < 2:
        server = subprocess.Popen([sys.executable, str(ROOT / 'scripts' / 'serve.py'), str(SERVE_PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
    proc = subprocess.Popen([CHROME, '--headless=new', f'--remote-debugging-port={PORT}', f'--user-data-dir={prof}', '--no-first-run',
                             '--disable-gpu', '--window-size=412,915', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                targets = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json'))
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        else:
            print('Chrome ne répond pas'); return 2
        page = next(t for t in targets if t['type'] == 'page')
        ws = WS(page['webSocketDebuggerUrl'])
        ws.call('Page.enable'); ws.call('Runtime.enable'); ws.call('Network.enable')
        first = navigate(ws, BASE + 'harcelement-scolaire/14-demander-de-l-aide.html', 5)
        print('en ligne      :', first)
        state = None
        for _ in range(40):
            state = evaluate(ws, '''(async () => { const r = await navigator.serviceWorker.getRegistration(); const ks = await caches.keys(); let n = 0; for (const k of ks) n += (await (await caches.open(k)).keys()).length; return JSON.stringify({active: r && r.active ? r.active.state : null, controller: !!navigator.serviceWorker.controller, caches: ks.length, entries: n}); })()''')
            st = json.loads(state)
            if st['active'] == 'activated' and st['entries'] >= 26:
                break
            time.sleep(1)
        print('service worker :', state)
        if not st['controller']:
            navigate(ws, BASE + 'harcelement-scolaire/14-demander-de-l-aide.html', 4)  # la page suivante est contrôlée
        ws.call('Network.emulateNetworkConditions', offline=True, latency=0, downloadThroughput=-1, uploadThroughput=-1)
        if server:
            server.kill(); time.sleep(1)  # plus aucun serveur : seul le cache du service worker peut répondre
            print('serveur de test arrêté : phase hors ligne')
        cached = json.loads(navigate(ws, BASE + 'harcelement-scolaire/index.html', 6))
        visited = json.loads(navigate(ws, BASE + 'harcelement-scolaire/14-demander-de-l-aide.html', 6))
        never = json.loads(navigate(ws, BASE + 'harcelement-scolaire/01-grandir.html', 8))
        print('hors ligne, pré-cachée :', cached)
        print('hors ligne, consultée  :', visited)
        print('hors ligne, inconnue   :', never)
        ok = ('harcèlement' in cached['title'].lower() and 'hors ligne' not in cached['title'].lower()) and 'demander' in visited['title'].lower() \
            and ('hors ligne' in never['title'].lower() or 'hors ligne' in never['h1'].lower())
        print('VERDICT :', 'OK — le service worker sert les pages en cache et replie sur hors-ligne.html' if ok else 'ÉCHEC')
        return 0 if ok else 1
    finally:
        proc.kill()
        if server and server.poll() is None:
            server.kill()
        time.sleep(0.5)
        shutil.rmtree(prof, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
