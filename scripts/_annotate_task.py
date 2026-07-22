"""Bake a red 'TASK' label above a node (by id substring) in a mermaid SVG.
Usage: python _annotate_task.py <svg_path> <target_id_substring>
Font size scales with the box height so it looks right on any diagram."""
import re, sys
import xml.etree.ElementTree as ET

SVG = sys.argv[1]
TARGET_ID = sys.argv[2]
SVGNS = "http://www.w3.org/2000/svg"

ET.register_namespace("", SVGNS)
tree = ET.parse(SVG)
root = tree.getroot()

def local(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag

def parse_translate(el):
    t = el.get("transform", "") or ""
    m = re.search(r"translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)", t)
    return (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)

found = {}

def walk(el, cx, cy):
    dx, dy = parse_translate(el)
    ncx, ncy = cx + dx, cy + dy
    rid = el.get("id", "") or ""
    if local(el.tag) == "g" and TARGET_ID in rid and not found:
        rect = None
        for d in el.iter():
            if local(d.tag) in ("rect", "path") and d.get("width"):
                rect = d
                break
        if rect is not None:
            rx = float(rect.get("x", "0")); ry = float(rect.get("y", "0"))
            w = float(rect.get("width")); h = float(rect.get("height"))
            found["cx"] = ncx + rx + w / 2.0
            found["top"] = ncy + ry
            found["h"] = h
        return
    for child in el:
        walk(child, ncx, ncy)

walk(root, 0.0, 0.0)
if not found:
    raise SystemExit("target not found: " + TARGET_ID)

h = found["h"]
fs = max(10.0, round(0.30 * h, 1))
off = round(0.22 * h, 1)
tx = found["cx"]
ty = found["top"] - off
print("box top-center", round(tx, 1), round(found["top"], 1), "h", h, "-> font", fs, "y", round(ty, 1))

txt = ET.SubElement(root, f"{{{SVGNS}}}text")
txt.set("x", f"{tx:.1f}")
txt.set("y", f"{ty:.1f}")
txt.set("text-anchor", "middle")
txt.set("fill", "#ef5350")
txt.set("font-family", "trebuchet ms, Segoe UI, Arial, sans-serif")
txt.set("font-size", f"{fs}")
txt.set("font-weight", "bold")
txt.set("letter-spacing", f"{round(fs*0.08,2)}")
txt.text = "TASK"

tree.write(SVG, encoding="unicode", xml_declaration=False)
print("done")
