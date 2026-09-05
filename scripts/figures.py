"""Génère les graphiques de données (SVG inline) depuis data/figures.json vers src/figures/gen/.
Types : hbar (barres horizontales avec intervalle), gbar (barres groupées, 2 à 4 séries), dots100 (100 points),
dumbbell (avant → après), dotplot (points avec ligne de référence à 1).
Règles (dataviz) : marques fines (≤ 24 px), extrémité arrondie, grille en filet, étiquettes directes sobres,
texte en encre (jamais en couleur de série), légende dès 2 séries, couleurs = variables CSS --d1…--d4.
Usage : python scripts/figures.py
"""
from __future__ import annotations

import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'src' / 'figures' / 'gen'
OUT.mkdir(parents=True, exist_ok=True)
FIG = json.load(open(ROOT / 'data' / 'figures.json', encoding='utf-8'))

W = 640
LEFT = 250
RIGHT = 70
FONT = 13


def esc(s):
    return html.escape(str(s), quote=True)


def fmt(v, nd=1):
    s = f'{v:.{nd}f}'.replace('.', ',')
    return s.rstrip('0').rstrip(',') if ',' in s else s


def bar_path(x0, y0, w, h, r=4):
    """Barre horizontale carrée à gauche (ligne de base), arrondie à droite (extrémité de donnée)."""
    if w <= r:
        return f'M{x0},{y0} h{max(w, 0.5)} v{h} h{-max(w, 0.5)} z'
    return f'M{x0},{y0} h{w - r} a{r},{r} 0 0 1 {r},{r} v{h - 2 * r} a{r},{r} 0 0 1 {-r},{r} h{-(w - r)} z'


def wrap(label, width=32, maxlines=2):
    """Coupe en lignes. Au-delà du plafond, on le dit par des points de suspension :
    une étiquette tronquée en silence a déjà fait lire « … est fréquent à la » sans la fin."""
    words = label.split()
    lines, cur = [], ''
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w).strip()
    if cur:
        lines.append(cur)
    if len(lines) > maxlines:
        lines = lines[:maxlines]
        lines[-1] = lines[-1].rstrip(' ,;:') + '…'
    return lines


CUR = {'name': 'fig'}


def svg_open(w, h, title, desc, cls=''):
    n = CUR['name']
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="{n}-t {n}-d" class="{cls}" font-family="Public Sans, Segoe UI, system-ui, sans-serif" font-size="{FONT}">'
            f'<title id="{n}-t">{esc(title)}</title><desc id="{n}-d">{esc(desc)}</desc>')


def grid(x_of, vmax, y0, y1, step, unit=''):
    """Graduations. L'unité est portée par la dernière, pour qu'un chiffre nu ne reste jamais sans nom."""
    out = []
    v, dernier = 0, None
    while v <= vmax + 1e-9:
        x = x_of(v)
        out.append(f'<line class="grid" x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y1}"/>')
        dernier = (x, v)
        out.append(f'<text class="t-sm" x="{x:.1f}" y="{y1 + 16}" text-anchor="middle">{fmt(v)}</text>')
        v += step
    if unit and dernier:
        out[-1] = f'<text class="t-sm" x="{dernier[0]:.1f}" y="{y1 + 16}" text-anchor="middle">{fmt(dernier[1])} {esc(unit)}</text>'
    return out


def label_lines(x, y, label, anchor='end', maxlines=2):
    lines = wrap(label, maxlines=maxlines)
    dy = -(len(lines) - 1) * 7
    return ''.join(f'<text x="{x}" y="{y + dy + i * 15:.1f}" text-anchor="{anchor}" dominant-baseline="middle">{esc(l)}</text>' for i, l in enumerate(lines))


def render_hbar(d):
    items = d['items']
    # trois lignes d'étiquette autorisées, et une ligne de plus quand une étendue est décrite
    nl = max(len(wrap(i['label'], maxlines=3)) for i in items)
    avec_etendue = any(i.get('range_label') for i in items)
    rowh = max(44 if len(items) < 8 else 34, 22 + 15 * nl + (18 if avec_etendue else 8))
    top = 18 if not d.get('refline') else 30
    h = top + rowh * len(items) + 34
    vmax = d.get('max', max(i.get('hi', i['value']) for i in items) * 1.15)
    x_of = lambda v: LEFT + (W - LEFT - RIGHT) * v / vmax
    step = 10 if vmax > 25 else 5 if vmax > 10 else 1
    out = [svg_open(W, h, d['title'], d['desc'])]
    out += grid(x_of, vmax, top - 6, top + rowh * len(items), step, d.get('unit', ''))
    for i, it in enumerate(items):
        y = top + i * rowh + (10 if rowh > 40 else 6)
        out.append(f'<path class="f1" d="{bar_path(x_of(0), y, x_of(it["value"]) - x_of(0), 22)}"><title>{esc(it["label"])} : {fmt(it["value"])} {esc(d.get("unit", ""))}{(" (" + esc(it["range_label"]) + ")") if it.get("range_label") else ""}</title></path>')
        if 'lo' in it:
            out.append(f'<line class="line" x1="{x_of(it["lo"]):.1f}" y1="{y + 11}" x2="{x_of(it["hi"]):.1f}" y2="{y + 11}" stroke-width="1.5"/>')
            out.append(f'<line class="line" x1="{x_of(it["lo"]):.1f}" y1="{y + 5}" x2="{x_of(it["lo"]):.1f}" y2="{y + 17}"/><line class="line" x1="{x_of(it["hi"]):.1f}" y1="{y + 5}" x2="{x_of(it["hi"]):.1f}" y2="{y + 17}"/>')
        lignes = wrap(it['label'], maxlines=3)
        out.append(label_lines(LEFT - 10, y + 11, it['label'], maxlines=3))
        xv = x_of(it.get('hi', it['value'])) + 8
        out.append(f'<text class="t-num" x="{xv:.1f}" y="{y + 11}" dominant-baseline="middle">{fmt(it["value"])} {esc(d.get("unit", ""))}</text>')
        if it.get('range_label'):
            # ce que mesure la moustache, dit sur sa propre ligne : d'une barre à l'autre ce n'est pas la même chose
            ry = y + 11 + (len(lignes) - 1) * 7 + 16
            out.append(f'<text class="t-sm" x="{LEFT - 10}" y="{ry:.1f}" text-anchor="end">{esc(it["range_label"])}</text>')
    if d.get('refline'):
        rx = x_of(d['refline']['value'])
        out.append(f'<line class="ref" x1="{rx:.1f}" y1="{top - 6}" x2="{rx:.1f}" y2="{top + rowh * len(items)}" stroke-width="2"/>')
        out.append(f'<text class="t-sm" x="{rx + 4:.1f}" y="{top - 8}">{esc(d["refline"]["label"])}</text>')
    out.append('</svg>')
    return ''.join(out)


def render_gbar(d):
    items = d['items']
    series = d['series']
    n = len(series)
    barh = 14
    gap = 3
    rowh = n * (barh + gap) + 18
    top = 34
    h = top + rowh * len(items) + 34
    vmax = d.get('max', max(v for i in items for v in i['values']) * 1.15)
    x_of = lambda v: LEFT + (W - LEFT - RIGHT) * v / vmax
    step = 10 if vmax > 25 else 5
    out = [svg_open(W, h, d['title'], d['desc'])]
    # légende
    lx = LEFT
    for k, s in enumerate(series):
        out.append(f'<rect class="f{k + 1}" x="{lx}" y="6" width="12" height="12" rx="2"/><text x="{lx + 17}" y="12.5" dominant-baseline="middle">{esc(s)}</text>')
        lx += 17 + len(s) * 7.5 + 18
    out += grid(x_of, vmax, top - 6, top + rowh * len(items), step, d.get('unit', ''))
    for i, it in enumerate(items):
        y0 = top + i * rowh + 6
        for k, v in enumerate(it['values']):
            y = y0 + k * (barh + gap)
            out.append(f'<path class="f{k + 1}" d="{bar_path(x_of(0), y, x_of(v) - x_of(0), barh, 3)}"><title>{esc(it["label"])} · {esc(series[k])} : {fmt(v)} %</title></path>')
            out.append(f'<text class="t-sm t-num" x="{x_of(v) + 6:.1f}" y="{y + barh / 2:.1f}" dominant-baseline="middle">{fmt(v)}</text>')
        out.append(label_lines(LEFT - 10, y0 + (n * (barh + gap) - gap) / 2, it['label']))
    out.append('</svg>')
    return ''.join(out)


def render_dots100(d):
    cols = 10
    r = 9
    step = 26
    pad = 14
    w = pad * 2 + step * cols
    h = pad * 2 + step * 10 + 30
    out = [svg_open(w, h, d['title'], d['desc'], 'narrow')]
    for i in range(100):
        cx = pad + step * (i % cols) + step / 2
        cy = pad + step * (i // cols) + step / 2
        on = ' on' if i < d['value'] else ''
        out.append(f'<circle class="dot{on}" cx="{cx}" cy="{cy}" r="{r}"/>')
    out.append(f'<text class="t-b" x="{pad}" y="{h - 12}"><tspan class="t-num" font-size="18">{d["value"]}</tspan> sur 100 · {esc(d["src"])}</text>')
    out.append('</svg>')
    return ''.join(out)


def render_dumbbell(d):
    """Deux états reliés. La couleur seule ne dirait pas lequel est lequel : on nomme les deux
    extrémités dans une clé, on leur donne deux formes (anneau puis disque), et la flèche dit le sens."""
    items = d['items']
    series = d.get('series') or ['Avant', 'Après']
    rowh = 56
    top = 34
    h = top + rowh * len(items) + 34
    vmax = d.get('max', 100)
    unit = d.get('unit', '%')
    x_of = lambda v: LEFT + (W - LEFT - RIGHT) * v / vmax
    out = [svg_open(W, h, d['title'], d['desc'])]
    # clé : forme et couleur, dans l'ordre de lecture
    lx = LEFT
    out.append(f'<circle class="halo" cx="{lx + 6}" cy="12" r="8"/><circle class="dot-ring" cx="{lx + 6}" cy="12" r="6"/>'
               f'<text x="{lx + 19}" y="12.5" dominant-baseline="middle">{esc(series[0])}</text>')
    lx += 19 + len(series[0]) * 7.5 + 22
    out.append(f'<circle class="halo" cx="{lx + 6}" cy="12" r="8"/><circle class="f1" cx="{lx + 6}" cy="12" r="6"/>'
               f'<text x="{lx + 19}" y="12.5" dominant-baseline="middle">{esc(series[1])}</text>')
    out += grid(x_of, vmax, top - 6, top + rowh * len(items), 10, unit)
    for i, it in enumerate(items):
        y = top + i * rowh + 20
        x1, x2 = x_of(it['from']), x_of(it['to'])
        sens = -1 if x2 < x1 else 1
        out.append(f'<line class="line" x1="{x1:.1f}" y1="{y}" x2="{x2 - sens * 11:.1f}" y2="{y}" stroke-width="3"/>')
        # pointe de flèche : le sens de lecture ne se devine plus
        out.append(f'<path class="f1" d="M{x2 - sens * 11:.1f},{y - 5} L{x2 - sens * 11:.1f},{y + 5} L{x2 - sens * 2:.1f},{y} z"/>')
        out.append(f'<circle class="halo" cx="{x1:.1f}" cy="{y}" r="9"/><circle class="dot-ring" cx="{x1:.1f}" cy="{y}" r="7">'
                   f'<title>{esc(series[0])} : {fmt(it["from"])} {esc(unit)}</title></circle>')
        out.append(f'<circle class="halo" cx="{x2:.1f}" cy="{y}" r="9"/><circle class="f1" cx="{x2:.1f}" cy="{y}" r="7">'
                   f'<title>{esc(series[1])} : {fmt(it["to"])} {esc(unit)}</title></circle>')
        out.append(f'<text class="t-num" x="{x1:.1f}" y="{y - 15}" text-anchor="middle">{fmt(it["from"])} {esc(unit)}</text>')
        out.append(f'<text class="t-num" x="{x2:.1f}" y="{y - 15}" text-anchor="middle">{fmt(it["to"])} {esc(unit)}</text>')
        out.append(label_lines(LEFT - 10, y, it['label'], maxlines=3))
    out.append('</svg>')
    return ''.join(out)


def render_dotplot(d):
    items = d['items']
    rowh = 34
    top = 18
    h = top + rowh * len(items) + 34
    vmax = d.get('max', 4)
    x_of = lambda v: LEFT + (W - LEFT - RIGHT) * v / vmax
    out = [svg_open(W, h, d['title'], d['desc'])]
    out += grid(x_of, vmax, top - 6, top + rowh * len(items), 1)
    out.append(f'<line class="ref" x1="{x_of(1):.1f}" y1="{top - 6}" x2="{x_of(1):.1f}" y2="{top + rowh * len(items)}" stroke-width="2"/>')
    out.append(f'<text class="t-sm" x="{x_of(1) + 4:.1f}" y="{top - 8}">1 = aucune différence</text>')
    for i, it in enumerate(items):
        y = top + i * rowh + 14
        out.append(f'<line class="line-soft" x1="{x_of(1):.1f}" y1="{y}" x2="{x_of(it["value"]):.1f}" y2="{y}"/>')
        out.append(f'<circle class="halo" cx="{x_of(it["value"]):.1f}" cy="{y}" r="8"/><circle class="f1" cx="{x_of(it["value"]):.1f}" cy="{y}" r="6"><title>{esc(it["label"])} : {fmt(it["value"], 2)}</title></circle>')
        out.append(f'<text class="t-num" x="{x_of(it["value"]) + 12:.1f}" y="{y}" dominant-baseline="middle">{fmt(it["value"], 2)}</text>')
        out.append(label_lines(LEFT - 10, y, it['label']))
    out.append('</svg>')
    return ''.join(out)


RENDER = {'hbar': render_hbar, 'gbar': render_gbar, 'dots100': render_dots100, 'dumbbell': render_dumbbell, 'dotplot': render_dotplot}

n = 0
for name, d in FIG.items():
    CUR['name'] = name
    svg = RENDER[d['type']](d)
    (OUT / f'{name}.svg').write_text(svg, encoding='utf-8')
    # la note de figure (sources, mises en garde) n'est plus dessinée : troisième ligne du jumeau, rendue sous la figure
    (OUT / f'{name}.txt').write_text(d['title'] + '\n' + d['desc'] + '\n' + (d.get('note') or '') + chr(10), encoding='utf-8')
    n += 1
print(f'{n} figures générées dans {OUT.relative_to(ROOT)}')
