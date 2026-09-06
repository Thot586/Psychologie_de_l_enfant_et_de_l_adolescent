"""Assemble le site statique à partir de src/ et data/.

    python scripts/build.py            construit tout, échoue sur toute erreur de validation
    python scripts/build.py --lenient  signale les erreurs de contenu sans arrêter (développement)
    python scripts/build.py --check    n'écrit rien, liste les fichiers qui changeraient

Entrées :  src/site.json, src/shell/*.html, src/body/**, src/figures/**, src/css/*.css, src/sw.template.js,
           data/glossaire.json, data/references.json, data/quiz/*.json, data/wizard.json, data/ressources.json,
           data/interactifs/*.json
Sorties :  pages HTML à la racine et dans <session>/, assets/css/styles.css, data/search-index.json,
           sitemap.xml, sw.js, 404.html, hors-ligne.html
Aucune dépendance hors bibliothèque standard.
"""
from __future__ import annotations

import datetime as dt
import html as htmlmod
import json
import pathlib
import posixpath
import re
import sys as _sys

for _flux in (_sys.stdout, _sys.stderr):   # la console Windows n'est pas en UTF-8 par défaut
    try:
        _flux.reconfigure(encoding='utf-8', errors='replace')
    except Exception:  # noqa: BLE001
        pass
import sys
import unicodedata
from collections import OrderedDict, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
DATA = ROOT / 'data'
SHELL = SRC / 'shell'

LENIENT = '--lenient' in sys.argv
CHECK = '--check' in sys.argv
BUILD_ID = dt.datetime.now().strftime('%Y-%m-%d.%H%M')
TODAY = dt.date.today().isoformat()

errors: list[str] = []
warnings: list[str] = []


def err(msg):
    (warnings if LENIENT else errors).append(msg)


def warn(msg):
    warnings.append(msg)


def load_json(path, default):
    p = pathlib.Path(path)
    if not p.exists():
        warn(f'fichier de données absent : {p.relative_to(ROOT)}')
        return default
    return json.loads(p.read_text(encoding='utf-8'))


site = load_json(SRC / 'site.json', {})
S = site['site']
GLOSS = load_json(DATA / 'glossaire.json', [])
REFS = load_json(DATA / 'references.json', [])
WIZARD = load_json(DATA / 'wizard.json', {})
RESSOURCES = load_json(DATA / 'ressources.json', {}) if (DATA / 'ressources.json').exists() else {}
GLOSS_BY_ID = {g['id']: g for g in GLOSS}
REFS_BY_KEY = {r['key']: r for r in REFS}
for _r in REFS:
    for _a in _r.get('aliases', []):
        REFS_BY_KEY.setdefault(_a, _r)

CSS_ORDER = ['fonts.css', 'tokens.css', 'base.css', 'layout.css', 'components.css', 'figures.css', 'print.css']
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr', 'path', 'circle', 'rect', 'line', 'polyline', 'polygon', 'ellipse', 'use', 'stop'}
NO_GLOSS_TAGS = {'h1', 'h2', 'h3', 'h4', 'a', 'button', 'figure', 'svg', 'code', 'pre', 'script', 'style', 'summary', 'label', 'option', 'title', 'desc'}
NO_GLOSS_CLASS = {'no-gloss', 'mhead', 'refs', 'say', 'cite-group', 'kicker', 'objectifs'}
TAG_RE = re.compile(r'<!--.*?-->|<[^>]+>|[^<]+', re.S)


# ------------------------------------------------------------------ utilitaires
def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def slugify(s):
    s = strip_accents(s).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:60] or 'section'


def strip_tags(s):
    return htmlmod.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s))).strip()


def esc(s):
    return htmlmod.escape(str(s), quote=True)


def rel(from_out, to_path):
    d = posixpath.dirname(from_out)
    return posixpath.relpath(to_path, d or '.')


def root_prefix(out):
    depth = len(pathlib.PurePosixPath(out).parts) - 1
    return '../' * depth


def fill(tpl, mapping):
    def sub(m):
        k = m.group(1)
        if k not in mapping:
            raise KeyError(f'placeholder inconnu {{{{{k}}}}}')
        return str(mapping[k])
    return re.sub(r'\{\{(\w+)\}\}', sub, tpl)


def read(path):
    return pathlib.Path(path).read_text(encoding='utf-8')


def write_if_changed(path, content):
    p = pathlib.Path(path)
    old = p.read_text(encoding='utf-8') if p.exists() else None
    if old == content:
        return False
    if CHECK:
        print(f'  DIFF {p.relative_to(ROOT)}')
        return True
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    return True


def tag_name(tok):
    m = re.match(r'</?\s*([a-zA-Z][\w:-]*)', tok)
    return m.group(1).lower() if m else ''


def tag_attr(tok, name):
    m = re.search(r'\s' + name + r'\s*=\s*"([^"]*)"', tok)
    if m:
        return m.group(1)
    m = re.search(r"\s" + name + r"\s*=\s*'([^']*)'", tok)
    return m.group(1) if m else None


def tag_has_attr(tok, name):
    return re.search(r'\s' + name + r'(\s|=|>|/)', tok) is not None


# ------------------------------------------------------------------ pages
def build_page_list():
    pages = []
    pages.append({'slug': 'index', 'type': 'hub', 'title': S['title'], 'description': S['description'],
                  'out': 'index.html', 'session': None, 'body': SRC / 'body' / 'index.html'})
    for sp in site.get('shared_pages', []):
        pages.append({**sp, 'session': None, 'body': SRC / 'body' / f'{sp["slug"]}-intro.html'})
    for sess in site['sessions']:
        seq = []
        for p in sess['pages']:
            out = f'{sess["slug"]}/{p["slug"]}.html'
            page = {**p, 'session': sess, 'out': out, 'body': SRC / 'body' / sess['slug'] / f'{p["slug"]}.html'}
            pages.append(page)
            seq.append(page)
        sess['_seq'] = seq
        for i, p in enumerate(seq):
            p['_prev'] = seq[i - 1] if i > 0 else None
            p['_next'] = seq[i + 1] if i + 1 < len(seq) else None
        sess['_modules'] = [p for p in seq if p['type'] == 'module']
        sess['_step_of'] = {}
        for st in sess['steps']:
            for m in st['modules']:
                sess['_step_of'][m] = st
    return pages


# ------------------------------------------------------------------ figures
FIG_ALIASES = load_json(SRC / 'figures' / 'aliases.json', {})
# Légende visible : une phrase. La description complète reste dans le <desc> du SVG, pour les lecteurs d'écran.
FIG_LEGENDES = load_json(DATA / 'legendes.json', {})
# Les six niveaux de preuve : une seule définition, rendue dans la légende et rappelée au clic sur une pastille.
NIVEAUX = load_json(DATA / 'niveaux-preuve.json', {})


def render_evidence_legend():
    lignes = ''.join(f'<div><span class="ev {c}">{esc(v["label"])}</span>{esc(v["def"])}</div>' for c, v in NIVEAUX.items())
    return f'<div class="legend" aria-label="Niveaux de preuve">{lignes}</div>'


def load_figure(name):
    name = FIG_ALIASES.get(name, name)
    for cand in (SRC / 'figures' / f'{name}.svg', SRC / 'figures' / 'gen' / f'{name}.svg'):
        if cand.exists():
            svg = read(cand).strip()
            txt = cand.with_suffix('.txt')
            title, desc = '', ''
            note, source = '', ''
            if txt.exists():
                lignes = read(txt).split('\n')
                title = lignes[0].strip() if lignes else ''
                desc = lignes[1].strip() if len(lignes) > 1 else ''
                note = lignes[2].strip() if len(lignes) > 2 else ''      # note de figure : mises en garde
                source = lignes[3].strip() if len(lignes) > 3 else ''    # d'où viennent les données
            svg = re.sub(r'<\?xml[^>]*>\s*', '', svg)
            if '<title' not in svg and title:
                tid = f'fig-{slugify(name)}-t'
                did = f'fig-{slugify(name)}-d'
                inject = f'<title id="{tid}">{esc(title)}</title>' + (f'<desc id="{did}">{esc(desc)}</desc>' if desc else '')
                svg = re.sub(r'(<svg\b[^>]*>)', lambda m: m.group(1) + inject, svg, count=1)
                labelled = f' aria-labelledby="{tid}{(" " + did) if desc else ""}"'
                svg = re.sub(r'<svg\b', '<svg role="img"' + labelled, svg, count=1)
            elif 'role=' not in svg[:200]:
                svg = re.sub(r'<svg\b', '<svg role="img"', svg, count=1)
            return svg, title, desc, note, source
    return None, '', '', '', ''


def expand_figures(body, page):
    """Chaque figure porte un numéro, un titre et une note, comme dans un mémoire.

    Le numéro court par page : on lit un module comme un document. L'appel « (Figure 3) »
    posé dans le texte par <a class="figref" data-fig="nom"> renvoie à la figure ; le numéro
    est résolu ici, après le comptage, pour qu'insérer une figure renumérote tout le reste.
    """
    numeros, ordre = {}, []

    def prochain(name):
        cle = FIG_ALIASES.get(name, name)
        if cle not in numeros:
            numeros[cle] = len(ordre) + 1
            ordre.append(cle)
        return numeros[cle]

    def bloc(name, classes, n, svg, title, visible, source=''):
        # Le bouton d'agrandissement se pose sur la ligne de légende, jamais sur le dessin.
        agrandir = ('<button type="button" class="fig-zoom" title="Agrandir" aria-label="Agrandir la figure ' + esc(title or str(n))
                    + '"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9V4h5M20 15v5h-5M4 15v5h5M20 9V4h-5"/></svg></button>')
        cap = (f'<figcaption class="fig-cap"><span class="fig-lib"><span class="fig-n">Figure&nbsp;{n}</span>'
               f'<span class="fig-t">{esc(title)}</span></span>{agrandir}</figcaption>') if title else ''
        # la source est portée par la figure : on ne doit pas avoir à la chercher dans le texte
        if not source and not re.search(r'(19|20)[0-9]{2}', visible or ''):
            err(f'{page["out"]} : la figure « {name} » n\'indique pas d\'où viennent ses données')
        src = f'<span class="fig-src">{esc(source if source.startswith("Schéma") else "Source : " + source)}</span>' if source else ''
        note = (f'<p class="fig-note"><span class="fig-note-l">Note.</span> {esc(visible)}{(" " + src) if src else ""}</p>'
                if (visible or src) else '')
        return (f'<figure class="fig {classes}" id="fig-{slugify(name)}" data-fig-n="{n}">{cap}'
                f'<div class="fig-box">{svg}{"" if title else agrandir}</div>{note}</figure>')

    def marker(m):
        name = m.group(1).strip()
        classes = (m.group(2) or '').strip()
        svg, title, desc, note_fig, source_fig = load_figure(name)
        if svg is None:
            err(f'{page["out"]} : figure introuvable « {name} »')
            return f'<!-- figure manquante : {name} -->'
        visible = FIG_LEGENDES.get(name) or FIG_LEGENDES.get(FIG_ALIASES.get(name, name)) or desc
        if note_fig:
            visible = (visible + ' ' + note_fig).strip()
        return bloc(name, classes, prochain(name), svg, title, visible, source_fig)
    body = re.sub(r'<!--\s*figure:\s*([\w./-]+)(?:\s+([\w\s-]+))?\s*-->', marker, body)

    def explicit(m):
        attrs, inner = m.group(1), m.group(2)
        name = tag_attr('<figure' + attrs + '>', 'data-figure')
        svg, title, desc, note_fig, source_fig = load_figure(name)
        if svg is None:
            err(f'{page["out"]} : figure introuvable « {name} »')
            return m.group(0)
        return f'<figure{attrs} data-fig-n="{prochain(name)}"><div class="fig-box">{svg}</div>{inner}</figure>'
    body = re.sub(r'<figure((?:\s[^>]*)?\sdata-figure="[^"]+"[^>]*)>(.*?)</figure>', explicit, body, flags=re.S)

    def appel(m):
        name = m.group(1).strip()
        cle = FIG_ALIASES.get(name, name)
        if cle not in numeros:
            err(f'{page["out"]} : appel « {name} » sans figure correspondante dans la page')
            return ''
        av = m.group(2) or ''
        libelle = f'Figure&nbsp;{numeros[cle]}'
        return f'<a class="figref" href="#fig-{slugify(name)}">{"voir la " + libelle.lower() if av == "voir" else libelle}</a>'
    body = re.sub(r'<a\s+class="figref"\s+data-fig="([\w./-]+)"(?:\s+data-forme="(\w+)")?\s*></a>', appel, body)
    return body


# ------------------------------------------------------------------ quiz / assistant / ressources / interactifs
def render_quiz(page):
    path = DATA / 'quiz' / f'{page["slug"]}.json'
    if not path.exists():
        err(f'{page["out"]} : quiz manquant ({path.relative_to(ROOT)})')
        return ''
    q = load_json(path, {})
    letters = 'ABCDEFGH'
    kinds = {'comprendre': 'Comprendre', 'appliquer': 'Appliquer', 'trancher': 'Trancher'}
    qs = q.get('questions', [])
    out = [f'<section class="quiz" id="quiz" aria-labelledby="quiz-h" data-quiz="{esc(page["slug"])}">',
           f'<h2 id="quiz-h">{esc(q.get("title", "Testez-vous"))}</h2>']
    if q.get('intro'):
        out.append(f'<p>{q["intro"]}</p>')
    out.append('<p class="qprog" id="qprog" aria-live="polite" hidden></p>')
    out.append('<noscript><style>.qz .fb{display:block}.qz .fb::before{content:"Réponse : ";font-weight:700}.qz .qo button .w{display:block}</style></noscript>')
    for i, it in enumerate(qs):
        kind = f'<span class="qk">{esc(kinds.get(it.get("kind", ""), ""))}</span>' if it.get('kind') in kinds else ''
        out.append(f'<div class="qz" data-q="{i}" data-a="{it["a"]}"><p class="qn">Question {i + 1} sur {len(qs)}{kind}</p><p class="qq">{it["q"]}</p><ul class="qo">')
        whys = it.get('why') or []
        for j, opt in enumerate(it['o']):
            w = f'<span class="w">{whys[j]}</span>' if j < len(whys) and whys[j] else ''
            out.append(f'<li><button type="button" data-i="{j}"><span class="l" aria-hidden="true">{letters[j]}</span><span class="ot">{opt}{w}</span></button></li>')
        sec = it.get('section') or ''
        link = f' <a href="#{esc(sec)}" class="qsec">Revoir la section</a>' if sec else ''
        out.append(f'</ul><div class="fb">{it["x"]}{link}</div></div>')
    out.append('<div class="score" id="score" aria-live="polite"></div>')
    out.append('<p class="wtools"><button type="button" class="lnk" data-quiz-reset hidden>Recommencer le quiz</button></p>')
    out.append('</section>')
    return chr(10).join(out)


def render_wizard(page):
    if not WIZARD:
        err(f'{page["out"]} : data/wizard.json absent')
        return ''
    start = WIZARD.get('start')
    nodes = WIZARD.get('nodes', {})
    out = [f'<div class="wiz" id="wiz" data-start="{esc(start)}" aria-label="Assistant de repérage">']
    if WIZARD.get('intro'):
        out.append(f'<p class="small">{WIZARD["intro"]}</p>')
    n = 0
    for key, node in nodes.items():
        if 'q' in node:
            n += 1
            out.append(f'<div class="wnode" id="w-{esc(key)}" data-node="{esc(key)}" data-label="Question {n}"><p class="wq">{node["q"]}</p><ul class="wo">')
            for label, nxt in node['o']:
                out.append(f'<li><a href="#w-{esc(nxt)}" data-next="{esc(nxt)}">{label}</a></li>')
            out.append('</ul></div>')
        else:
            urg = ' urg' if node.get('urg') else ''
            out.append(f'<div class="wnode" id="w-{esc(key)}" data-node="{esc(key)}" data-label="Conclusion"><div class="wout{urg}">{node["t"]}</div></div>')
    out.append('<p class="wtrail" id="wtrail" aria-live="polite"></p><div class="wtools"><button type="button" class="lnk" id="wreset" hidden>Recommencer</button></div></div>')
    return '\n'.join(out)


def render_ressources(key, page):
    grp = (RESSOURCES.get('groups') or {}).get(key)
    if not grp:
        err(f'{page["out"]} : groupe de ressources inconnu « {key} »')
        return ''
    conf_lbl = {'officiel': 'Source officielle', 'presse': 'Source de presse', 'a_confirmer': 'À confirmer'}
    out = [f'<div class="grid2 res-grid" data-res="{esc(key)}">']
    for it in grp.get('items', []):
        out.append('<div class="card res">')
        out.append(f'<h4>{esc(it["name"])}</h4>')
        if it.get('what'):
            out.append(f'<p>{it["what"]}</p>')
        if it.get('for'):
            out.append(f'<p class="small"><b>Pour qui :</b> {it["for"]}</p>')
        if it.get('contacts'):
            out.append('<ul class="contacts">')
            for c in it['contacts']:
                val = f'<a href="{esc(c["href"])}"{" target=_blank rel=noopener" if c["href"].startswith("http") else ""}>{esc(c["value"])}</a>' if c.get('href') else esc(c['value'])
                conf = c.get('confidence')
                badge = f' <span class="ev ev-{ {"officiel": "est", "presse": "low", "a_confirmer": "gap"}.get(conf, "gap") }">{conf_lbl.get(conf, conf)}</span>' if conf else ''
                out.append(f'<li><b>{esc(c["label"])} :</b> {val}{badge}</li>')
            out.append('</ul>')
        if it.get('note'):
            out.append(f'<p class="small">{it["note"]}</p>')
        if it.get('source_html'):
            out.append(f'<p class="small muted">{it["source_html"]}</p>')
        out.append('</div>')
    out.append('</div>')
    return '\n'.join(out)


def render_sort(key, page):
    d = load_json(DATA / 'interactifs' / f'sort-{key}.json', None)
    if not d:
        err(f'{page["out"]} : tri interactif inconnu « {key} »')
        return ''
    out = [f'<div class="sort" data-sort="{esc(key)}">']
    if d.get('intro'):
        out.append(f'<p>{d["intro"]}</p>')
    for i, it in enumerate(d['items']):
        out.append(f'<div class="item" data-a="{it["a"]}"><p class="sit">{i + 1}. {it["sit"]}</p><div class="opts">')
        for j, o in enumerate(d['options']):
            out.append(f'<button type="button" data-i="{j}">{esc(o)}</button>')
        crit = it.get('crit')
        segs = ''
        if crit:
            segs = '<div class="segs" aria-hidden="true">' + ''.join(f'<div data-on="{str(bool(crit.get(k))).lower()}">{lbl}<i></i></div>' for k, lbl in (('rep', 'Répétition'), ('pow', 'Rapport de force'), ('ret', 'Retentissement'))) + '</div>'
        out.append(f'</div>{segs}<div class="why"><b>Réponse : {esc(d["options"][it["a"]])}.</b> {it["why"]}</div></div>')
    out.append('<noscript><style>.sort .why{display:block}</style></noscript></div>')
    return '\n'.join(out)


def render_simulator(key, page):
    d = load_json(DATA / 'interactifs' / f'sim-{key}.json', None)
    if not d:
        err(f'{page["out"]} : simulateur inconnu « {key} »')
        return ''
    out = [f'<div class="wiz sim" data-sim="{esc(key)}">']
    if d.get('intro'):
        out.append(f'<p class="small">{d["intro"]}</p>')
    for i, t in enumerate(d['turns']):
        out.append(f'<div class="wnode" data-turn="{i}" data-label="Tour {i + 1}"><p class="wq">{t["prompt"]}</p><ul class="wo">')
        for j, c in enumerate(t['choices']):
            out.append(f'<li><button type="button" data-c="{j}" data-good="{str(bool(c.get("good"))).lower()}">{c["text"]}</button></li>')
        out.append('</ul><div class="reactions">')
        for j, c in enumerate(t['choices']):
            out.append(f'<div class="wout{"" if c.get("good") else " urg"}" data-r="{j}" hidden><b>{esc(c["text"])}</b> — {c["reaction"]}</div>')
        out.append('</div></div>')
    out.append(f'<div class="wnode" data-turn="end" data-label="Bilan"><div class="wout">{d.get("end", "")}</div></div>')
    out.append('<div class="wtools"><button type="button" class="lnk" data-sim-reset hidden>Recommencer</button></div></div>')
    return '\n'.join(out)


def render_compare(key, page):
    d = load_json(DATA / 'interactifs' / f'compare-{key}.json', None)
    if not d:
        err(f'{page["out"]} : comparateur inconnu « {key} »')
        return ''
    cols = d['columns']
    out = [f'<div class="tw" data-compare="{esc(key)}"><table><thead><tr><th>{esc(d.get("row_label", ""))}</th>']
    out += [f'<th>{esc(c)}</th>' for c in cols]
    out.append('</tr></thead><tbody>')
    for r in d['rows']:
        out.append(f'<tr><td>{r["label"]}</td>' + ''.join(f'<td>{v}</td>' for v in r['values']) + '</tr>')
    out.append('</tbody></table></div>')
    return '\n'.join(out)


def expand_markers(body, page):
    body = re.sub(r'<!--\s*include:\s*evidence-legend\s*-->', lambda m: render_evidence_legend(), body)
    body = re.sub(r'<!--\s*include:\s*([\w-]+)\s*-->', lambda m: read(SHELL / 'partials' / f'{m.group(1)}.html').strip(), body)
    body = expand_figures(body, page)
    body = re.sub(r'<!--\s*quiz\s*-->', lambda m: render_quiz(page), body)
    body = re.sub(r'<!--\s*wizard\s*-->', lambda m: render_wizard(page), body)
    body = re.sub(r'<!--\s*ressources:\s*([\w-]+)\s*-->', lambda m: render_ressources(m.group(1), page), body)
    body = re.sub(r'<!--\s*sort:\s*([\w-]+)\s*-->', lambda m: render_sort(m.group(1), page), body)
    body = re.sub(r'<!--\s*simulator:\s*([\w-]+)\s*-->', lambda m: render_simulator(m.group(1), page), body)
    body = re.sub(r'<!--\s*compare:\s*([\w-]+)\s*-->', lambda m: render_compare(m.group(1), page), body)
    body = body.replace('<!-- pagenav -->', render_pagenav(page))
    return body


# ------------------------------------------------------------------ citations
def short_cite(r):
    suf = r.get('suffixe', '') or ''
    return f'{r["auteurs_court"]}, {r["annee"]}{suf}'


def expand_citations(body, page):
    used = OrderedDict()

    def sub(m):
        keys = [k.strip() for k in m.group(1).split(',') if k.strip()]
        narrative = m.group(2) is not None
        parts = []
        for k in keys:
            r = REFS_BY_KEY.get(k)
            if not r:
                err(f'{page["out"]} : référence inconnue « {k} »')
                parts.append(f'<span class="cite-missing">[{esc(k)}]</span>')
                continue
            used[k] = r
            if narrative:
                parts.append(f'<a class="cite" href="#ref-{esc(k)}" data-ref="{esc(k)}">{esc(r["auteurs_court"])} ({esc(r["annee"])}{esc(r.get("suffixe") or "")})</a>')
            else:
                parts.append(f'<a class="cite" href="#ref-{esc(k)}" data-ref="{esc(k)}">{esc(short_cite(r))}</a>')
        if narrative:
            return ' ; '.join(parts)
        return '<span class="cite-group">(' + ' ; '.join(parts) + ')</span>'
    body = re.sub(r'<a class="cite" data-ref="([^"]+)"(\s+data-narrative)?\s*>\s*</a>', sub, body)
    leftovers = re.findall(r'<a class="cite"[^>]*>(?!</a>)', body)
    return body, used


# ------------------------------------------------------------------ glossaire
def term_patterns():
    pats = []
    for g in GLOSS:
        forms = [g['terme']] + list(g.get('variantes', []))
        forms = [f for f in forms if f and len(f) > 2]
        if not forms:
            continue
        forms.sort(key=len, reverse=True)
        alt = '|'.join(re.escape(f) for f in forms)
        rx = re.compile(r'(?<![\w-])(' + alt + r')(s|x)?(?![\w-])', re.IGNORECASE)
        pats.append((max(len(f) for f in forms), g['id'], rx))
    pats.sort(key=lambda t: -t[0])
    return pats


PATTERNS = term_patterns()


def glossary_href(page, gid):
    return rel(page['out'], 'glossaire.html') + '#' + gid


def link_terms(body, page):
    """Lie la première occurrence de chaque terme du glossaire dans chaque section h2."""
    if not PATTERNS:
        return body, {}
    toks = TAG_RE.findall(body)
    out = []
    stack = []          # (tag, skip)
    skip_depth = 0
    section = 0
    seen = defaultdict(set)   # section -> ids
    used = {}                 # id -> first section
    # pré-repérage des termes marqués à la main par section
    sec = 0
    for tok in toks:
        if tok.startswith('<h2'):
            sec += 1
        if tok.startswith('<a ') and 'class="term"' in tok:
            t = tag_attr(tok, 'data-term')
            if t:
                seen[sec].add(t)
    section = 0
    for tok in toks:
        if tok.startswith('<!--'):
            out.append(tok)
            continue
        if tok.startswith('<'):
            name = tag_name(tok)
            if tok.startswith('</'):
                while stack:
                    t, sk = stack.pop()
                    if sk:
                        skip_depth -= 1
                    if t == name:
                        break
                out.append(tok)
                continue
            if name == 'h2':
                section += 1
            if name == 'a' and 'class="term"' in tok:
                gid = tag_attr(tok, 'data-term')
                g = GLOSS_BY_ID.get(gid)
                if not g:
                    err(f'{page["out"]} : terme de glossaire inconnu « {gid} »')
                else:
                    used.setdefault(gid, section)
                    tok = f'<a class="term" href="{glossary_href(page, gid)}" data-term="{esc(gid)}" data-def="{esc(g["court"])}">'
            self_closing = tok.endswith('/>') or name in VOID
            cls = (tag_attr(tok, 'class') or '').split()
            skip = name in NO_GLOSS_TAGS or bool(set(cls) & NO_GLOSS_CLASS) or tag_has_attr(tok, 'data-noterm') or (tag_attr(tok, 'lang') or '') == 'mg'
            if not self_closing:
                stack.append((name, skip))
                if skip:
                    skip_depth += 1
            out.append(tok)
            continue
        # texte
        if skip_depth or not tok.strip():
            out.append(tok)
            continue
        pieces = [(tok, True)]
        for _, gid, rx in PATTERNS:
            if gid in seen[section]:
                continue
            for idx, (txt, linkable) in enumerate(pieces):
                if not linkable:
                    continue
                m = rx.search(txt)
                if not m:
                    continue
                g = GLOSS_BY_ID[gid]
                a = f'<a class="term" href="{glossary_href(page, gid)}" data-term="{esc(gid)}" data-def="{esc(g["court"])}">{m.group(0)}</a>'
                pieces[idx:idx + 1] = [(txt[:m.start()], True), (a, False), (txt[m.end():], True)]
                seen[section].add(gid)
                used.setdefault(gid, section)
                break
        out.append(''.join(p for p, _ in pieces))
    return ''.join(out), used


# ------------------------------------------------------------------ sections, références, validations
def collect_h2(body, page):
    h2s = []
    for m in re.finditer(r'<h2([^>]*)>(.*?)</h2>', body, re.S):
        attrs, inner = m.group(1), m.group(2)
        hid = tag_attr('<h2' + attrs + '>', 'id')
        if not hid:
            err(f'{page["out"]} : h2 sans id « {strip_tags(inner)[:50]} »')
            hid = slugify(strip_tags(inner))
        h2s.append((hid, strip_tags(inner)))
    return h2s


def render_refs_section(used):
    if not used:
        return ''
    items = sorted(used.values(), key=lambda r: strip_accents(strip_tags(r['apa7'])).lower())
    out = ['<section class="refs" id="references" aria-labelledby="refs-h"><h2 id="refs-h">Références</h2>',
           '<p class="small">Références citées dans cette page. Toute la bibliographie est réunie sur la <a href="__REFS__">page Bibliographie</a>.</p>',
           '<ol class="reflist">']
    for r in items:
        out.append(render_ref_li(r))
    out.append('</ol></section>')
    return '\n'.join(out)


TAG_CLASS = {'Presse': 'press', 'Institution': 'inst', 'ONG': 'ong', 'Prépublication': 'pre', 'Méta-analyse': 'meta', 'Juridique': 'inst'}


def render_ref_li(r, extra=''):
    url = r.get('url', '')
    link = f' <a href="{esc(url)}" target="_blank" rel="noopener">{esc(url)}</a>' if url else ''
    tag = f' <span class="tag {TAG_CLASS.get(r["etiquette"], "inst")}">{esc(r["etiquette"])}</span>' if r.get('etiquette') else ''
    return f'<li id="ref-{esc(r["key"])}">{r["apa7"]}{link}{tag}{extra}</li>'


def word_count(html_fragment):
    return len(strip_tags(html_fragment).split())


def validate_body(page, body):
    if re.search(r'<details\b', body):
        err(f'{page["out"]} : accordéon <details> interdit')
    if re.search(r'lire plus|voir plus|en savoir plus', body, re.I):
        err(f'{page["out"]} : mention « lire plus / voir plus / en savoir plus » interdite')
    for name in S.get('forbidden_names', []):
        if name.lower() in body.lower():
            err(f'{page["out"]} : nom proscrit « {name} »')
    if re.search(r'<[^>]+\sstyle="', body) and page['type'] != 'hub':
        err(f'{page["out"]} : attribut style inline interdit dans un corps de page')
    if re.search(r'<script\b', body) and 'application/json' not in body:
        err(f'{page["out"]} : script inline interdit dans un corps de page')
    if page['type'] == 'module':
        if 'class="box retenir"' not in body and 'class="retenir' not in body:
            err(f'{page["out"]} : encadré « Ce que je retiens » (.retenir) absent')
        if '<!-- quiz -->' not in body and 'class="quiz"' not in body:
            err(f'{page["out"]} : quiz absent')
        deep = sum(word_count(m) for m in re.findall(r'<aside class="deep"[^>]*>(.*?)</aside>', body, re.S))
        total = word_count(body)
        if total and deep / total > 0.40:
            err(f'{page["out"]} : encadrés Approfondir = {deep / total:.0%} des mots (> 40 %)')
    for m in re.finditer(r'href="([^"#]+)(#[^"]*)?"', body):
        href = m.group(1)
        if href.startswith(('http://', 'https://', 'mailto:', 'tel:')):
            continue
        target = posixpath.normpath(posixpath.join(posixpath.dirname(page['out']), href))
        if not (ROOT / target).exists() and not any(target == p['out'] for p in ALL_PAGES):
            err(f'{page["out"]} : lien interne cassé « {href} »')


# ------------------------------------------------------------------ coquille
def render_rail(page):
    sess = page['session']
    if not sess:
        return ''
    out = [f'<nav class="rail" id="rail" aria-label="Sommaire de la session">',
           f'<div class="rail-head"><a href="{rel(page["out"], sess["slug"] + "/index.html")}">{esc(sess["title"])}<small>{esc(sess["date_label"])}</small></a></div>',
           '<ol class="rail-steps">']
    for st in sess['steps']:
        out.append(f'<li class="rail-step"><div class="step-title"><span class="step-key">{esc(st["key"])}</span><span>{esc(st["title"])}</span></div><ol>')
        for slug in st['modules']:
            m = next(p for p in sess['_seq'] if p['slug'] == slug)
            cur = ' cur' if m['slug'] == page['slug'] else ''
            aria = ' aria-current="page"' if cur else ''
            out.append(f'<li><a class="mod{cur}" href="{rel(page["out"], m["out"])}" data-page="{esc(m["out"])}"{aria}><span class="n">{m["num"]}</span><span>{esc(m["short"])}</span></a></li>')
        out.append('</ol></li>')
    out.append('</ol>')
    if page.get('_h2s'):
        out.append('<div class="rail-toc" id="toc"><p class="toc-h">Dans cette page</p><ol>')
        for hid, txt in page['_h2s']:
            out.append(f'<li><a href="#{esc(hid)}">{esc(txt)}</a></li>')
        out.append('</ol></div>')
    n = len(sess['_modules'])
    pos = f'Module {page["num"]} sur {n}' if page['type'] == 'module' else esc(page['title'])
    out.append(f'<div class="rail-foot"><div id="ptxt" aria-live="polite">{pos}</div><div class="pbar"><i id="pfill"></i></div><div id="pdone">0 module consulté</div>')
    links = [(rel(page['out'], f'{sess["slug"]}/index.html'), 'Sommaire'), (rel(page['out'], 'glossaire.html'), 'Glossaire'), (rel(page['out'], 'references.html'), 'Bibliographie'),
             (rel(page['out'], f'{sess["slug"]}/methode-et-limites.html'), 'Méthode et limites'), (rel(page['out'], f'{sess["slug"]}/ethique-et-confidentialite.html'), 'Éthique')]
    out.append('<div class="rail-links">' + ''.join(f'<a href="{h}">{t}</a>' for h, t in links) + '</div></div></nav>')
    return '\n'.join(out)


def render_crumb(page):
    if page['type'] == 'hub':
        return ''
    items = [(rel(page['out'], 'index.html'), 'Accueil')]
    sess = page['session']
    if sess:
        if page['type'] == 'session-index':
            items.append((None, sess['short_title']))
        else:
            items.append((rel(page['out'], f'{sess["slug"]}/index.html'), sess['short_title']))
            if page['type'] == 'module':
                st = sess['_step_of'].get(page['slug'])
                if st:
                    items.append((rel(page['out'], f'{sess["slug"]}/index.html') + f'#etape-{st["key"].lower()}', f'Étape {st["key"]} · {st["title"]}'))
                items.append((None, f'Module {page["num"]}'))
            else:
                items.append((None, page['title']))
    else:
        items.append((None, page['title']))
    parts = []
    for i, (href, label) in enumerate(items):
        if i:
            parts.append('<span class="sep" aria-hidden="true">›</span>')
        parts.append(f'<a href="{href}">{esc(label)}</a>' if href else f'<span aria-current="page">{esc(label)}</span>')
    return '<nav class="crumb" aria-label="Fil d\'Ariane">' + ''.join(parts) + '</nav>'


def page_label(p):
    if p['type'] == 'module':
        return f'Module {p["num"]}'
    if p['type'] == 'session-index':
        return 'Sommaire'
    return 'Page'


def render_pager(page):
    prev, nxt = page.get('_prev'), page.get('_next')
    if not (prev or nxt):
        return ''
    out = ['<nav class="pager" aria-label="Navigation entre les pages">']
    if prev:
        out.append(f'<a class="prev" href="{rel(page["out"], prev["out"])}" rel="prev"><small>← Précédent · {esc(page_label(prev))}</small><span class="pt">{esc(prev["title"])}</span></a>')
    if nxt:
        out.append(f'<a class="next" href="{rel(page["out"], nxt["out"])}" rel="next"><small>Suivant · {esc(page_label(nxt))} →</small><span class="pt">{esc(nxt["title"])}</span></a>')
    out.append('</nav>')
    return '\n'.join(out)


def bottom_link(page, target, kind):
    ico = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg>' if kind == 'prev' else '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>'
    label = 'Précédent' if kind == 'prev' else 'Suivant'
    if not target:
        return f'<a href="#" aria-disabled="true" tabindex="-1">{ico}{label}</a>'
    return f'<a href="{rel(page["out"], target["out"])}" rel="{kind}">{ico}{label}</a>'


def shared_links(page):
    """Les pages partagées, dans l'ordre où on les cherche."""
    s = (page['session'] or site['sessions'][0])['slug']
    return [('index.html', 'Accueil'), (f'{s}/index.html', 'Sommaire de la session'),
            ('glossaire.html', 'Glossaire'), ('references.html', 'Bibliographie'),
            (f'{s}/methode-et-limites.html', 'Méthode et limites'),
            (f'{s}/ethique-et-confidentialite.html', 'Éthique et confidentialité')]


def nav_items(page):
    out = []
    for target, label in shared_links(page):
        cur = ' aria-current="page"' if target == page['out'] else ''
        out.append(f'<li><a href="{rel(page["out"], target)}"{cur}>{esc(label)}</a></li>')
    return ''.join(out)


def footer_links(page):
    return nav_items(page)


def render_pagenav(page):
    """Barre de pages : la seule navigation de l'accueil, qui n'a pas de rail."""
    return f'<nav class="pagenav" aria-label="Pages du site"><ul class="links">{nav_items(page)}</ul></nav>'


def title_tag(page):
    parts = [page['title']]
    if page['session'] and page['type'] != 'session-index':
        parts.append(page['session']['short_title'])
    if page['type'] != 'hub':
        parts.append(S['title'])
    return ' · '.join(parts)


def fix_heading_order(html_fragment):
    """Aucun saut de niveau de titre (h2 -> h4) : un titre trop profond est remonté au niveau suivant du précédent."""
    state = {'prev': 1}

    def sub(m):
        level = int(m.group(1))
        if level > state['prev'] + 1:
            level = state['prev'] + 1
        state['prev'] = level
        return f'<h{level}{m.group(2)}>{m.group(3)}</h{level}>'
    return re.sub(r'<h([1-6])\b([^>]*)>(.*?)</h\1>', sub, html_fragment, flags=re.S)


def wrap(page, content, refs_used, gloss_used):
    content = fix_heading_order(content)
    root = root_prefix(page['out'])
    body_class = f'page-{page["type"]}' + ('' if page['session'] else ' no-rail') + (' has-margin' if page['type'] in ('module', 'page') else '')
    head = fill(read(SHELL / 'head.html'), {
        'slug': page['slug'], 'session': page['session']['slug'] if page['session'] else '', 'type': page['type'],
        'title_tag': esc(title_tag(page)), 'description': esc(page['description']), 'author_short': esc(S['author_short']),
        'canonical': S['base_url'] + '/' + ('' if page['out'] == 'index.html' else page['out']), 'site_title': esc(S['title']),
        'theme_light': S['theme_color_light'], 'theme_dark': S['theme_color_dark'], 'root': root, 'build_id': BUILD_ID, 'body_class': body_class,
    })
    header = fill(read(SHELL / 'header.html'), {'root': root, 'site_title': esc(S['title']), 'site_short': esc(S['short_title']), 'brand_sub': esc(page['session']['short_title'] if page['session'] else 'Outils pédagogiques')})
    refs_json = json.dumps({k: {'apa': r['apa7'], 'url': r.get('url', ''), 'short': short_cite(r)} for k, r in refs_used.items()}, ensure_ascii=False)
    def gloss_source(g):
        src = dict(g.get('source') or {})
        r = REFS_BY_KEY.get(src.get('refId'))
        if r:
            src['citation'] = short_cite(r)
            src['refId'] = r['key']
        return src

    gloss_json = json.dumps({gid: {'terme': GLOSS_BY_ID[gid]['terme'], 'categorie': GLOSS_BY_ID[gid].get('categorie', ''), 'court': GLOSS_BY_ID[gid]['court'], 'long': GLOSS_BY_ID[gid].get('long', ''),
                                   'source': gloss_source(GLOSS_BY_ID[gid]), 'liens': GLOSS_BY_ID[gid].get('liens', []), 'voirAussi': GLOSS_BY_ID[gid].get('voirAussi', [])}
                             for gid in gloss_used if gid in GLOSS_BY_ID}, ensure_ascii=False)
    footer = fill(read(SHELL / 'footer.html'), {
        'author': esc(S['author']), 'license_url': S['license']['url'], 'license_name': S['license']['name'], 'footer_links': footer_links(page),
        'repo_url': S['repo_url'], 'build_id': BUILD_ID, 'root': root,
        'bottom_prev': bottom_link(page, page.get('_prev'), 'prev'), 'bottom_next': bottom_link(page, page.get('_next'), 'next'),
        'ev_json': (json.dumps(NIVEAUX, ensure_ascii=False) if 'class="ev ev-' in content else '{}').replace('</', '<\/'),
        'methode_url': root + ((page['session'] or site['sessions'][0])['slug'] + '/methode-et-limites.html'),
        'refs_json': refs_json.replace('</', '<\\/'), 'gloss_json': gloss_json.replace('</', '<\\/'),
    })
    main = ['<main id="main" class="main">', render_crumb(page), f'<article class="page{" has-margin" if page["type"] in ("module", "page") else ""}{" page--wide" if page["type"] in ("glossaire", "references", "session-index", "hub") else ""}">', content, '</article>', render_pager(page), '</main>']
    return head + header + render_rail(page) + '\n'.join(main) + footer


# ------------------------------------------------------------------ pages générées : glossaire, bibliographie
def render_glossary_page(page, term_usage):
    root = root_prefix(page['out'])
    intro = read(page['body']) if page['body'].exists() else ''
    entries = sorted(GLOSS, key=lambda g: strip_accents(g['terme']).lower())
    letters = OrderedDict()
    for g in entries:
        first = strip_accents(g['terme'])[0].upper()
        letters.setdefault(first, []).append(g)
    all_letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    out = [f'<header class="mhead"><p class="kicker">{esc(S["title"])}</p><h1>Glossaire</h1><p class="lead">{esc(page["description"])}</p></header>',
           '<div class="backbar" id="backbar" hidden><a href="#" id="backlink">← Retour à votre lecture</a><button type="button" class="x" id="backx" aria-label="Masquer">×</button></div>',
           intro,
           '<nav class="gl-nav" aria-label="Lettres">' + ''.join(f'<a href="#lettre-{L}"{"" if L in letters else " class=off aria-disabled=true"}>{L}</a>' for L in all_letters) + '</nav>']
    if not GLOSS:
        out.append('<p class="muted">Le glossaire est en cours de constitution.</p>')
    for L, items in letters.items():
        out.append(f'<h2 class="gl-letter" id="lettre-{L}">{L}</h2>')
        for g in items:
            src = g.get('source') or {}
            src_html = ''
            if src.get('refId') and src['refId'] in REFS_BY_KEY:
                r = REFS_BY_KEY[src['refId']]
                src_html = f'<p class="src small">Source : <a class="cite" href="{root}references.html#ref-{esc(r["key"])}" data-ref="{esc(r["key"])}">{esc(short_cite(r))}</a></p>'
            elif src.get('texte'):
                src_html = f'<p class="src small">Source : {src["texte"]}</p>'
            links = ''.join(f'<a href="{esc(l["url"])}" target="_blank" rel="noopener">{esc(l["label"])}</a>' for l in g.get('liens', []))
            also = ''
            if g.get('voirAussi'):
                also = '<p class="also">Voir aussi : ' + ', '.join(f'<a href="#{esc(v)}">{esc(GLOSS_BY_ID[v]["terme"])}</a>' for v in g['voirAussi'] if v in GLOSS_BY_ID) + '</p>'
            used = ''
            if term_usage.get(g['id']):
                refs = sorted(term_usage[g['id']], key=lambda t: t[0])
                used = '<p class="used">Utilisé dans : ' + ' · '.join(f'<a href="{rel(page["out"], o)}#{hid}">{esc(lbl)}</a>' for o, lbl, hid in refs) + '</p>'
            cat = f'<span class="cat">{esc(g["categorie"])}</span>' if g.get('categorie') else ''
            variants = f'<p class="small muted">Aussi : {esc(", ".join(g["variantes"]))}</p>' if g.get('variantes') else ''
            out.append(f'<article class="gl-entry" id="{esc(g["id"])}">{cat}<h3>{esc(g["terme"])}</h3><p class="short">{esc(g["court"])}</p>{g.get("long", "")}{variants}{src_html}<div class="ext">{links}</div>{also}{used}</article>')
    refs_used = OrderedDict()
    for g in GLOSS:
        src = g.get('source') or {}
        if src.get('refId') in REFS_BY_KEY:
            refs_used[src['refId']] = REFS_BY_KEY[src['refId']]
    return '\n'.join(out), refs_used


def render_references_page(page, ref_usage):
    intro = read(page['body']) if page['body'].exists() else ''
    types = OrderedDict()
    for r in REFS:
        types.setdefault(r.get('type', 'autre'), 0)
        types[r.get('type', 'autre')] += 1
    chips = '<ul class="chips" data-ref-filter><li><button type="button" class="chip" data-type="" aria-pressed="true">Toutes (' + str(len(REFS)) + ')</button></li>' + ''.join(
        f'<li><button type="button" class="chip" data-type="{esc(t)}" aria-pressed="false">{esc(t)} ({n})</button></li>' for t, n in sorted(types.items())) + '</ul>'
    out = [f'<header class="mhead"><p class="kicker">{esc(S["title"])}</p><h1>Bibliographie</h1><p class="lead">{esc(page["description"])}</p></header>',
           '<div class="backbar" id="backbar" hidden><a href="#" id="backlink">← Retour au texte</a><button type="button" class="x" id="backx" aria-label="Masquer">×</button></div>',
           intro, f'<p class="small">{len(REFS)} références.</p>', chips,
           '<div class="search" id="refsearch"><input type="search" id="refq" placeholder="Filtrer par auteur, année, titre…" aria-label="Filtrer la bibliographie" autocomplete="off"></div>',
           '<ol class="reflist" id="reflist">']
    for r in sorted(REFS, key=lambda r: strip_accents(strip_tags(r['apa7'])).lower()):
        cited = ''
        if ref_usage.get(r['key']):
            cited = '<span class="cited">Cité dans : ' + ' · '.join(f'<a href="{rel(page["out"], o)}#ref-{esc(r["key"])}">{esc(lbl)}</a>' for o, lbl in sorted(ref_usage[r['key']])) + '</span>'
        ver = ''   # la date de vérification est une information de fabrication : le lecteur ouvre le lien lui-même
        li = render_ref_li(r, cited + ver)
        li = li.replace('<li ', f'<li data-type="{esc(r.get("type", "autre"))}" data-search="{esc(strip_accents(strip_tags(r["apa7"])).lower())}" ', 1)
        out.append(li)
    out.append('</ol>')
    return '\n'.join(out)


def render_session_toc(sess, page, visited_attr=True):
    out = ['<ol class="toc-steps">']
    for st in sess['steps']:
        out.append(f'<li class="toc-step" id="etape-{st["key"].lower()}"><div class="st"><span class="step-key">{esc(st["key"])}</span><h3>{esc(st["title"])}</h3></div><ol>')
        for slug in st['modules']:
            m = next(p for p in sess['_seq'] if p['slug'] == slug)
            out.append(f'<li><a href="{rel(page["out"], m["out"])}" data-page="{esc(m["out"])}"><span class="n">{m["num"]}</span><span class="tt">{esc(m["title"])}<span class="td">{esc(m["description"])}</span></span></a></li>')
        out.append('</ol></li>')
    out.append('</ol>')
    return '\n'.join(out)


def render_session_cards(page):
    out = []
    for sess in site['sessions']:
        n = len(sess['_modules'])
        out.append(f'<a class="session-card plain" href="{rel(page["out"], sess["slug"] + "/index.html")}"><span class="date">{esc(sess["date_label"])}</span><h2 id="session-{esc(sess["slug"])}">{esc(sess["title"])}</h2><p>{esc(sess["description"])}</p><span class="meta"><span>{n} modules en {len(sess["steps"])} étapes</span><span class="go">Ouvrir le sommaire →</span></span></a>')
    return '\n'.join(out)


# ------------------------------------------------------------------ index de recherche
BLOCK_TAGS = {'p', 'li', 'td', 'th', 'dt', 'dd', 'h2', 'h3', 'h4', 'figcaption', 'blockquote'}


def index_page(page, content, index):
    toks = TAG_RE.findall(content)
    stack = []
    cur_sec = ('', page['title'])
    buf = None
    depth_skip = 0
    for tok in toks:
        if tok.startswith('<!--'):
            continue
        if tok.startswith('<'):
            name = tag_name(tok)
            if tok.startswith('</'):
                if stack and stack[-1][0] == name and stack[-1][1]:
                    txt = re.sub(r'\s+', ' ', htmlmod.unescape(buf or '')).strip()
                    if len(txt) > 20:
                        index.append({'p': page['out'], 't': page['title'], 's': cur_sec[0], 'sh': cur_sec[1], 'x': txt[:600]})
                    buf = None
                if stack and stack[-1][0] == name:
                    if stack[-1][2]:
                        depth_skip -= 1
                    stack.pop()
                continue
            if name == 'h2':
                cur_sec = (tag_attr(tok, 'id') or '', '')
            skip = name in ('script', 'style', 'svg', 'nav', 'button') or 'class="refs"' in tok or 'class="quiz"' in tok
            self_closing = tok.endswith('/>') or name in VOID
            if not self_closing:
                is_block = name in BLOCK_TAGS and buf is None and not depth_skip
                stack.append((name, is_block, skip))
                if skip:
                    depth_skip += 1
                if is_block:
                    buf = ''
            continue
        if buf is not None and not depth_skip:
            buf += tok
            if cur_sec[1] == '' and stack and stack[-1][0] == 'h2':
                cur_sec = (cur_sec[0], htmlmod.unescape(tok).strip())


def group_index(flat):
    """Regroupe l'index plat par page puis par section (p, t, s, sh ne sont plus répétés à chaque bloc)."""
    pages = []
    for it in flat:
        if not pages or pages[-1]['p'] != it['p']:
            pages.append({'p': it['p'], 't': it['t'], 'secs': []})
        secs = pages[-1]['secs']
        if not secs or secs[-1]['s'] != it['s'] or secs[-1]['sh'] != it['sh']:
            secs.append({'s': it['s'], 'sh': it['sh'], 'x': []})
        secs[-1]['x'].append(it['x'])
    return pages


# ------------------------------------------------------------------ construction
ALL_PAGES = build_page_list()


def main():
    print(f'Build {BUILD_ID}' + (' (lenient)' if LENIENT else '') + (' (check)' if CHECK else ''))
    term_usage = defaultdict(set)
    ref_usage = defaultdict(set)
    search_index = []
    rendered = {}
    generated_outs = []

    # 1) corps des pages de session et hub
    for page in ALL_PAGES:
        if page['type'] in ('glossaire', 'references'):
            continue
        if not page['body'].exists():
            err(f'{page["out"]} : corps introuvable ({page["body"].relative_to(ROOT)})')
            body = f'<header class="mhead"><h1>{esc(page["title"])}</h1><p class="lead">{esc(page["description"])}</p></header><p class="muted">Page en cours de rédaction.</p>'
        else:
            body = read(page['body'])
        body = expand_markers(body, page)
        if page['type'] == 'hub':
            body = body.replace('<!-- sessions -->', render_session_cards(page))
        if page['type'] == 'session-index':
            body = body.replace('<!-- session-toc -->', render_session_toc(page['session'], page))
        validate_body(page, body)
        body, refs_used = expand_citations(body, page)
        body, gloss_used = link_terms(body, page)
        h2s = collect_h2(body, page)
        page['_h2s'] = h2s
        if refs_used:
            body += '\n' + render_refs_section(refs_used).replace('__REFS__', rel(page['out'], 'references.html'))
        label = f'Module {page["num"]} · {page["short"]}' if page['type'] == 'module' else page['title']
        for gid, sec in gloss_used.items():
            hid = h2s[sec - 1][0] if 0 < sec <= len(h2s) else ''
            term_usage[gid].add((page['out'], label, hid))
        for k in refs_used:
            ref_usage[k].add((page['out'], label))
        index_page(page, body, search_index)
        rendered[page['out']] = wrap(page, body, refs_used, gloss_used)
        generated_outs.append(page['out'])

    # 2) glossaire et bibliographie
    for page in ALL_PAGES:
        if page['type'] == 'glossaire':
            body, refs_used = render_glossary_page(page, term_usage)
            page['_h2s'] = []
            rendered[page['out']] = wrap(page, body, refs_used, {})
        elif page['type'] == 'references':
            body = render_references_page(page, ref_usage)
            page['_h2s'] = []
            rendered[page['out']] = wrap(page, body, OrderedDict(), {})
        else:
            continue
        index_page(page, body, search_index)
        generated_outs.append(page['out'])

    # 3) validations globales
    for g in GLOSS:
        if not (g.get('source') or {}).get('refId') and not (g.get('source') or {}).get('texte'):
            err(f'glossaire : « {g["terme"]} » sans source')
        if not g.get('liens'):
            err(f'glossaire : « {g["terme"]} » sans lien externe')
        if len(g.get('court', '')) > 220:
            err(f'glossaire : définition courte trop longue pour « {g["terme"]} » ({len(g["court"])} caractères)')
    for r in REFS:
        if not r.get('url'):
            err(f'références : « {r["key"]} » sans URL')

    if errors:
        print('\nERREURS :')
        for e in errors:
            print('  ✗', e)
        print(f'\n{len(errors)} erreur(s). Build interrompu (utilisez --lenient pour forcer pendant la rédaction).')
        sys.exit(1)

    # 4) écriture
    changed = 0
    for out, html in rendered.items():
        changed += write_if_changed(ROOT / out, html)
    css = '\n\n'.join(read(SRC / 'css' / n) for n in CSS_ORDER if (SRC / 'css' / n).exists())
    # la version est lisible depuis la page : de quoi détecter une feuille périmée servie par un cache
    entete_css = f'/* généré par scripts/build.py {BUILD_ID} : modifier src/css/ */\n:root {{ --build: "{BUILD_ID}"; }}\n'
    changed += write_if_changed(ROOT / 'assets' / 'css' / 'styles.css', entete_css + css)
    for js in (SRC / 'js').glob('*.js'):
        changed += write_if_changed(ROOT / 'assets' / 'js' / js.name, read(js))
    changed += write_if_changed(DATA / 'search-index.json', json.dumps(group_index(search_index), ensure_ascii=False, separators=(',', ':')))
    urls = ''.join(f'<url><loc>{S["base_url"]}/{"" if o == "index.html" else o}</loc><lastmod>{TODAY}</lastmod></url>' for o in generated_outs)
    changed += write_if_changed(ROOT / 'sitemap.xml', f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    changed += write_if_changed(ROOT / 'robots.txt', f'User-agent: *\nAllow: /\nSitemap: {S["base_url"]}/sitemap.xml\n')
    changed += write_if_changed(ROOT / '.nojekyll', '')
    # pages spéciales
    off = read(SHELL / 'offline.html')
    changed += write_if_changed(ROOT / 'hors-ligne.html', fill(off, {'title': 'Hors ligne', 'site_title': esc(S['title']), 'heading': 'Vous êtes hors ligne', 'text': 'Cette page n\'a pas encore été enregistrée sur votre appareil. Les pages déjà consultées restent disponibles ; reconnectez-vous pour ouvrir celle-ci, ou rendez toute la session disponible hors ligne depuis les réglages.', 'base_path': S['base_path'], 'author': esc(S['author'])}))
    changed += write_if_changed(ROOT / '404.html', fill(off, {'title': 'Page introuvable', 'site_title': esc(S['title']), 'heading': 'Page introuvable', 'text': 'L\'adresse demandée n\'existe pas ou a changé. Utilisez les liens ci-dessous ou la recherche du site.', 'base_path': S['base_path'], 'author': esc(S['author'])}))
    # service worker
    # Les pages demandent la feuille et les modules avec « ?v=BUILD_ID » : on pré-cache exactement
    # ces URL, sinon une première visite hors ligne les chercherait sous une adresse absente du cache.
    precache = ['./', 'index.html', 'hors-ligne.html', f'assets/css/styles.css?v={BUILD_ID}', 'manifest.webmanifest', 'data/search-index.json', 'assets/icons/favicon.svg'] + \
               [f'assets/js/{p.name}?v={BUILD_ID}' for p in sorted((SRC / 'js').glob('*.js'))] + [f'assets/fonts/{p.name}' for p in sorted((ROOT / 'assets' / 'fonts').glob('*.woff2'))]
    precache += [o for o in generated_outs if o.endswith('index.html') or o in ('glossaire.html', 'references.html')]
    precache = list(dict.fromkeys(precache))  # Cache.addAll() refuse les doublons : dédoublonner en gardant l'ordre
    all_pages = [o for o in generated_outs if o not in precache]
    sw = read(SRC / 'sw.template.js').replace('__BUILD_ID__', BUILD_ID).replace('__PRECACHE__', json.dumps(precache)).replace('__ALL_PAGES__', json.dumps(all_pages))
    changed += write_if_changed(ROOT / 'sw.js', sw)
    total_kb = sum((ROOT / o).stat().st_size for o in all_pages if (ROOT / o).exists()) // 1024
    if warnings:
        print('\nAvertissements :')
        for w in warnings:
            print('  !', w)
    print(f'\n{len(rendered)} pages, {len(search_index)} blocs indexés, {len(GLOSS)} termes, {len(REFS)} références ; pré-chargement complet ≈ {total_kb} Ko ; {changed} fichier(s) modifié(s).')


if __name__ == '__main__':
    main()
