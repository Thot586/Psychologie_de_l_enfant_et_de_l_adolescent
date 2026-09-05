"""Serveur local qui reproduit le sous-chemin GitHub Pages.
    python scripts/serve.py [port]   ->  http://localhost:8765/Psychologie_de_l_enfant_et_de_l_adolescent/
"""
import http.server, json, pathlib, sys, functools
ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = json.loads((ROOT / 'src' / 'site.json').read_text(encoding='utf-8'))['site']['base_path'].rstrip('/')
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765

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
            body = (ROOT / '404.html').read_bytes()
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Service-Worker-Allowed', BASE + '/')
        super().end_headers()
    def log_message(self, *a):
        pass

H.extensions_map.update({'.webmanifest': 'application/manifest+json', '.js': 'text/javascript', '.mjs': 'text/javascript', '.woff2': 'font/woff2', '.svg': 'image/svg+xml'})
handler = functools.partial(H, directory=str(ROOT))
print(f'http://localhost:{PORT}{BASE}/')
http.server.ThreadingHTTPServer(('127.0.0.1', PORT), handler).serve_forever()
