import sys
from playwright.sync_api import sync_playwright

src = sys.argv[1]
out = sys.argv[2]
url = "file:///" + src.replace("\\", "/")

W, H = 1280, 775

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
    pg.goto(url, wait_until="networkidle", timeout=120000)
    pg.wait_for_timeout(1500)
    # hide on-screen chrome so the markup PDF is clean
    pg.add_style_tag(content=(
        ".reveal .controls,.reveal .progress,.reveal .slide-number,"
        ".reveal .backgrounds .slide-background .slide-number{display:none!important}"
    ))
    total = pg.evaluate("Reveal.getTotalSlides()")
    print("slides:", total)
    images = []
    for i in range(total):
        pg.evaluate("Reveal.slide(%d)" % i)
        pg.wait_for_timeout(450)  # allow fade transition + bg swap
        png = "Output/Slides/_canary_pg_%02d.png" % i
        pg.screenshot(path=png, clip={"x": 0, "y": 0, "width": W, "height": H})
        images.append(png)
    b.close()

# assemble into PDF, one slide per page, no white margins
import img2pdf
with open(out, "wb") as f:
    f.write(img2pdf.convert(images))
print("wrote", out, "pages:", len(images))
