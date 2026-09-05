"""Page de relecture des passages en malgache : extrait chaque fragment lang="mg" du site
avec son contexte français, son module et sa section, et écrit _relecture-malgache.html
(page de travail, non publiée : la racine ignore les fichiers _*.html).

Usage : python scripts/extract_malgache.py
"""
from __future__ import annotations

import html as htmlmod
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
BODY = ROOT / 'src' / 'body' / 'harcelement-scolaire'
SITE = json.loads((ROOT / 'src' / 'site.json').read_text(encoding='utf-8'))
BASE = SITE['site']['base_path']
OUT = ROOT / '_relecture-malgache.html'
TXT = ROOT / 'src' / 'research' / 'malgache-a-relire.md'

TITLES = {}
for sess in SITE.get('sessions', []):
    steps = {st['key']: st['title'] for st in sess.get('steps', [])}
    for pg in sess.get('pages', []):
        etape = f"Étape {pg['step']} · {steps.get(pg['step'], '')}" if pg.get('step') else 'Page transversale'
        TITLES[pg['slug']] = (pg.get('num'), pg.get('title', pg['slug']), etape)

BLOCK = ('p', 'li', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'dd', 'dt', 'figcaption', 'span')


def txt(s):
    return re.sub(r'\s+', ' ', htmlmod.unescape(re.sub(r'<[^>]+>', '', s))).strip()


def enclosing(src, pos):
    """Bloc (p, li, td…) qui contient la position donnée : renvoie (nom, html interne)."""
    best = None
    for m in re.finditer(r'<(' + '|'.join(BLOCK[:-1]) + r')\b[^>]*>', src):
        if m.end() > pos:
            break
        name = m.group(1)
        close = src.find(f'</{name}>', m.end())
        if close > pos:
            best = (name, src[m.end():close])
    return best or ('', src[max(0, pos - 300):pos + 300])


def kind_of(name, block_html, mg):
    if name == 'p' and 'class="say"' in block_html[:0]:
        return 'phrase à dire'
    words = len(mg.split())
    if words >= 4 or mg.rstrip().endswith(('?', '.', '!')):
        return 'phrase'
    return 'mot ou expression'


items = []
for path in sorted(BODY.glob('*.html')):
    src = path.read_text(encoding='utf-8')
    slug = path.stem
    num, title, etape = TITLES.get(slug, (None, slug, ''))
    heads = [(m.start(), m.group(1), re.search(r'\sid="([^"]+)"', m.group(0)), txt(m.group(2)))
             for m in re.finditer(r'<(h[234])\b([^>]*)>(.*?)</\1>', src, re.S)]
    heads = [(m.start(), m.group(1), (re.search(r'\sid="([^"]+)"', m.group(0)) or [None, ''])[1], txt(m.group(3)))
             for m in re.finditer(r'<(h[234])\b([^>]*)>(.*?)</\1>', src, re.S)]
    for m in re.finditer(r'<(\w+)([^>]*)\slang="mg"([^>]*)>(.*?)</\1>', src, re.S):
        mg = txt(m.group(4))
        if not mg:
            continue
        sec = ('', '')
        for start, lvl, hid, htxt in heads:
            if start < m.start():
                sec = (hid, htxt)
        name, block = enclosing(src, m.start())
        full = txt(block)
        # contexte : le bloc complet, sans le fragment malgache lui-même
        ctx = full.replace(mg, ' ⟦…⟧ ').strip()
        say = 'class="say"' in src[max(0, m.start() - 400):m.start()]
        items.append({'slug': slug, 'num': num, 'title': title, 'etape': etape, 'sec_id': sec[0], 'sec': sec[1],
                      'mg': mg, 'ctx': ctx, 'tag': name, 'say': say,
                      'kind': 'phrase à dire à un enfant' if say else ('phrase' if (len(mg.split()) >= 4 or mg.rstrip()[-1:] in '?.!') else 'mot ou expression')})

# glossaire : entrées dont le terme ou les variantes sont en malgache
gloss = json.load(open(ROOT / 'data' / 'glossaire.json', encoding='utf-8'))
MG_HINT = re.compile(r'\b(malgache|malagasy|en mg\b)', re.I)
gl_items = []
for g in gloss:
    if g.get('categorie') != 'Madagascar et culture':
        continue
    long_txt = txt(g['long'])
    mgs = re.findall(r'<(\w+)[^>]*lang="mg"[^>]*>(.*?)</\1>', g['long'], re.S)
    gl_items.append({'id': g['id'], 'terme': g['terme'], 'variantes': g.get('variantes', []),
                     'court': g['court'], 'long': long_txt, 'mg': [txt(x[1]) for x in mgs]})

order = {s: i for i, s in enumerate(TITLES)}
items.sort(key=lambda it: order.get(it['slug'], 99))
phrases = [it for it in items if it['kind'] != 'mot ou expression']
mots = [it for it in items if it['kind'] == 'mot ou expression']
groups = [[it for it in phrases if it['say']], [it for it in phrases if not it['say']], mots]
n = 0
for grp in groups:  # numérotation continue dans l'ordre de lecture de la page
    for it in grp:
        n += 1
        it['n'] = n

CSS = """
:root { color-scheme: light dark; --paper:#F7F3EC; --surface:#FFFDF9; --ink:#1E2433; --ink-2:#4B5364; --ink-3:#5C6474;
        --line:#E3DDD2; --primary:#3B4B8C; --primary-soft:#E4E8F5; --accent-soft:#FBEFD9; --accent-ink:#8F5C00; }
@media (prefers-color-scheme: dark) { :root { --paper:#14161C; --surface:#1C1F27; --ink:#ECE6DA; --ink-2:#BDB7AB;
        --ink-3:#928D84; --line:#2C303B; --primary:#A5AEEA; --primary-soft:#242A3D; --accent-soft:#3D2E0E; --accent-ink:#E8C06A; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--paper); color:var(--ink); font:16px/1.6 'Public Sans','Segoe UI',system-ui,sans-serif; }
.wrap { max-width: 940px; margin: 0 auto; padding: 28px 18px 80px; }
h1 { font-family: Literata, Georgia, serif; font-size: 1.8rem; line-height:1.2; margin:0 0 6px; }
h2 { font-family: Literata, Georgia, serif; font-size: 1.25rem; margin: 34px 0 10px; padding-top:14px; border-top:1px solid var(--line); }
.lead { color: var(--ink-2); margin: 0 0 18px; }
.item { background: var(--surface); border:1px solid var(--line); border-radius: 12px; padding: 14px 16px; margin: 12px 0; }
.hd { display:flex; flex-wrap:wrap; gap:6px 12px; align-items:baseline; font-size:.78rem; color:var(--ink-3); margin-bottom:8px; }
.n { font-weight:700; color:var(--primary); font-size:.95rem; }
.kind { background:var(--primary-soft); color:var(--primary); border-radius:999px; padding:1px 9px; font-weight:700; font-size:.7rem; }
.kind.say { background:var(--accent-soft); color:var(--accent-ink); }
.mg { font-size:1.12rem; font-weight:600; background:var(--accent-soft); border-left:3px solid var(--accent-ink); padding:9px 12px; border-radius:0 8px 8px 0; margin:6px 0 10px; }
.ctx { color:var(--ink-2); font-size:.92rem; }
.ctx b { color:var(--ink); }
a { color: var(--primary); }
.mark { background: var(--primary-soft); padding:0 4px; border-radius:4px; font-weight:600; }
table { border-collapse:collapse; width:100%; font-size:.9rem; margin-top:8px; }
th,td { text-align:left; padding:7px 9px; border-bottom:1px solid var(--line); vertical-align:top; }
th { font-size:.75rem; text-transform:uppercase; letter-spacing:.05em; color:var(--ink-3); }
.term { font-weight:600; }
.small { font-size:.85rem; color:var(--ink-3); }
"""


def item_html(it):
    href = f"{BASE}harcelement-scolaire/{it['slug']}.html" + (f"#{it['sec_id']}" if it['sec_id'] else '')
    where = f"Module {it['num']}" if it['num'] else 'Page'
    ctx = htmlmod.escape(it['ctx']).replace('⟦…⟧', '<span class="mark">⟦ la phrase malgache ⟧</span>')
    return (f'<div class="item" id="p{it["n"]}"><div class="hd"><span class="n">{it["n"]}</span>'
            f'<span class="kind{" say" if it["say"] else ""}">{it["kind"]}</span>'
            f'<span>{where} · {htmlmod.escape(it["title"])}{" › " + htmlmod.escape(it["sec"]) if it["sec"] else ""}</span>'
            f'<a href="{href}" target="_blank" rel="noopener">voir dans le site ↗</a></div>'
            f'<div class="mg" lang="mg">{htmlmod.escape(it["mg"])}</div>'
            f'<div class="ctx">{ctx}</div></div>')


def gl_html(g):
    href = f"{BASE}glossaire.html#{g['id']}"
    var = ', '.join(g['variantes'][:6])
    return (f'<div class="item"><div class="hd"><span class="term">{htmlmod.escape(g["terme"])}</span>'
            f'<span class="small">variantes : {htmlmod.escape(var) or "—"}</span>'
            f'<a href="{href}" target="_blank" rel="noopener">voir dans le glossaire ↗</a></div>'
            f'<div class="ctx"><b>Définition courte :</b> {htmlmod.escape(g["court"])}</div>'
            f'<div class="ctx" style="margin-top:6px"><b>Définition longue :</b> {htmlmod.escape(g["long"][:900])}{"…" if len(g["long"]) > 900 else ""}</div></div>')


out = [f'<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">',
       '<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">',
       '<title>Relecture des passages en malgache</title>', f'<style>{CSS}</style></head><body><div class="wrap">',
       '<h1>Passages en malgache : à relire</h1>',
       f'<p class="lead">{len(items)} fragments balisés <code>lang="mg"</code> dans les 20 pages de la session, '
       f'dont {len(phrases)} phrases complètes et {len(mots)} mots ou expressions, plus {len(gl_items)} entrées de glossaire malgaches. '
       'Chaque fragment est donné avec la phrase française qui l\'entoure : ⟦ la phrase malgache ⟧ marque sa place exacte. '
       'Dites simplement les numéros à corriger, avec la correction ; les autres seront considérés comme validés.</p>',
       f'<h2>1. Phrases à dire à un enfant ou à un adulte ({len(groups[0])})</h2>']
out += [item_html(it) for it in groups[0]]
out += [f'<h2>2. Autres phrases complètes ({len(groups[1])})</h2>']
out += [item_html(it) for it in groups[1]]
out += [f'<h2>3. Mots et expressions ({len(mots)})</h2>']
out += [item_html(it) for it in mots]
out += [f'<h2>4. Entrées de glossaire malgaches ({len(gl_items)})</h2>',
        '<p class="lead">Le terme, sa définition courte (l\'infobulle) et sa définition longue. À vérifier : l\'orthographe, '
        'les variantes reconnues par la recherche, et surtout la justesse culturelle de la définition.</p>']
out += [gl_html(g) for g in gl_items]
out += ['</div></body></html>']
OUT.write_text('\n'.join(out), encoding='utf-8', newline='\n')

md = ['# Passages en malgache à faire relire par un locuteur', '',
      f'{len(items)} fragments `lang="mg"`, {len(gl_items)} entrées de glossaire malgaches. '
      'Page de relecture : `_relecture-malgache.html` (non publiée).', '']
for section, group in (('Phrases à dire', groups[0]), ('Autres phrases', groups[1]), ('Mots et expressions', groups[2])):
    md += [f'## {section}', '']
    for it in group:
        where = f"Module {it['num']}" if it['num'] else 'Page'
        md += [f'**{it["n"]}. {it["mg"]}**', f'  - {where} · {it["title"]}' + (f' › {it["sec"]}' if it['sec'] else ''),
               f'  - Contexte : {it["ctx"][:400]}', '']
md += ['## Entrées de glossaire malgaches', '']
for g in gl_items:
    md += [f'- **{g["terme"]}** ({", ".join(g["variantes"][:5])}) : {g["court"]}']
TXT.write_text('\n'.join(md) + '\n', encoding='utf-8', newline='\n')

print(f'{len(items)} fragments ({len(phrases)} phrases, {len(mots)} mots) + {len(gl_items)} entrées de glossaire')
print(f'→ {OUT.name} et {TXT.relative_to(ROOT)}')
