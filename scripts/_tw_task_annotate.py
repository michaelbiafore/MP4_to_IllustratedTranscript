"""Insert a red 'TASK' label directly above the 'Parse analyst...' box in _tw_top.svg."""
import re
import xml.etree.ElementTree as ET

SVG = r"A:/Packages/Transcript2MDSlides/Input/_tw_top.svg"
SVGNS = "http://www.w3.org/2000/svg"
TARGET = "Parse analyst"

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
    cls = el.get("class", "") or ""
    if local(el.tag) == "g" and re.search(r"\bnode\b", cls) and not found:
        text = "".join(el.itertext())
        if TARGET in text:
            rect = None
            for d in el.iter():
                if local(d.tag) in ("rect", "path") and d.get("width"):
                    rect = d
                    break
            if rect is not None:
                rx = float(rect.get("x", "0"))
                ry = float(rect.get("y", "0"))
                w = float(rect.get("width"))
                h = float(rect.get("height"))
                found["cx"] = ncx + rx + w / 2.0
                found["top"] = ncy + ry
                found["w"] = w
                found["h"] = h
                return
    for child in el:
        walk(child, ncx, ncy)

walk(root, 0.0, 0.0)

if not found:
    raise SystemExit("target box not found")

print("viewBox:", root.get("viewBox"))
print("box center-x:", round(found["cx"], 1), "top-y:", round(found["top"], 1),
      "w:", found["w"], "h:", found["h"])

# TASK label baseline ~18 units above the box top
tx = found["cx"]
ty = found["top"] - 16

txt = ET.SubElement(root, f"{{{SVGNS}}}text")
txt.set("x", f"{tx:.1f}")
txt.set("y", f"{ty:.1f}")
txt.set("text-anchor", "middle")
txt.set("fill", "#ef5350")
txt.set("font-family", "trebuchet ms, Segoe UI, Arial, sans-serif")
txt.set("font-size", "24")
txt.set("font-weight", "bold")
txt.set("letter-spacing", "2")
txt.text = "TASK"

tree.write(SVG, encoding="unicode", xml_declaration=False)
print("Inserted TASK at x=%.1f y=%.1f" % (tx, ty))
