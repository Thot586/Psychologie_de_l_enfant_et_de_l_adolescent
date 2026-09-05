"""Génère des schémas conceptuels SVG (inline, thème-aware) depuis data/schemas.json vers src/figures/gen/.

Types : fork, columns, timeline, venn2, venn3, rings, cycle, chain, curves, bands, stairs, triangle, matrix, iceberg, balance, grid.
Style : classes CSS de figures.css (box, box-p, box-a, box-s, box-b, f1…f4, s1…s4, line, arrow, t-sm, t-b…), texte en encre,
aucune couleur en dur. Chaque figure reçoit <title> et <desc> (fichier .txt jumeau : titre + description).
Usage : python scripts/schemas.py
"""
from __future__ import annotations

import html
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'src' / 'figures' / 'gen'
OUT.mkdir(parents=True, exist_ok=True)
SPECS = json.load(open(ROOT / 'data' / 'schemas.json', encoding='utf-8'))
W = 640
TONE = {'p': 'box-p', 'a': 'box-a', 's': 'box-s', 'b': 'box-b', '': 'box', None: 'box'}
FILL = {'p': 'f1', 'a': 'f2', 's': 'f4', 'b': 'f3', '': 'f1', None: 'f1'}


def esc(s):
    return html.escape(str(s), quote=True)


def wrap(text, width):
    words = str(text).split()
    lines, cur = [], ''
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w).strip()
    if cur:
        lines.append(cur)
    return lines


def text_block(x, y, text, width_chars, cls='', anchor='start', lh=15, size=None):
    lines = wrap(text, width_chars)
    fs = f' font-size="{size}"' if size else ''
    return ''.join(f'<text class="{cls}" x="{x:.1f}" y="{y + i * lh:.1f}" text-anchor="{anchor}"{fs}>{esc(l)}</text>' for i, l in enumerate(lines)), len(lines)


def box(x, y, w, h, tone='', rx=8):
    return f'<rect class="{TONE.get(tone, "box")}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}"/>'


def marker_defs(name):
    return (f'<defs><marker id="{name}-arr" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto" markerUnits="userSpaceOnUse">'
            f'<path d="M0,0 L8,4 L0,8 z" fill="currentColor"/></marker></defs>')


def arrow(name, x1, y1, x2, y2, soft=False, dashed=False):
    cls = 'arrow-soft' if soft else 'arrow'
    dash = ' stroke-dasharray="5 4"' if dashed else ''
    return f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" marker-end="url(#{name}-arr)"{dash}/>'


def svg(name, h, body, cls=''):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" role="img" aria-labelledby="{name}-t {name}-d" class="{cls}" '
            f'font-family="Public Sans, Segoe UI, system-ui, sans-serif" font-size="13"><title id="{name}-t">__T__</title><desc id="{name}-d">__D__</desc>{body}</svg>')


def titled_box(x, y, w, title, lines, tone='', width_chars=None, min_h=0):
    width_chars = width_chars or max(12, int(w / 7.2))
    body_lines = []
    for l in lines:
        body_lines += wrap(l, width_chars)
    tl = wrap(title, width_chars) if title else []
    h = max(min_h, 14 + len(tl) * 16 + (len(body_lines) * 14 + (6 if body_lines else 0)) + 8)
    out = [box(x, y, w, h, tone)]
    yy = y + 20
    for l in tl:
        out.append(f'<text class="t-b" x="{x + 10:.1f}" y="{yy:.1f}">{esc(l)}</text>')
        yy += 16
    yy += 2
    for l in body_lines:
        out.append(f'<text class="t-sm" x="{x + 10:.1f}" y="{yy:.1f}">{esc(l)}</text>')
        yy += 14
    return ''.join(out), h


def note(y, text):
    return text_block(10, y, text, 95, 't-sm')[0]


# ------------------------------------------------------------------ types
def r_fork(name, s):
    branches = s['branches']
    bw = 300
    x0 = 20
    xb = W - bw - 20
    parts = [marker_defs(name)]
    y = 16
    common = s.get('common')
    if common:
        b, h = titled_box(x0, y, W - 40, common.get('title', ''), common.get('lines', []), common.get('tone', 's'))
        parts.append(b)
        y += h + 14
    ys = y
    ybs = []
    for br in branches:
        b, h = titled_box(xb, y, bw, br.get('title', ''), br.get('lines', []), br.get('tone', ''))
        parts.append(b)
        ybs.append((y, h))
        y += h + 10
    total = y - ys - 10
    rh = 70
    ry = ys + total / 2 - rh / 2
    b, rh2 = titled_box(x0, ry, 190, s['root'].get('title', ''), s['root'].get('lines', []), s['root'].get('tone', 'p'), min_h=rh)
    parts.append(b)
    for (by, bh) in ybs:
        parts.append(f'<path class="arrow-soft" d="M{x0 + 190},{ry + rh2 / 2:.1f} C{x0 + 250},{ry + rh2 / 2:.1f} {xb - 60},{by + bh / 2:.1f} {xb - 2},{by + bh / 2:.1f}" marker-end="url(#{name}-arr)"/>')
    if s.get('note'):
        parts.append(note(y + 6, s['note']))
        y += 16 * len(wrap(s['note'], 95)) + 6
    return svg(name, y + 10, ''.join(parts))


def r_columns(name, s):
    cols = s['columns']
    n = len(cols)
    gap = 12
    cw = (W - 40 - gap * (n - 1)) / n
    parts = []
    y = 16
    hmax = 0
    for i, c in enumerate(cols):
        x = 20 + i * (cw + gap)
        b, h = titled_box(x, y, cw, c.get('title', ''), c.get('items', []), c.get('tone', ''))
        parts.append(b)
        hmax = max(hmax, h)
    # égalise les hauteurs
    parts2 = []
    for i, c in enumerate(cols):
        x = 20 + i * (cw + gap)
        b, _ = titled_box(x, y, cw, c.get('title', ''), c.get('items', []), c.get('tone', ''), min_h=hmax)
        parts2.append(b)
    y += hmax + 10
    if s.get('arrows'):
        parts2.insert(0, marker_defs(name))
        for i in range(n - 1):
            x = 20 + (i + 1) * (cw + gap) - gap
            parts2.append(arrow(name, x + 1, 16 + hmax / 2, x + gap - 1, 16 + hmax / 2))
    if s.get('note'):
        parts2.append(note(y + 6, s['note']))
        y += 16 * len(wrap(s['note'], 95)) + 6
    return svg(name, y + 10, ''.join(parts2))


def r_timeline(name, s):
    ax = s['axis']
    start, end = ax['start'], ax['end']
    x0, x1 = 30, W - 30
    x_of = lambda v: x0 + (x1 - x0) * (v - start) / (end - start)
    lanes = s.get('lanes', [])
    parts = []
    y = 26
    zones = s.get('zones') or []

    # Une seule chose est dite par la couleur : la tranche d'âge. Les tranches deviennent donc des
    # bandes verticales qui traversent toutes les pistes, dans les teintes d'âge du reste du site ;
    # les pistes, elles, ne sont plus colorées — leur intitulé suffit à les distinguer.
    base_h = s.get('lane_height', 54) + 14
    ly = y + (22 if zones else 0)
    lane_top = ly
    tracé = []
    for ln in lanes:
        # 1) placer les étiquettes : autant de rangées qu'il en faut pour qu'aucune ne se chevauche
        placed, rows = [], []
        for e in sorted(ln.get('events', []), key=lambda e: e['at']):
            ex = x_of(e['at'])
            width = len(e['label']) * 6.4
            anchor = 'start' if ex + 6 + width < x1 else 'end'
            x_start = ex + 6 if anchor == 'start' else ex - 6 - width
            row = next((r for r, occupied in enumerate(rows) if x_start > occupied + 8), len(rows))
            if row == len(rows):
                rows.append(-1e9)
            rows[row] = x_start + width
            placed.append((e, ex, anchor, row))
        # 2) la piste est aussi haute qu'il le faut pour ces rangées
        lane_h = max(base_h, 30 + max(0, len(rows) - 1) * 13 + 26)
        tracé.append((ln, placed, ly, lane_h))
        ly += lane_h

    if zones:
        hauteur = ly - (y - 14)
        for i, z in enumerate(zones):
            zx, zw = x_of(z['from']), x_of(z['to']) - x_of(z['from'])
            parts.append(f'<rect class="fa{min(i + 1, 4)}s band" x="{zx:.1f}" y="{y - 14}" width="{zw:.1f}" height="{hauteur:.1f}" rx="4"/>')
            parts.append(f'<text class="t-sm t-b ta{min(i + 1, 4)}" x="{zx + zw / 2:.1f}" y="{y}" text-anchor="middle">{esc(z["label"])}</text>')

    for ln, placed, top, lane_h in tracé:
        if top > lane_top:
            parts.append(f'<line class="line-soft" x1="{x0}" y1="{top - 3}" x2="{x1}" y2="{top - 3}"/>')
        parts.append(f'<text class="t-b" x="{x0 + 8}" y="{top + 16}">{esc(ln["title"])}</text>')
        for e, ex, anchor, row in placed:
            ey = top + 30 + row * 13
            parts.append(f'<circle class="dot-ink" cx="{ex:.1f}" cy="{top + lane_h - 12}" r="4"/>')
            parts.append(f'<line class="line-soft" x1="{ex:.1f}" y1="{ey + 3}" x2="{ex:.1f}" y2="{top + lane_h - 16}"/>')
            parts.append(f'<text class="t-sm" x="{ex + (6 if anchor == "start" else -6):.1f}" y="{ey:.1f}" text-anchor="{anchor}">{esc(e["label"])}</text>')
    y = ly + 4
    parts.append(f'<line class="line" x1="{x0}" y1="{y}" x2="{x1}" y2="{y}"/>')
    last_tick = -1e9
    for t in ax['ticks']:
        tx = x_of(t)
        parts.append(f'<line class="line" x1="{tx:.1f}" y1="{y - 4}" x2="{tx:.1f}" y2="{y + 4}"/>')
        if tx - last_tick < 34:      # deux graduations trop proches : on garde le trait, pas l'année
            continue
        last_tick = tx
        parts.append(f'<text class="t-sm" x="{tx:.1f}" y="{y + 18}" text-anchor="middle">{esc(ax.get("format", "{}").format(t))}</text>')
    y += 24
    ms = sorted(s.get('milestones', []), key=lambda m: m['at'])
    if ms:
        # empilement adaptatif : un jalon descend d'une rangée tant qu'il en croiserait un autre
        placed, rows = [], []
        for m in ms:
            lines = wrap(m['label'], 22)
            w = max(len(l) for l in lines) * 6.4
            mx = x_of(m['at'])
            left = mx - w / 2
            row = next((r for r, occupied in enumerate(rows) if left > occupied + 10), len(rows))
            if row == len(rows):
                rows.append(-1e9)
            rows[row] = left + w
            placed.append((m, mx, lines, row))
        heights = {}
        for _, _, lines, row in placed:
            heights[row] = max(heights.get(row, 0), len(lines))
        offset, acc = {}, 0
        for r in sorted(heights):
            offset[r] = acc
            acc += heights[r] * 13 + 6
        for m, mx, lines, row in placed:
            ty = y + 20 + offset[row]
            half = max(len(l) for l in lines) * 3.2
            tx = min(max(mx, x0 + half), x1 - half)   # jamais coupé par le bord du cadre
            parts.append(f'<circle class="{FILL.get(m.get("tone"), "f2")}" cx="{mx:.1f}" cy="{y + 4}" r="5"/>')
            if offset[row]:
                parts.append(f'<line class="line-soft" x1="{mx:.1f}" y1="{y + 10}" x2="{tx:.1f}" y2="{ty - 9:.1f}"/>')
            parts.append(text_block(tx, ty, m['label'], 22, 't-sm', 'middle', 13)[0])
        y += 20 + acc
    if s.get('note'):
        parts.append(note(y + 6, s['note']))
        y += 16 * len(wrap(s['note'], 95)) + 6
    return svg(name, y + 10, ''.join(parts), 'scroll' if s.get('scroll') else '')


def r_venn(name, s, n):
    sets = s['sets']
    parts = []
    if n == 2:
        cx = [236, 404]
        cy = [190, 190]
        r = 132
    else:
        cx = [320 - 95, 320 + 95, 320]
        cy = [170, 170, 320]
        r = 125
    for i in range(n):
        parts.append(f'<circle class="{FILL.get(sets[i].get("tone"), f"f{i + 1}")} area" cx="{cx[i]}" cy="{cy[i]}" r="{r}"/><circle class="s{i + 1}" fill="none" stroke-width="1.5" cx="{cx[i]}" cy="{cy[i]}" r="{r}"/>')
    lab_pos = [(cx[0] - r + 20, cy[0] - r + 26), (cx[1] + r - 20, cy[1] - r + 26)] + ([(cx[2], cy[2] + r - 16)] if n == 3 else [])
    anchors = ['start', 'end', 'middle']
    for i in range(n):
        tb, _ = text_block(lab_pos[i][0], lab_pos[i][1], sets[i]['label'], 20, 't-b', anchors[i], 15)
        parts.append(tb)
        if sets[i].get('note'):
            nx = lab_pos[i][0]
            ny = lab_pos[i][1] + 16 * len(wrap(sets[i]['label'], 20))
            tb, _ = text_block(nx, ny, sets[i]['note'], 22, 't-sm', anchors[i], 13)
            parts.append(tb)
    if s.get('center'):
        ccx = sum(cx) / n
        ccy = sum(cy) / n + (10 if n == 3 else 0)
        tb, _ = text_block(ccx, ccy - 4, s['center'], 12 if n == 2 else 16, 't-b', 'middle', 15)
        parts.append(tb)
    y_extra = cy[0] + r + 26 if n == 2 else 0
    for p in s.get('pairs', []):
        if n == 2:
            tb, nl = text_block(320, y_extra, p['label'], 70, 't-sm', 'middle', 14)
            y_extra += 14 * nl + 4
        else:
            tb, _ = text_block(p['x'], p['y'], p['label'], 18, 't-sm', 'middle', 13)
        parts.append(tb)
    h = (max(380, int(y_extra) + 10)) if n == 2 else 470
    if s.get('note'):
        ny = (int(y_extra) + 10) if n == 2 else h - 22
        parts.append(note(ny, s['note']))
        h = ny + 16 * len(wrap(s['note'], 95)) + 6
    return svg(name, h, ''.join(parts))


def r_rings(name, s):
    rings = s['rings']
    n = len(rings)
    cx, cy = 230, 230
    rmax = 210
    step = rmax / n
    parts = []
    for i in range(n - 1, -1, -1):
        r = step * (i + 1)
        parts.append(f'<circle class="{TONE.get(rings[i].get("tone"), "box")}" cx="{cx}" cy="{cy}" r="{r:.1f}"/>')
    for i, rg in enumerate(rings):
        r_in = step * i
        r_out = step * (i + 1)
        ty = cy - (r_in + r_out) / 2 if i else cy
        parts.append(f'<text class="t-b" x="{cx}" y="{ty + 4:.1f}" text-anchor="middle">{esc(rg["title"])}</text>')
    # légende à droite
    lx, ly = 470, 30
    for i, rg in enumerate(rings):
        parts.append(f'<circle class="{TONE.get(rg.get("tone"), "box")}" cx="{lx}" cy="{ly + 4}" r="6"/>')
        parts.append(f'<text class="t-b" x="{lx + 14}" y="{ly + 8}">{esc(rg["title"])}</text>')
        ly += 18
        for it in rg.get('items', []):
            for l in wrap(it, 24):
                parts.append(f'<text class="t-sm" x="{lx + 14}" y="{ly + 6}">{esc(l)}</text>')
                ly += 14
        ly += 8
    h = max(460, ly + 10)
    if s.get('note'):
        parts.append(note(h - 6, s['note']))
        h += 16 * len(wrap(s['note'], 95))
    return svg(name, h, ''.join(parts))


def r_cycle(name, s):
    cycles = s['cycles'] if 'cycles' in s else [s]
    parts = [marker_defs(name)]
    n_c = len(cycles)
    cw = (W - 40) / n_c
    h = 0
    for ci, c in enumerate(cycles):
        steps = c['steps']
        n = len(steps)
        cx = 20 + cw * ci + cw / 2
        cy = 190
        R = min(120, cw / 2 - 70)
        pos = []
        for i in range(n):
            a = -math.pi / 2 + 2 * math.pi * i / n
            pos.append((cx + R * math.cos(a), cy + R * math.sin(a)))
        for i in range(n):
            x1, y1 = pos[i]
            x2, y2 = pos[(i + 1) % n]
            dx, dy = x2 - x1, y2 - y1
            L = math.hypot(dx, dy)
            ux, uy = dx / L, dy / L
            parts.append(arrow(name, x1 + ux * 46, y1 + uy * 46, x2 - ux * 50, y2 - uy * 50))
        for i, st in enumerate(steps):
            x, y = pos[i]
            lines = wrap(st, 14)
            bh = 14 + 14 * len(lines)
            parts.append(box(x - 52, y - bh / 2, 104, bh, c.get('tone', ''), 7))
            for j, l in enumerate(lines):
                parts.append(f'<text class="t-sm" x="{x:.1f}" y="{y - bh / 2 + 16 + j * 14:.1f}" text-anchor="middle">{esc(l)}</text>')
        if c.get('title'):
            parts.append(f'<text class="t-b" x="{cx:.1f}" y="{cy + R + 66}" text-anchor="middle">{esc(c["title"])}</text>')
        h = max(h, cy + R + 84)
    if s.get('note'):
        parts.append(note(h, s['note']))
        h += 16 * len(wrap(s['note'], 95))
    return svg(name, h + 6, ''.join(parts))


def r_chain(name, s):
    steps = s['steps']
    n = len(steps)
    gap = 26
    bw = (W - 40 - gap * (n - 1)) / n
    parts = [marker_defs(name)]
    y = 16
    hmax = 0
    for i, st in enumerate(steps):
        _, h = titled_box(0, 0, bw, st.get('title', ''), st.get('lines', []), st.get('tone', ''))
        hmax = max(hmax, h)
    for i, st in enumerate(steps):
        x = 20 + i * (bw + gap)
        b, _ = titled_box(x, y, bw, st.get('title', ''), st.get('lines', []), st.get('tone', ''), min_h=hmax)
        parts.append(b)
        if i < n - 1:
            parts.append(arrow(name, x + bw + 2, y + hmax / 2, x + bw + gap - 2, y + hmax / 2))
    yb = y + hmax
    fb = s.get('feedback')
    if fb:
        bxw = 260
        bx = W / 2 - bxw / 2
        by = yb + 58
        b, h = titled_box(bx, by, bxw, fb.get('title', ''), fb.get('lines', []), fb.get('tone', 's'))
        tx = 20 + (fb.get('to', n - 2)) * (bw + gap) + bw / 2
        parts.append(f'<path class="curve s4" d="M{W / 2:.1f},{by - 2} C{W / 2:.1f},{by - 40} {tx:.1f},{yb + 40} {tx:.1f},{yb + 6}" marker-end="url(#{name}-arr)"/>')
        parts.append(b)
        if fb.get('label'):
            tb, nl = text_block(W / 2, by + h + 18, fb['label'], 80, 't-sm', 'middle', 14)
            parts.append(tb)
            h += 18 + 14 * nl
        yb = by + h
    if s.get('note'):
        parts.append(note(yb + 12, s['note']))
        yb += 16 * len(wrap(s['note'], 95)) + 12
    return svg(name, yb + 12, ''.join(parts))


def smooth_path(pts):
    if len(pts) < 2:
        return ''
    d = f'M{pts[0][0]:.1f},{pts[0][1]:.1f}'
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        cx = (x0 + x1) / 2
        d += f' C{cx:.1f},{y0:.1f} {cx:.1f},{y1:.1f} {x1:.1f},{y1:.1f}'
    return d


def r_curves(name, s):
    ax = s['x']
    x0, x1 = 60, W - 130
    y0, y1 = 250, 30
    x_of = lambda v: x0 + (x1 - x0) * (v - ax['start']) / (ax['end'] - ax['start'])
    y_of = lambda v: y0 - (y0 - y1) * v / 100
    parts = [marker_defs(name)]
    for bnd in s.get('bands', []):
        parts.append(f'<rect class="f2 area" x="{x_of(bnd["from"]):.1f}" y="{y1}" width="{x_of(bnd["to"]) - x_of(bnd["from"]):.1f}" height="{y0 - y1}"/>')
        tb, _ = text_block((x_of(bnd['from']) + x_of(bnd['to'])) / 2, y1 + 14, bnd['label'], 22, 't-sm', 'middle', 13)
        parts.append(tb)
    parts.append(f'<line class="line" x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}"/>')
    parts.append(f'<line class="line" x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}"/>')
    for t in ax['ticks']:
        parts.append(f'<line class="line" x1="{x_of(t):.1f}" y1="{y0}" x2="{x_of(t):.1f}" y2="{y0 + 5}"/><text class="t-sm" x="{x_of(t):.1f}" y="{y0 + 18}" text-anchor="middle">{esc(t)}</text>')
    parts.append(f'<text class="t-sm" x="{(x0 + x1) / 2:.1f}" y="{y0 + 34}" text-anchor="middle">{esc(ax.get("label", ""))}</text>')
    if s.get('y_label'):
        parts.append(f'<text class="t-sm" x="{x0 + 6}" y="{y1 - 8}" text-anchor="start">{esc(s["y_label"])}</text>')
    for i, se in enumerate(s['series']):
        pts = [(x_of(px), y_of(py)) for px, py in se['points']]
        parts.append(f'<path class="curve s{i + 1}" d="{smooth_path(pts)}"/>')
        lx, ly = pts[-1]
        tb, _ = text_block(lx + 8, ly + 4, se['label'], 16, 't-sm', 'start', 13)
        parts.append(tb)
    h = y0 + 46
    if s.get('note'):
        parts.append(note(h, s['note']))
        h += 16 * len(wrap(s['note'], 95))
    return svg(name, h + 6, ''.join(parts))


def r_bands(name, s):
    bands = s['bands']
    parts = []
    y = 16
    bh = s.get('band_height', 70)
    tops = []
    for b in bands:
        h = bh * (b.get('weight', 1))
        parts.append(box(20, y, W - 40, h - 6, b.get('tone', ''), 8))
        tb, _ = text_block(30, y + 20, b['title'], 60, 't-b')
        parts.append(tb)
        if b.get('lines'):
            tb, _ = text_block(30, y + 38, ' · '.join(b['lines']), 78, 't-sm', 'start', 14)
            parts.append(tb)
        tops.append((y, h))
        y += h
    if s.get('line'):
        pts = [(20 + (W - 40) * px / 100, 16 + (y - 16) * py / 100) for px, py in s['line']]
        parts.append(f'<path class="curve s1" d="{smooth_path(pts)}"/>')
        for m in s.get('markers', []):
            mx = 20 + (W - 40) * m['x'] / 100
            my = 16 + (y - 16) * m['y'] / 100
            parts.append(f'<circle class="halo" cx="{mx:.1f}" cy="{my:.1f}" r="8"/><circle class="f2" cx="{mx:.1f}" cy="{my:.1f}" r="5"/>')
            tb, _ = text_block(mx, my - 12, m['label'], 20, 't-sm', 'middle', 12)
            parts.append(tb)
    if s.get('note'):
        parts.append(note(y + 8, s['note']))
        y += 16 * len(wrap(s['note'], 95)) + 8
    return svg(name, y + 10, ''.join(parts))


def r_stairs(name, s):
    steps = s['steps']
    n = len(steps)
    sw = (W - 40) / n
    rise = 52
    parts = []
    base = 60 + rise * n + 60
    for i, st in enumerate(steps):
        x = 20 + i * sw
        top = base - rise * (i + 1) - 40
        h = base - top
        parts.append(box(x, top, sw - 4, h, st.get('tone', 's' if i == n - 1 else ''), 4))
        tb, nl = text_block(x + 8, top + 18, f'{i + 1}. {st["title"]}', int((sw - 16) / 7.2), 't-b', 'start', 15)
        parts.append(tb)
        tb, _ = text_block(x + 8, top + 18 + nl * 15 + 4, st.get('line', ''), int((sw - 16) / 6.5), 't-sm', 'start', 13)
        parts.append(tb)
    h = base + 8
    if s.get('note'):
        parts.append(note(h, s['note']))
        h += 16 * len(wrap(s['note'], 95))
    return svg(name, h + 6, ''.join(parts))


def r_triangle(name, s):
    v = s['vertices']
    pts = [(320, 84), (110, 364), (530, 364)]
    parts = [f'<polygon class="box" points="{" ".join(f"{x},{y}" for x, y in pts)}"/>']
    labs = [(320, 24, 'middle'), (100, 386, 'start'), (540, 386, 'end')]
    for i in range(3):
        x, y, a = labs[i]
        parts.append(f'<text class="t-b" x="{x}" y="{y}" text-anchor="{a}">{esc(v[i]["title"])}</text>')
        if v[i].get('question'):
            tb, _ = text_block(x, y + 16, v[i]['question'], 30, 't-sm', a, 13)
            parts.append(tb)
    if s.get('center'):
        b, h = titled_box(230, 224, 180, s['center'].get('title', ''), s['center'].get('lines', []), s['center'].get('tone', 'b'))
        parts.append(b)
    h = 436
    if s.get('note'):
        parts.append(note(h, s['note']))
        h += 16 * len(wrap(s['note'], 95))
    return svg(name, h + 6, ''.join(parts))


def r_matrix(name, s):
    cols, rows, cells = s['cols'], s['rows'], s['cells']
    x0, y0 = 150, 50
    cw, ch = (W - x0 - 20) / 2, 120
    parts = []
    for j, c in enumerate(cols):
        parts.append(f'<text class="t-b" x="{x0 + cw * j + cw / 2:.1f}" y="{y0 - 14}" text-anchor="middle">{esc(c)}</text>')
    for i, r in enumerate(rows):
        tb, _ = text_block(x0 - 12, y0 + ch * i + ch / 2 - 4, r, 18, 't-b', 'end', 15)
        parts.append(tb)
        for j in range(2):
            cell = cells[i][j]
            x, y = x0 + cw * j + 3, y0 + ch * i + 3
            parts.append(box(x, y, cw - 6, ch - 6, cell.get('tone', ''), 8))
            parts.append(f'<text class="t-b" x="{x + 10:.1f}" y="{y + 22}">{esc(cell["title"])}</text>')
            tb, _ = text_block(x + 10, y + 40, cell.get('line', ''), int((cw - 20) / 6.6), 't-sm', 'start', 13)
            parts.append(tb)
    h = y0 + ch * 2 + 10
    if s.get('note'):
        parts.append(note(h + 4, s['note']))
        h += 16 * len(wrap(s['note'], 95)) + 4
    return svg(name, h + 6, ''.join(parts))


def r_iceberg(name, s):
    parts = [marker_defs(name)]
    above = s.get('above', [])
    below = s.get('below', [])
    top_h = 24 + len(above) * 22
    wl = top_h + 26
    bot_h = 40 + len(below) * 24
    # partie émergée : trapèze
    parts.append(f'<polygon class="box" points="205,{wl} 435,{wl} 395,{wl - top_h} 245,{wl - top_h}"/>')
    # partie immergée : trapèze large
    parts.append(f'<polygon class="box-p" points="96,{wl} 544,{wl} 474,{wl + bot_h} 166,{wl + bot_h}"/>')
    parts.append(f'<line class="ref" x1="20" y1="{wl}" x2="620" y2="{wl}"/>')
    parts.append(f'<text class="t-sm" x="24" y="{wl - 8}">{esc(s.get("above_label", "ce que je vois"))}</text>')
    parts.append(f'<text class="t-sm" x="24" y="{wl + 18}">{esc(s.get("below_label", "ce qui se passe dessous"))}</text>')
    for i, a in enumerate(above):
        parts.append(f'<text class="t-b" x="320" y="{wl - top_h + 24 + i * 22}" text-anchor="middle">{esc(a)}</text>')
    for i, b in enumerate(below):
        parts.append(f'<text x="320" y="{wl + 34 + i * 24}" text-anchor="middle">{esc(b)}</text>')
    h = wl + bot_h + 14
    if s.get('note'):
        parts.append(note(h, s['note']))
        h += 16 * len(wrap(s['note'], 95))
    return svg(name, h + 6, ''.join(parts))


def r_balance(name, s):
    parts = []
    cx, top = 320, 110
    tilt = s.get('tilt', -6)
    parts.append(f'<polygon class="box-p" points="{cx - 14},{top + 190} {cx + 14},{top + 190} {cx},{top + 10}"/>')
    parts.append(f'<text class="t-b" x="{cx}" y="{top + 214}" text-anchor="middle">{esc(s.get("pivot", ""))}</text>')
    parts.append(f'<g transform="rotate({tilt} {cx} {top + 10})"><line class="line" x1="{cx - 230}" y1="{top + 10}" x2="{cx + 230}" y2="{top + 10}" stroke-width="3"/>'
                 f'<line class="line-soft" x1="{cx - 210}" y1="{top + 10}" x2="{cx - 210}" y2="{top + 60}"/><line class="line-soft" x1="{cx + 210}" y1="{top + 10}" x2="{cx + 210}" y2="{top + 60}"/></g>')
    for side, sx in (('left', cx - 210), ('right', cx + 210)):
        pan = s[side]
        dy = (top + 60 + (10 if side == 'left' else -10)) if tilt < 0 else (top + 60 - (10 if side == 'left' else -10))
        b, h = titled_box(sx - 105, dy - 10, 210, pan.get('title', ''), pan.get('items', []), pan.get('tone', 'b' if side == 'left' else 's'))
        parts.append(b)
    h = top + 240
    if s.get('note'):
        parts.append(note(h, s['note']))
        h += 16 * len(wrap(s['note'], 95))
    return svg(name, h + 6, ''.join(parts))


def r_grid(name, s):
    cols = s['cols']
    rows = s['rows']
    x0 = 130
    cw = (W - x0 - 20) / len(cols)
    parts = []
    y = 30
    for j, c in enumerate(cols):
        tb, _ = text_block(x0 + cw * j + cw / 2, y, c, int(cw / 6.5), 't-b', 'middle', 14)
        parts.append(tb)
    y += 24
    for r in rows:
        cells = r['cells']
        hmax = 0
        for j, c in enumerate(cells):
            hmax = max(hmax, 12 + 13 * len(wrap(c.get('text', c) if isinstance(c, dict) else c, int(cw / 6.6))))
        tb, _ = text_block(x0 - 10, y + 16, r['label'], 16, 't-b', 'end', 14)
        parts.append(tb)
        for j, c in enumerate(cells):
            txt = c.get('text', '') if isinstance(c, dict) else c
            tone = c.get('tone', '') if isinstance(c, dict) else ''
            parts.append(box(x0 + cw * j + 2, y, cw - 4, hmax, tone, 6))
            tb, _ = text_block(x0 + cw * j + 8, y + 16, txt, int(cw / 6.6), 't-sm', 'start', 13)
            parts.append(tb)
        y += hmax + 6
    if s.get('note'):
        parts.append(note(y + 8, s['note']))
        y += 16 * len(wrap(s['note'], 95)) + 8
    return svg(name, y + 10, ''.join(parts))


def r_flow(name, s):
    """Organigramme vertical : étapes numérotées ; une étape peut porter deux branches (oui / non) sous elle."""
    steps = s['steps']
    parts = [marker_defs(name)]
    y = 16
    x0, bw = 130, W - 150
    for i, st in enumerate(steps):
        b, h = titled_box(x0, y, bw, f"{i + 1}. {st.get('title', '')}", st.get('lines', []), st.get('tone', 'p'))
        parts.append(b)
        parts.append(f'<circle class="f1" cx="{x0 - 30}" cy="{y + 20}" r="14"/><text class="on-fill t-b" x="{x0 - 30}" y="{y + 25}" text-anchor="middle">{i + 1}</text>')
        y += h
        br = st.get('branches')
        if br:
            y += 12
            n_br = len(br)
            cw = (bw - 20) / 2 if n_br > 1 else bw * 0.62
            hb = 0
            for j, b2 in enumerate(br):
                bx = x0 + j * (cw + 20) if n_br > 1 else x0 + (bw - cw) / 2
                bb, hh = titled_box(bx, y + 16, cw, b2.get('title', ''), b2.get('lines', []), b2.get('tone', 's' if j == 0 else 'b'))
                parts.append(bb)
                sx = x0 + bw / 2 + ((-40 if j == 0 else 40) if n_br > 1 else 0)
                parts.append(arrow(name, sx, y - 10, bx + cw / 2, y + 14, soft=True))
                hb = max(hb, hh)
            y += 16 + hb
        if i < len(steps) - 1:
            parts.append(arrow(name, x0 + bw / 2, y + 2, x0 + bw / 2, y + 16))
            y += 20
    if s.get('note'):
        parts.append(note(y + 12, s['note']))
        y += 16 * len(wrap(s['note'], 95)) + 12
    return svg(name, y + 12, ''.join(parts))


RENDER = {'fork': r_fork, 'columns': r_columns, 'timeline': r_timeline, 'venn2': lambda n, s: r_venn(n, s, 2), 'venn3': lambda n, s: r_venn(n, s, 3),
          'rings': r_rings, 'cycle': r_cycle, 'chain': r_chain, 'curves': r_curves, 'bands': r_bands, 'stairs': r_stairs, 'triangle': r_triangle,
          'matrix': r_matrix, 'iceberg': r_iceberg, 'balance': r_balance, 'grid': r_grid, 'flow': r_flow}

n = 0
for name, spec in SPECS.items():
    out = RENDER[spec['type']](name, spec).replace('__T__', esc(spec['title'])).replace('__D__', esc(spec['desc']))
    (OUT / f'{name}.svg').write_text(out, encoding='utf-8')
    (OUT / f'{name}.txt').write_text(spec['title'] + '\n' + spec['desc'] + '\n', encoding='utf-8')
    n += 1
print(f'{n} schémas générés dans {OUT.relative_to(ROOT)}')
