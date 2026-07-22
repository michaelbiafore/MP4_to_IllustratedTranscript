#!/usr/bin/env python
"""Render an Excalidraw file into per-slide SVG/HTML, sliced at horizontal black
delimiter lines. Faithful (not rough) renderer: images, rects, arrows, lines,
text with excalidraw yellow highlights. Output HTML wrappers are then rasterized
to high-res PNG by msedge (see companion bash loop)."""
import json, sys, os, html, math

SRC = sys.argv[1]
OUTDIR = sys.argv[2]
os.makedirs(OUTDIR, exist_ok=True)

d = json.load(open(SRC, encoding='utf-8'))
files = d.get('files', {})
els = [e for e in d['elements'] if not e.get('isDeleted')]

def esc(s): return html.escape(str(s), quote=True)

# font mapping: excalidraw family 5 = Excalifont (hand-drawn) -> handwritten stack
FONT = {
    1: '"Segoe Print","Bradley Hand","Comic Sans MS",cursive',
    2: '"Segoe UI",Helvetica,Arial,sans-serif',
    3: '"Cascadia Code",Consolas,monospace',
    5: '"Segoe Print","Bradley Hand","Comic Sans MS",cursive',
    6: '"Segoe UI",Helvetica,Arial,sans-serif',
    7: '"Cascadia Code",Consolas,monospace',
}

# ---- scene bounds & delimiter lines ----
lines = [e for e in els if e['type'] == 'line' and e.get('width',0) > 300 and e.get('height',0) < 40]
line_ys = sorted(e['y'] for e in lines)
all_y0 = min(e['y'] for e in els)
all_x0 = min(e['x'] for e in els)
all_x1 = max(e['x'] + e.get('width', 0) for e in els)
PADX = 24
view_x = all_x0 - PADX
view_w = (all_x1 - all_x0) + 2 * PADX

# cut points: top of scene + each delimiter line
cuts = [all_y0 - 16] + line_ys
slides = []
for k in range(len(cuts) - 1):
    top = cuts[k]
    bot = cuts[k + 1]
    # inset below a delimiter line (k>0) so the previous slide's rule isn't shown
    vtop = top + (10 if k > 0 else 0)
    vbot = bot + 4  # include this slide's own bottom rule
    slides.append((vtop, vbot))

def bbox(e):
    return e['x'], e['y'], e['x'] + e.get('width', 0), e['y'] + e.get('height', 0)

def render_element(e):
    t = e['type']
    op = e.get('opacity', 100) / 100.0
    x, y = e['x'], e['y']
    w, h = e.get('width', 0), e.get('height', 0)
    stroke = e.get('strokeColor', '#1e1e1e')
    sw = e.get('strokeWidth', 1)
    bg = e.get('backgroundColor', 'transparent')
    ang = e.get('angle', 0) or 0
    cx, cy = x + w / 2, y + h / 2
    xf = '' if abs(ang) < 1e-6 else f' transform="rotate({math.degrees(ang):.3f} {cx:.2f} {cy:.2f})"'
    out = []
    if t == 'image':
        fid = e.get('fileId')
        f = files.get(fid)
        if not f: return ''
        href = f['dataURL']
        out.append(f'<image x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
                   f'opacity="{op:.2f}" preserveAspectRatio="none" href="{href}"{xf}/>')
    elif t == 'rectangle':
        rx = 0
        if e.get('roundness'):
            rx = min(32, min(abs(w), abs(h)) / 4)
        fill = bg if bg and bg != 'transparent' else 'none'
        out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{rx:.1f}" '
                   f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op:.2f}"{xf}/>')
    elif t in ('line', 'freedraw'):
        pts = e.get('points', [])
        if len(pts) < 2: return ''
        dpts = ' '.join(f'{x+px:.2f},{y+py:.2f}' for px, py in pts)
        fill = bg if (t == 'freedraw' and bg and bg != 'transparent') else 'none'
        out.append(f'<polyline points="{dpts}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
                   f'stroke-linecap="round" stroke-linejoin="round" opacity="{op:.2f}"{xf}/>')
    elif t == 'arrow':
        pts = e.get('points', [])
        if len(pts) < 2: return ''
        dpts = ' '.join(f'{x+px:.2f},{y+py:.2f}' for px, py in pts)
        mk = ' marker-end="url(#arrowhead)"' if e.get('endArrowhead') else ''
        mks = ' marker-start="url(#arrowtail)"' if e.get('startArrowhead') else ''
        out.append(f'<polyline points="{dpts}" fill="none" stroke="{stroke}" stroke-width="{sw}" '
                   f'stroke-linecap="round" stroke-linejoin="round" opacity="{op:.2f}"{mk}{mks}{xf}/>')
    elif t == 'text':
        fs = e.get('fontSize', 20)
        lh = e.get('lineHeight', 1.25)
        fam = FONT.get(e.get('fontFamily', 5), FONT[5])
        color = stroke
        align = e.get('textAlign', 'left')
        anchor = {'left': 'start', 'center': 'middle', 'right': 'end'}.get(align, 'start')
        tx = {'left': x, 'center': x + w / 2, 'right': x + w}.get(align, x)
        # yellow highlight background
        if bg and bg != 'transparent':
            out.append(f'<rect x="{x-3:.2f}" y="{y:.2f}" width="{w+6:.2f}" height="{h:.2f}" '
                       f'fill="{bg}" opacity="{op:.2f}"/>')
        lines_t = e.get('text', '').split('\n')
        spans = []
        for i, ln in enumerate(lines_t):
            by = y + i * lh * fs + fs * 0.82
            spans.append(f'<tspan x="{tx:.2f}" y="{by:.2f}">{esc(ln) if ln else "&#160;"}</tspan>')
        out.append(f'<text font-family={chr(34)}{fam}{chr(34)} font-size="{fs}" fill="{color}" '
                   f'text-anchor="{anchor}" opacity="{op:.2f}"{xf}>{"".join(spans)}</text>')
    return '\n'.join(out)

# z-order: excalidraw draws in array order; keep it
manifest = []
for idx, (vtop, vbot) in enumerate(slides, start=1):
    vh = vbot - vtop
    sel = []
    for e in els:
        ex0, ey0, ex1, ey1 = bbox(e)
        if ey1 >= vtop - 2 and ey0 <= vbot + 2:
            sel.append(e)
    body = '\n'.join(render_element(e) for e in sel)
    body = '\n'.join(s for s in body.split('\n') if s.strip())
    defs = ('<defs>'
            '<marker id="arrowhead" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">'
            '<path d="M0,0 L8,3 L0,6 Z" fill="#1e1e1e"/></marker>'
            '<marker id="arrowtail" markerWidth="10" markerHeight="10" refX="0" refY="3" orient="auto" markerUnits="strokeWidth">'
            '<path d="M8,0 L0,3 L8,6 Z" fill="#1e1e1e"/></marker>'
            '</defs>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{view_w:.0f}" height="{vh:.0f}" '
           f'viewBox="{view_x:.2f} {vtop:.2f} {view_w:.2f} {vh:.2f}">'
           f'{defs}<rect x="{view_x:.2f}" y="{vtop:.2f}" width="{view_w:.2f}" height="{vh:.2f}" fill="#ffffff"/>'
           f'{body}</svg>')
    htmlpage = (f'<!doctype html><html><head><meta charset="utf-8">'
                f'<style>html,body{{margin:0;padding:0;background:#fff}}svg{{display:block}}</style></head>'
                f'<body>{svg}</body></html>')
    with open(os.path.join(OUTDIR, f'slide_{idx:02d}.html'), 'w', encoding='utf-8') as fp:
        fp.write(htmlpage)
    manifest.append({'idx': idx, 'w': round(view_w), 'h': round(vh),
                     'y_top': round(vtop), 'y_bot': round(vbot), 'n_elements': len(sel)})

json.dump(manifest, open(os.path.join(OUTDIR, '_manifest.json'), 'w'), indent=2)
print(f"wrote {len(slides)} slides to {OUTDIR}")
for m in manifest:
    print(f"  slide_{m['idx']:02d}  {m['w']}x{m['h']}  y[{m['y_top']}..{m['y_bot']}]  els={m['n_elements']}")
