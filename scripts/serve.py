"""Serveur local qui reproduit le sous-chemin GitHub Pages.
    python scripts/serve.py [port]   ->  http://localhost:8765/Psychologie_de_l_enfant_et_de_l_adolescent/
"""
import gzip, http.server, json, pathlib, sys, functools
ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = json.loads((ROOT / 'src' / 'site.json').read_text(encoding='utf-8'))['site']['base_path'].rstrip('/')
PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8765
GZIP = '--no-gzip' not in sys.argv  # python scripts/serve.py 8765 --no-gzip pour servir sans compression
TEXT_TYPES = {'text/html', 'text/css', 'text/javascript', 'application/json', 'application/manifest+json', 'image/svg+xml', 'text/plain', 'application/xml', 'text/xml'}

class H(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        p = path.split('?', 1)[0].split('#', 1)[0]
        if p == BASE or p == BASE + '/':
            p = '/index.html'
        elif p.startswith(BASE + '/'):
            p = p[len(BASE):]
        else:
            return str(ROOT / '__hors-base__')
        return super().translate_path(p)

    def do_GET(self):
        target = pathlib.Path(self.translate_path(self.path))
        if target.is_dir():
            target = target / 'index.html'
        if not target.is_file():  # même comportement que GitHub Pages : 404.html servie avec le statut 404
            self._send(404, 'text/html; charset=utf-8', (ROOT / '404.html').read_bytes())
            return
        ctype = self.guess_type(str(target))
        if ctype.split(';')[0] in TEXT_TYPES:  # GitHub Pages compresse les textes : on fait de même pour des mesures locales fidèles
            self._send(200, ctype + ('; charset=utf-8' if 'charset' not in ctype else ''), target.read_bytes())
            return
        super().do_GET()

    def _send(self, status, ctype, body):
        gz = GZIP and 'gzip' in (self.headers.get('Accept-Encoding') or '')
        data = gzip.compress(body, 6) if gz else body
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        if gz:
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Vary', 'Accept-Encoding')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')  # revalidation à chaque fois, corps conservé (outils de mesure)
        self.send_header('Service-Worker-Allowed', BASE + '/')
        super().end_headers()
    def log_message(self, *a):
        pass

H.extensions_map.update({'.webmanifest': 'application/manifest+json', '.js': 'text/javascript', '.mjs': 'text/javascript', '.woff2': 'font/woff2', '.svg': 'image/svg+xml'})
handler = functools.partial(H, directory=str(ROOT))
print(f'http://localhost:{PORT}{BASE}/')
http.server.ThreadingHTTPServer(('127.0.0.1', PORT), handler).serve_forever()
