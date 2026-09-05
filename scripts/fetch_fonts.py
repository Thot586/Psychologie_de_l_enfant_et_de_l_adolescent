"""Télécharge les polices du site (Literata, Public Sans) en WOFF2 découpés par plage Unicode
depuis les fichiers servis par Google Fonts, et écrit src/css/fonts.css avec des chemins locaux.

Les polices sont sous SIL Open Font License 1.1 ; les textes de licence sont copiés dans assets/fonts/.
Usage : python scripts/fetch_fonts.py
"""
from __future__ import annotations

import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / 'assets' / 'fonts'
FONTS.mkdir(parents=True, exist_ok=True)

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
CSS_URL = ('https://fonts.googleapis.com/css2?'
           'family=Literata:ital,opsz,wght@0,7..72,400..700;1,7..72,400..700'
           '&family=Public+Sans:ital,wght@0,400..700;1,400..700'
           '&display=swap')
LICENSES = {
    'OFL-Literata.txt': 'https://raw.githubusercontent.com/googlefonts/literata/main/OFL.txt',
    'OFL-PublicSans.txt': 'https://raw.githubusercontent.com/uswds/public-sans/develop/LICENSE.md',
}
KEEP_SUBSETS = {'latin', 'latin-ext'}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


css = get(CSS_URL).decode('utf-8')
blocks = re.findall(r'/\* (\S+) \*/\s*@font-face \{(.*?)\}', css, re.S)
out = ['/* Polices auto-hébergées : Literata et Public Sans (SIL OFL 1.1). Généré par scripts/fetch_fonts.py */']
n = 0
for subset, body in blocks:
    if subset not in KEEP_SUBSETS:
        continue
    family = re.search(r"font-family: '([^']+)'", body).group(1)
    style = re.search(r'font-style: (\w+)', body).group(1)
    weight = re.search(r'font-weight: ([\d ]+)', body).group(1).strip()
    url = re.search(r'url\((https://[^)]+)\)', body).group(1)
    urange = re.search(r'unicode-range: ([^;]+);', body).group(1).strip()
    fam_slug = family.lower().replace(' ', '-')
    fname = f'{fam_slug}-{style}-{subset}.woff2'
    data = get(url)
    (FONTS / fname).write_bytes(data)
    n += 1
    print(f'  {fname:40s} {len(data)//1024:4d} Ko  weight {weight}')
    out.append(
        '@font-face {\n'
        f"  font-family: '{family}';\n"
        f'  font-style: {style};\n'
        f'  font-weight: {weight};\n'
        '  font-display: swap;\n'
        f"  src: url('../fonts/{fname}') format('woff2');\n"
        f'  unicode-range: {urange};\n'
        '}'
    )
(ROOT / 'src' / 'css').mkdir(parents=True, exist_ok=True)
(ROOT / 'src' / 'css' / 'fonts.css').write_text('\n'.join(out) + '\n', encoding='utf-8')
for name, url in LICENSES.items():
    try:
        (FONTS / name).write_bytes(get(url))
        print(f'  {name} ok')
    except Exception as e:  # noqa: BLE001
        print(f'  {name} ECHEC {e}')
print(f'{n} fichiers de police ; src/css/fonts.css écrit')
