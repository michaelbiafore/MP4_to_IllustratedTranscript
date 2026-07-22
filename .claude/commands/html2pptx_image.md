# HTML to PPTX (Image-Based Export)

Add an in-browser "Export to PPTX" button to a reveal.js HTML slide deck. Each slide is captured as a high-resolution screenshot using html2canvas, then embedded into a PowerPoint file via PptxGenJS.

**Input file**: $ARGUMENTS

## Instructions

1. **Resolve the input file path**:
   - If the path contains only a filename (no directory separators), look for it in the `Input/` directory
   - If the path contains a full path, use that path directly

2. **Read the input HTML file** and verify it is a reveal.js presentation (contains `<div class="reveal">` and `<div class="slides">`)

3. **Derive the output PPTX filename**:
   - Extract the base filename (without path and without `.html` extension)
   - The PPTX filename used in the export script must be: `{base_filename}.pptx`
   - Example: `Upgrade_201_Slides_09.html` → `Upgrade_201_Slides_09.pptx`

4. **Inject the export code** immediately before the closing `</body>` tag. Insert all three blocks in this order:

   **a) CDN script tags:**
   ```html
   <!-- PPTX Export -->
   <script src="https://cdn.jsdelivr.net/npm/pptxgenjs@latest/dist/pptxgen.bundle.js"></script>
   <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
   ```

   **b) Export button:**
   ```html
   <button id="export-btn" onclick="exportToPowerPoint()" style="position: fixed; top: 10px; right: 10px; z-index: 9999; padding: 8px 16px; background: #64b5f6; color: #1a1a2e; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">
     Export to PPTX
   </button>
   ```

   **c) Export script:**
   ```html
   <script>
   async function exportToPowerPoint() {
     const btn = document.getElementById('export-btn');
     btn.textContent = 'Exporting...';
     btn.disabled = true;

     try {
       const pptx = new PptxGenJS();
       pptx.defineLayout({ name: 'WIDE', width: 13.33, height: 7.5 });
       pptx.layout = 'WIDE';

       const revealEl = document.querySelector('.reveal');
       const sections = document.querySelectorAll('.reveal .slides > section');
       const totalSlides = sections.length;

       // Extract logo and compute its natural aspect ratio for correct placement
       const logoEl = document.querySelector('.slide-logo');
       const logoSrc = logoEl ? logoEl.src : null;
       let logoW = 0, logoH = 0.5;
       if (logoSrc) {
         const img = new Image();
         img.src = logoSrc;
         await new Promise(r => { img.onload = r; });
         const aspect = img.naturalWidth / img.naturalHeight;
         logoW = logoH * aspect;
       }

       // Force all fragments visible (they'll be hidden by reveal.js transitions otherwise)
       const fragmentStyle = document.createElement('style');
       fragmentStyle.id = 'pptx-export-fragments';
       fragmentStyle.textContent = '.reveal .fragment { opacity: 1 !important; visibility: visible !important; }';
       document.head.appendChild(fragmentStyle);

       // Hide UI chrome and logo for clean capture (logo added separately)
       const controls = document.querySelector('.reveal .controls');
       const progress = document.querySelector('.reveal .progress');
       if (controls) controls.style.display = 'none';
       if (progress) progress.style.display = 'none';
       if (logoEl) logoEl.style.display = 'none';
       btn.style.display = 'none';

       for (let i = 0; i < totalSlides; i++) {
         Reveal.slide(i);
         await new Promise(r => setTimeout(r, 400));

         const canvas = await html2canvas(revealEl, {
           backgroundColor: '#1a1a2e',
           scale: 2,
           useCORS: true,
           logging: false
         });

         const imgData = canvas.toDataURL('image/png');
         const slide = pptx.addSlide();
         slide.background = { color: '1a1a2e' };
         slide.addImage({ data: imgData, x: 0, y: 0, w: '100%', h: '100%' });

         // Add logo to upper-left corner of every slide
         if (logoSrc) {
           slide.addImage({ data: logoSrc, x: 0.2, y: 0.12, w: logoW, h: logoH });
         }
       }

       // Restore UI
       fragmentStyle.remove();
       if (controls) controls.style.display = '';
       if (progress) progress.style.display = '';
       if (logoEl) logoEl.style.display = '';
       btn.style.display = '';

       await pptx.writeFile({ fileName: 'PPTX_FILENAME' });
     } catch (err) {
       console.error('Export failed:', err);
       alert('Export failed: ' + err.message);
     } finally {
       btn.textContent = 'Export to PPTX';
       btn.disabled = false;
     }
   }
   </script>
   ```

   **IMPORTANT**: Replace the literal string `PPTX_FILENAME` in the script with the actual derived filename from step 3 (e.g., `Upgrade_201_Slides_09.pptx`).

   **Logo handling**: The script looks for an element with class `.slide-logo` (commonly used for fixed-position logos in reveal.js decks). If found, it:
   - Loads the image to determine its natural aspect ratio
   - Computes width from the target height (0.5") to preserve aspect ratio
   - Hides it during html2canvas capture (since `position: fixed` is unreliable with html2canvas)
   - Adds it as a separate PptxGenJS image on every slide at `x: 0.2", y: 0.12"` (upper-left corner)

5. **Handle background color**:
   - Look for the `--r-background-color` CSS variable in the file's `<style>` block
   - Use that color value for both the `html2canvas` `backgroundColor` option and the `slide.background` color in the export script
   - If not found, default to `#1a1a2e`
   - The color in `slide.background` must be specified **without** the `#` prefix (PptxGenJS requirement)

6. **Do NOT modify any existing content** — only append the export block before `</body>`

7. **Write the output file**:
   - Write the modified HTML back to the **same path as the input file** (in-place modification)

8. **Report completion**:
   - Confirm the file was modified
   - State the PPTX filename that will be generated when the user clicks the export button
   - Remind the user: "Open the HTML file in a browser and click **Export to PPTX** to download the PowerPoint file"

## Notes

- This produces image-based slides — text will not be editable in PowerPoint, but visual fidelity is exact
- The 400ms delay between slides allows reveal.js transitions to complete before capture
- `scale: 2` produces high-resolution captures suitable for projection
- The export button is hidden during capture so it doesn't appear in the slides
- Navigation controls and progress bar are also hidden during capture
