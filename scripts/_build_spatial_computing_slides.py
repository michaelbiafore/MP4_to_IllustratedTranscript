"""
Build a portable, self-contained 30-slide reveal.js deck for the
"Spatial Computing: Concept, Applications, Challenges and Future Directions" paper.

Reads:
  - Figures: A:/Packages/Transcript2MDSlides/Input/Spatial_Computing_VR_2026_figs/*.png
  - Reveal assets: A:/Packages/Transcript2MDSlides/.cache/reveal/reveal.min.{css,js}

Writes:
  A:/Packages/Transcript2MDSlides/Output/Spatial_Computing_VR_2026_SLIDES.html

Per project conventions: inlined reveal CSS+JS, base64 images, NO fragments,
dark background (#1a1a2e), blue accent (#64b5f6).
"""
import base64
import textwrap
from pathlib import Path

ROOT = Path(r"A:/Packages/Transcript2MDSlides")
FIGS = ROOT / "Input" / "Spatial_Computing_VR_2026_figs"
REVEAL_DIR = ROOT / ".cache" / "reveal"
OUT_HTML = ROOT / "Output" / "Spatial_Computing_VR_2026_SLIDES.html"

OUT_HTML.parent.mkdir(parents=True, exist_ok=True)

# ---- Load reveal.js inlined ----
reveal_css = (REVEAL_DIR / "reveal.min.css").read_text(encoding="utf-8")
reveal_js = (REVEAL_DIR / "reveal.min.js").read_text(encoding="utf-8")

# Minimal "white" theme look but adapted to dark — keep it simple, define our own CSS below.

# ---- Encode figures as base64 ----
def b64img(name: str) -> str:
    data = (FIGS / name).read_bytes()
    return f"data:image/png;base64,{base64.b64encode(data).decode('ascii')}"

IMG = {
    "fig1": b64img("fig1_Road_Map_of_User_Interfaces.png"),
    "fig2": b64img("fig2_Enabling_Technologies_of_Spatial_Computi.png"),
    "fig3": b64img("fig3_Navigating_the_Spatial_Frontier_Diverse_.png"),
    "fig4": b64img("fig4_Spatial_Computing_Integration_and_Open_C.png"),
    "tab1": b64img("tab1_List_of_key_Acronyms.png"),
    "tab2": b64img("tab2_Immersive_Technolgoies_Comparison_Matrix.png"),
    "tab3": b64img("tab3_Applications_of_Supportive_technologies_.png"),
    "tab4": b64img("tab4_Applications_of_Spatial_Computing.png"),
    "tab5": b64img("tab5_Spatial_Computing_Projects_Dive_into_Des.png"),
}

# ---- Custom CSS layered on top of reveal core ----
CUSTOM_CSS = """
:root{
  --bg:#1a1a2e;
  --bg2:#202044;
  --fg:#eaeaf2;
  --muted:#9aa0c4;
  --accent:#64b5f6;
  --accent2:#9ad0ff;
  --warn:#ef5350;
  --good:#66bb6a;
  --gold:#ffca28;
}
html, body, .reveal{ background:var(--bg); color:var(--fg); }
.reveal{ font-family: "Inter","Segoe UI","Helvetica Neue",Arial,sans-serif; font-size: 30px; }
.reveal .slides{ text-align:left; }
.reveal section{ padding: 0 2.5vw; }
.reveal h1, .reveal h2, .reveal h3{
  color: var(--accent);
  font-weight: 700;
  text-transform: none;
  letter-spacing: 0;
  line-height: 1.15;
}
.reveal h1{ font-size: 2.2em; }
.reveal h2{ font-size: 1.6em; margin-bottom: .3em; }
.reveal h3{ font-size: 1.1em; color: var(--accent2); margin-top: 0; }
.reveal p, .reveal li{ color: var(--fg); line-height:1.45; }
.reveal ul{ margin: .2em 0 0 1.2em; }
.reveal li{ margin: .35em 0; }
.reveal strong{ color: var(--accent2); }
.reveal em{ color: var(--muted); font-style: italic; }
.reveal small, .reveal .small{ color: var(--muted); font-size:.6em; }
.reveal a{ color: var(--accent2); }

.title{
  text-align:center;
}
.title h1{ font-size: 2.6em; margin-bottom:.25em; }
.title .subtitle{ color: var(--accent2); font-size: 1.1em; }
.title .authors{ color: var(--muted); font-size:.55em; margin-top:1.2em; line-height:1.4;}
.title .source{ color: var(--muted); font-size:.5em; margin-top:.8em;}

.bignum{
  font-size: 5.4em;
  font-weight: 800;
  color: var(--accent);
  line-height: 1;
  letter-spacing: -.02em;
}
.bignum.warn{ color: var(--warn); }
.bignum.good{ color: var(--good); }
.bignum.gold{ color: var(--gold); }
.arrow{
  color: var(--muted);
  font-size: 1.5em;
  margin: .3em 0;
}

.center{ text-align:center; }
.flex{ display:flex; gap:2em; align-items:flex-start; }
.flex > div{ flex:1; }
.grid2{ display:grid; grid-template-columns:1fr 1fr; gap:1.4em 2.2em; }
.grid3{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:1.2em 1.6em; }
.grid4{ display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:1em 1.2em; }

.card{
  background: var(--bg2);
  border-left: 4px solid var(--accent);
  padding: .7em .9em;
  border-radius: 6px;
}
.card h3{ margin: 0 0 .35em 0; font-size: .95em; color: var(--accent); }
.card p, .card li{ font-size: .58em; line-height:1.35; margin:.18em 0; }
.card.good{ border-left-color: var(--good); }
.card.good h3{ color: var(--good); }
.card.warn{ border-left-color: var(--warn); }
.card.warn h3{ color: var(--warn); }
.card.gold{ border-left-color: var(--gold); }
.card.gold h3{ color: var(--gold); }

.figwrap{ text-align:center; height: 78vh; display:flex; flex-direction:column; justify-content:center;}
.figwrap img{ max-height: 72vh; max-width: 96vw; margin: 0 auto; }
.figwrap .cap{ color: var(--muted); font-size:.55em; margin-top:.6em; }

.kicker{
  display:inline-block;
  background: var(--bg2);
  color: var(--accent2);
  padding: .15em .6em;
  border-radius: 999px;
  font-size:.5em;
  letter-spacing:.1em;
  text-transform: uppercase;
  margin-bottom: .6em;
}

.tag{
  display:inline-block;
  background: rgba(100,181,246,.15);
  color: var(--accent2);
  padding: .12em .55em;
  border-radius: 4px;
  font-size:.55em;
  margin-right:.35em;
}

.quote{
  font-size: 1.15em;
  font-style: italic;
  color: var(--accent2);
  border-left: 4px solid var(--accent);
  padding-left: .8em;
  margin: .4em 0;
}

.footer{
  position: fixed;
  bottom: 8px;
  right: 14px;
  color: var(--muted);
  font-size: .42em;
  z-index: 20;
}
"""

# ---- Helper to assemble slides ----
def slide(content: str, classes: str = "") -> str:
    cls = f' class="{classes}"' if classes else ""
    return f"      <section{cls}>\n{content}\n      </section>\n"

slides_html: list[str] = []

# 1. Title
slides_html.append(slide(
    """        <div class="title">
          <span class="kicker">arXiv 2402.07912 · Jan 2024 · 35 pages</span>
          <h1>Spatial Computing</h1>
          <div class="subtitle">Concept, Applications, Challenges and Future Directions</div>
          <p class="authors">Gokul Yenduri · Ramalingam M · Praveen Kumar Reddy Maddikunta · Thippa Reddy Gadekallu · Rutvij H Jhaveri · Ajay Bandi · Junxin Chen · Wei Wang · Adarsh Arunkumar Shirawalmath · Raghav Ravishankar · Weizheng Wang</p>
          <p class="source">VIT-AP · VIT · Lovely Professional Univ · PDEU · NWMSU · DUT · MSU-BIT · CityU HK</p>
        </div>"""
))

# 2. Why this matters — market size
slides_html.append(slide(
    """        <h2>Why this matters</h2>
        <div class="flex" style="margin-top:1em;">
          <div class="center">
            <div class="bignum">$102B</div>
            <p class="small">Market size · 2021</p>
          </div>
          <div class="center"><div class="arrow">→</div></div>
          <div class="center">
            <div class="bignum gold">$544B</div>
            <p class="small">Projected · 2032</p>
          </div>
        </div>
        <p style="margin-top:1.2em;">A <strong>5×</strong> market expansion in a decade — driven by AR/VR/MR, IoT, AI, and the immersive web.</p>
        <p><em>"Spatial computing… coined by Simon Greenwold (MIT, 2003) — machines that retain and manipulate referents to real-world objects and surroundings."</em></p>"""
))

# 3. The Big Idea — Definition
slides_html.append(slide(
    """        <h2>The Big Idea</h2>
        <p>Spatial computing <strong>blends the real and virtual worlds</strong> — enabling humans and machines to interact in a shared spatial context.</p>
        <div class="grid3" style="margin-top:1em;">
          <div class="card">
            <h3>AR · overlay</h3>
            <p>Adds digital content <em>on top of</em> the real world.</p>
          </div>
          <div class="card good">
            <h3>VR · replace</h3>
            <p>Replaces the real world with a simulated one.</p>
          </div>
          <div class="card gold">
            <h3>Spatial · blend</h3>
            <p>Real <em>+</em> virtual coexist with spatial awareness, mapping, and intent.</p>
          </div>
        </div>
        <p style="margin-top:1em;"><em>2023 inflection point: Apple Vision Pro, Meta Quest Pro, Magic Leap 2.</em></p>"""
))

# 4. Figure 1 — Road map of UIs
slides_html.append(slide(
    f"""        <h2>60 years of user interfaces</h2>
        <div class="figwrap">
          <img src="{IMG['fig1']}" alt="Road Map of User Interfaces"/>
          <div class="cap">Figure 1 · Road Map of User Interfaces — from command line to spatial computing</div>
        </div>"""
))

# 5. Acronyms (Table 1)
slides_html.append(slide(
    f"""        <h2>Key acronyms</h2>
        <div class="figwrap">
          <img src="{IMG['tab1']}" alt="Acronyms" style="max-height:68vh;"/>
          <div class="cap">Table 1 · Vocabulary used throughout the paper</div>
        </div>"""
))

# 6. Comparison matrix (Table 2)
slides_html.append(slide(
    f"""        <h2>AR vs VR vs Spatial Computing</h2>
        <div class="figwrap">
          <img src="{IMG['tab2']}" alt="Immersive Technologies Comparison"/>
          <div class="cap">Table 2 · Side-by-side comparison across hardware, interaction, immersion, and use cases</div>
        </div>"""
))

# 7. Six enabling technologies — title card
slides_html.append(slide(
    """        <h2>Six enabling technologies</h2>
        <p>Spatial computing is not one thing — it is the <strong>convergence</strong> of six maturing stacks.</p>
        <div class="grid3" style="margin-top:1.2em;">
          <div class="card"><h3>01 · AI</h3><p>Scene understanding · object tracking · gesture recognition</p></div>
          <div class="card"><h3>02 · IoT</h3><p>Depth sensors · LiDAR · RGB · HMDs · GPUs</p></div>
          <div class="card"><h3>03 · 5G & Beyond</h3><p>Ultra-low latency · haptic feedback · real-time data</p></div>
          <div class="card"><h3>04 · Cloud / Edge</h3><p>3D storage · render offload · on-device privacy</p></div>
          <div class="card"><h3>05 · Extended Reality</h3><p>AR + VR + MR · the user-facing surface</p></div>
          <div class="card"><h3>06 · Blockchain</h3><p>Geospatial integrity · smart contracts · dApps</p></div>
        </div>"""
))

# 8. Figure 2 — Enabling technologies diagram
slides_html.append(slide(
    f"""        <h2>The enabling-tech stack, visualized</h2>
        <div class="figwrap">
          <img src="{IMG['fig2']}" alt="Enabling Technologies of Spatial Computing"/>
          <div class="cap">Figure 2 · Six enablers and the application surfaces each unlocks</div>
        </div>"""
))

# 9. AI
slides_html.append(slide(
    """        <span class="kicker">Enabler 01</span>
        <h2>AI: the perceiver</h2>
        <ul>
          <li><strong>Computer vision</strong> identifies walls, furniture, surfaces — and builds a live 3D representation.</li>
          <li><strong>Occlusion handling</strong> so virtual objects hide correctly behind real ones.</li>
          <li><strong>Tracking systems</strong> — inside-out, outside-in, hand, body, eye, positional audio.</li>
          <li><strong>SLAM</strong> (Simultaneous Localization & Mapping) anchors content as the user moves.</li>
          <li><strong>Foveated rendering</strong> — render only where the eyes look.</li>
        </ul>
        <p class="small" style="margin-top:1em;"><em>Without AI, there is no "spatial" — only a passive overlay.</em></p>"""
))

# 10. IoT
slides_html.append(slide(
    """        <span class="kicker">Enabler 02</span>
        <h2>IoT + sensors: the body</h2>
        <ul>
          <li><strong>Depth + LiDAR + RGB + IR</strong> sensors gather the geometry of the room.</li>
          <li><strong>HMDs and smart glasses</strong> are the display surface — light, untethered.</li>
          <li><strong>GPUs</strong> render high-quality 3D in real time — lighting, shadows, physics.</li>
          <li><strong>Smartphones &amp; tablets</strong> remain the lowest-friction entry point.</li>
        </ul>
        <p class="quote" style="margin-top:1em;">"The combination of sensors + GPUs + HMDs is what makes immersion <em>real</em>, not just possible."</p>"""
))

# 11. 5G/6G
slides_html.append(slide(
    """        <span class="kicker">Enabler 03</span>
        <h2>5G &amp; beyond: the wire</h2>
        <div class="grid2">
          <div>
            <ul>
              <li><strong>Ultra-low latency</strong> — sub-10 ms for AR/VR loops.</li>
              <li><strong>High bandwidth</strong> — stream point clouds and volumetric video.</li>
              <li><strong>Network slicing</strong> — dedicated lanes per application class.</li>
              <li><strong>Haptic feedback</strong> — touch becomes networkable.</li>
            </ul>
          </div>
          <div>
            <div class="card"><h3>6G horizon</h3>
            <p>Tactile internet at scale: feel a virtual object as if it were in your hand. Architecture, surgery, remote control of physical machines all become co-presence experiences.</p>
            </div>
          </div>
        </div>"""
))

# 12. Cloud / Edge
slides_html.append(slide(
    """        <span class="kicker">Enabler 04</span>
        <h2>Cloud + edge: the split brain</h2>
        <div class="grid2">
          <div>
            <h3>Cloud</h3>
            <ul>
              <li>Holds the heavy 3D assets, world maps, geospatial datasets.</li>
              <li>Renders complex scenes and runs cross-user analytics.</li>
              <li>Enables shared/collaborative spatial experiences.</li>
            </ul>
          </div>
          <div>
            <h3>Edge</h3>
            <ul>
              <li>Cuts round-trip latency for real-time interaction.</li>
              <li>Keeps sensitive sensor data <strong>local</strong> — privacy + GDPR-friendly.</li>
              <li>Offloads compute from the headset → longer battery, lighter device.</li>
            </ul>
          </div>
        </div>"""
))

# 13. Extended Reality
slides_html.append(slide(
    """        <span class="kicker">Enabler 05</span>
        <h2>Extended Reality (XR)</h2>
        <p>The user-facing layer — three modes, one continuum.</p>
        <div class="grid3" style="margin-top:1em;">
          <div class="card">
            <h3>AR</h3>
            <p>Context-aware overlays · spatial cues for navigation · gesture and gaze-driven interfaces.</p>
          </div>
          <div class="card good">
            <h3>VR</h3>
            <p>Training simulations · virtual tours · spatial design · collaborative virtual workspaces.</p>
          </div>
          <div class="card gold">
            <h3>MR</h3>
            <p>Spatial anchors · digital objects that respect physical geometry · hands-free interaction.</p>
          </div>
        </div>"""
))

# 14. Blockchain
slides_html.append(slide(
    """        <span class="kicker">Enabler 06</span>
        <h2>Blockchain: trust for geospatial data</h2>
        <ul>
          <li><strong>Tamper-proof ledger</strong> for location-based information — navigation, logistics, urban planning.</li>
          <li><strong>Smart contracts</strong> for geospatial asset trading, location-based ads, microtransactions.</li>
          <li><strong>Decentralized data marketplaces</strong> — users own and monetize their location data.</li>
          <li><strong>dApps</strong> for AR/VR experiences, location-based gaming, decentralized navigation.</li>
        </ul>
        <p class="small" style="margin-top:1em;"><em>Open question: scalability and energy cost remain real frictions.</em></p>"""
))

# 15. Table 3 — Supportive technologies
slides_html.append(slide(
    f"""        <h2>Supportive technologies — and their trade-offs</h2>
        <div class="figwrap">
          <img src="{IMG['tab3']}" alt="Applications of supportive technologies"/>
          <div class="cap">Table 3 · AR · VR · MR · Spatial Mapping · Holography · Spatial Audio — each with its own ceiling</div>
        </div>"""
))

# 16. 9 application domains — title card
slides_html.append(slide(
    """        <h2>Nine industries, nine reinventions</h2>
        <div class="grid3" style="margin-top:1.4em;">
          <div class="card"><h3>Education</h3><p>Immersive labs, 3D models, collaborative learning.</p></div>
          <div class="card"><h3>Manufacturing</h3><p>Digital twins, AR-guided assembly, QC.</p></div>
          <div class="card"><h3>Gaming / Entertainment</h3><p>Markerless tracking, 3D audio, location-based play.</p></div>
          <div class="card good"><h3>Healthcare</h3><p>Surgical navigation, training, telemedicine.</p></div>
          <div class="card good"><h3>E-Commerce</h3><p>Virtual try-on, AR shopping, immersive stores.</p></div>
          <div class="card good"><h3>Architecture</h3><p>3D walkthroughs, clash detection, client engagement.</p></div>
          <div class="card gold"><h3>Tourism</h3><p>Virtual visits, on-site AR, cultural preservation.</p></div>
          <div class="card gold"><h3>Transportation</h3><p>AR head-up displays, AV perception, traffic mgmt.</p></div>
          <div class="card gold"><h3>Military</h3><p>Situational awareness, training, supply chain.</p></div>
        </div>"""
))

# 17. Table 4 — Applications by sector
slides_html.append(slide(
    f"""        <h2>Applications — challenges, solutions, supporting tech</h2>
        <div class="figwrap">
          <img src="{IMG['tab4']}" alt="Applications of Spatial Computing"/>
          <div class="cap">Table 4 · Per-sector challenges → spatial-computing applications → the technologies that power them</div>
        </div>"""
))

# 18. Figure 3 — diverse applications
slides_html.append(slide(
    f"""        <h2>The application surface, mapped</h2>
        <div class="figwrap">
          <img src="{IMG['fig3']}" alt="Diverse Applications of Spatial Computing"/>
          <div class="cap">Figure 3 · Four flagship use cases per industry — 32 concrete applications</div>
        </div>"""
))

# 19. Healthcare + Education
slides_html.append(slide(
    """        <h2>Healthcare · Education</h2>
        <div class="grid2">
          <div class="card good">
            <h3>Healthcare</h3>
            <p><strong>Surgical precision</strong> — 3D anatomical overlays during procedures.</p>
            <p><strong>Training</strong> — virtual patients with rare pathologies.</p>
            <p><strong>Telemedicine</strong> — clinicians "appear" in the patient's room.</p>
            <p><strong>Atlas EHR</strong> — spatial vision model for patient histories <em>[Farhadloo et al.]</em>.</p>
          </div>
          <div class="card">
            <h3>Education</h3>
            <p><strong>Immersive learning</strong> — VR field trips, historical contexts.</p>
            <p><strong>Hands-on practice</strong> in environments too dangerous or expensive in reality.</p>
            <p><strong>Magic Leap remote class</strong> — 10-week MR cohort reported higher engagement vs Zoom <em>[Akers et al.]</em>.</p>
          </div>
        </div>"""
))

# 20. Manufacturing + Gaming
slides_html.append(slide(
    """        <h2>Manufacturing · Gaming &amp; Entertainment</h2>
        <div class="grid2">
          <div class="card">
            <h3>Manufacturing</h3>
            <p><strong>Digital twins</strong> for production lines — simulate before you build.</p>
            <p><strong>AR-guided assembly</strong> reduces error and training time.</p>
            <p><strong>Remote maintenance</strong> — experts annotate machinery in technicians' field of view.</p>
            <p><strong>Quality control</strong> — vision-driven defect detection.</p>
          </div>
          <div class="card gold">
            <h3>Gaming &amp; Entertainment</h3>
            <p><strong>Immersive storytelling</strong> — interactive 3D environments.</p>
            <p><strong>Spatial audio</strong> — sound that responds to room geometry.</p>
            <p><strong>Location-based games</strong> — Pokémon Go was just the start.</p>
            <p><strong>Photogrammetry</strong> translates physical spaces into game worlds.</p>
          </div>
        </div>"""
))

# 21. E-commerce + Architecture
slides_html.append(slide(
    """        <h2>E-Commerce · Architectural Design</h2>
        <div class="grid2">
          <div class="card">
            <h3>E-Commerce</h3>
            <p><strong>Virtual try-on</strong> — clothing, eyewear, cosmetics on your own avatar.</p>
            <p><strong>3D product visualization</strong> — rotate, zoom, examine before purchase.</p>
            <p><strong>Immersive storefronts</strong> — walk the aisles in VR.</p>
            <p><strong>AR ads</strong> — products previewed in your real room.</p>
          </div>
          <div class="card good">
            <h3>Architecture</h3>
            <p><strong>VR walkthroughs</strong> of buildings before construction begins.</p>
            <p><strong>AR overlays</strong> on physical sites — see proposed designs in context.</p>
            <p><strong>Shapespark</strong> — browser-based collaborative architectural VR.</p>
            <p><strong>Clash detection</strong> in 3D before clash on site.</p>
          </div>
        </div>"""
))

# 22. Tourism + Transportation + Military
slides_html.append(slide(
    """        <h2>Tourism · Transportation · Military</h2>
        <div class="grid3">
          <div class="card">
            <h3>Tourism</h3>
            <p><strong>Google Earth VR</strong> — try before you fly.</p>
            <p><strong>Wikitude</strong> overlays history on the street.</p>
            <p><strong>Smart-city IoT</strong> — real-time parking, traffic, weather.</p>
          </div>
          <div class="card good">
            <h3>Transportation</h3>
            <p><strong>BMW AR HUD</strong> — directions on the windshield.</p>
            <p><strong>Google Maps Live View</strong> — AR navigation through the phone.</p>
            <p><strong>AV perception</strong> — spatial maps for safer self-driving.</p>
          </div>
          <div class="card gold">
            <h3>Military</h3>
            <p><strong>IVAS</strong> — Microsoft's $21.9B HoloLens contract with the US Army.</p>
            <p><strong>Situational awareness</strong> — sensor feeds in the soldier's field of view.</p>
            <p><strong>Geospatial mission planning</strong> in shared 3D space.</p>
          </div>
        </div>"""
))

# 23. 9 projects — title card
slides_html.append(slide(
    """        <h2>Nine projects on the frontier</h2>
        <p>The paper surveys nine concrete projects — five research/applications, four shipped devices.</p>
        <div class="grid3" style="margin-top:1em;">
          <div class="card"><h3>Neuralangelo</h3><p>NVIDIA · 3D reconstruction from RGB video.</p></div>
          <div class="card"><h3>ProjectDR</h3><p>Univ. Alberta · diagnostic images projected on patient skin.</p></div>
          <div class="card"><h3>Polycam</h3><p>LiDAR-driven 3D scanning on iPhone / iPad.</p></div>
          <div class="card good"><h3>Project Florence</h3><p>Microsoft Research · talk to a plant via NLP + light.</p></div>
          <div class="card good"><h3>IKEA Kreativ</h3><p>Scan a room, place IKEA furniture in AR before buying.</p></div>
          <div class="card good"><h3>Magic Leap 2</h3><p>70° FOV MR headset for medicine and engineering.</p></div>
          <div class="card gold"><h3>Apple Vision Pro</h3><p>visionOS · M2+R1 chips · 23 MP dual displays.</p></div>
          <div class="card gold"><h3>Microsoft HoloLens</h3><p>Waveguide optics · enterprise + military mainstay.</p></div>
          <div class="card gold"><h3>Meta Quest Pro</h3><p>Eye + face tracking · foveated render · color passthrough.</p></div>
        </div>"""
))

# 24. Table 5 — Projects table
slides_html.append(slide(
    f"""        <h2>Projects — at a glance</h2>
        <div class="figwrap">
          <img src="{IMG['tab5']}" alt="Spatial Computing Projects"/>
          <div class="cap">Table 5 · Descriptions, applications, advantages, and current limitations of all nine projects</div>
        </div>"""
))

# 25. Devices in the wild
slides_html.append(slide(
    """        <h2>Devices in the wild</h2>
        <div class="grid4" style="margin-top:.8em;">
          <div class="card gold">
            <h3>Apple Vision Pro</h3>
            <p>Dual 4K micro-OLED · M2 + R1 · 12 ms passthrough · eye, hand, voice control.</p>
            <p class="small"><em>Paradigm shift — "infinite canvas" with visionOS.</em></p>
          </div>
          <div class="card">
            <h3>Magic Leap 2</h3>
            <p>70° FOV · half the weight of v1 · global dimmer for VR-like blackout in AR.</p>
            <p class="small"><em>Enterprise focus: medicine + engineering.</em></p>
          </div>
          <div class="card good">
            <h3>Microsoft HoloLens</h3>
            <p>Waveguide optics with diffraction gratings · Intel x86 inside.</p>
            <p class="small"><em>IVAS: $21.9B / 10 yr / 120,000 units, US Army.</em></p>
          </div>
          <div class="card">
            <h3>Meta Quest Pro</h3>
            <p>Color passthrough · eye + face tracking · foveated render · no hardware depth.</p>
            <p class="small"><em>VR-first with MR ambitions.</em></p>
          </div>
        </div>"""
))

# 26. Research projects
slides_html.append(slide(
    """        <h2>Research &amp; applications worth watching</h2>
        <div class="grid3" style="margin-top:.6em;">
          <div class="card">
            <h3>Neuralangelo (NVIDIA)</h3>
            <p>SDF + Color MLPs · multi-resolution hash encoding · phone video → high-fidelity 3D mesh.</p>
          </div>
          <div class="card good">
            <h3>ProjectDR</h3>
            <p>Diagnostic images projected onto the patient's skin · CV + 3D model corrects for body topography.</p>
          </div>
          <div class="card">
            <h3>Polycam</h3>
            <p>LiDAR-driven point clouds → AR-rendered meshes · 3D scans from a phone.</p>
          </div>
          <div class="card gold">
            <h3>Project Florence</h3>
            <p>NLP sentiment → light frequency to plants · plant bio-signals → spoken response.</p>
          </div>
          <div class="card good">
            <h3>IKEA Kreativ</h3>
            <p>LiDAR room scan + VR placement · seamless add-to-cart from the immersive view.</p>
          </div>
          <div class="card">
            <h3>Reference platforms</h3>
            <p>Shapespark (architecture) · Wikitude (tourism AR) · Google Earth VR (virtual travel).</p>
          </div>
        </div>"""
))

# 27. Figure 4 — challenges
slides_html.append(slide(
    f"""        <h2>What still gets in the way</h2>
        <div class="figwrap">
          <img src="{IMG['fig4']}" alt="Integration and Open Challenges"/>
          <div class="cap">Figure 4 · Nine open problems with the paper's proposed solutions</div>
        </div>"""
))

# 28. Top challenges
slides_html.append(slide(
    """        <h2>The hard problems</h2>
        <div class="grid2">
          <div>
            <ul>
              <li><strong>Interoperability</strong> — every vendor a silo; no shared APIs.</li>
              <li><strong>Sensor fusion</strong> — accelerometer + camera + gyro drift apart in real time.</li>
              <li><strong>Latency</strong> — anything over ~20 ms breaks presence.</li>
              <li><strong>Hardware cost</strong> — Vision Pro at $3.5k is not mass-market.</li>
              <li><strong>Content creation</strong> — 3D pipelines are still bespoke.</li>
            </ul>
          </div>
          <div>
            <ul>
              <li><strong>Privacy</strong> — eye, gaze, room geometry, biometrics — all leakable.</li>
              <li><strong>Motion sickness</strong> — up to <strong>10%</strong> of adults affected in fully-autonomous vehicles <em>[UMTRI study]</em>.</li>
              <li><strong>Regulation</strong> — GDPR-style frameworks haven't caught up.</li>
              <li><strong>UX design</strong> — 2D habits don't translate to 3D.</li>
              <li><strong>User education</strong> — the on-ramp is steep.</li>
            </ul>
          </div>
        </div>"""
))

# 29. Solutions & future directions
slides_html.append(slide(
    """        <h2>The path forward</h2>
        <div class="grid2">
          <div class="card good">
            <h3>Technical levers</h3>
            <p><strong>Edge + on-device ML</strong> for latency and privacy.</p>
            <p><strong>Open APIs &amp; standards</strong> for cross-platform interop.</p>
            <p><strong>Adaptive sensor fusion</strong> (Kalman filters, learned calibration).</p>
            <p><strong>Distributed compute</strong> (Spark, R-tree, spatial indexing).</p>
            <p><strong>Haptic interfaces</strong> — touch makes virtual things feel real.</p>
          </div>
          <div class="card gold">
            <h3>Human levers</h3>
            <p><strong>Internal ethics committees</strong> at every vendor — not just legal review.</p>
            <p><strong>Privacy-preserving capture</strong> by default; transparent consent.</p>
            <p><strong>Universal-design accessibility</strong> baked into the OS, not bolted on.</p>
            <p><strong>Affordable hardware tiers</strong> for underserved communities.</p>
            <p><strong>Standardized usage guidelines</strong> for VR/AR health &amp; safety.</p>
          </div>
        </div>"""
))

# 30. Conclusion
slides_html.append(slide(
    """        <div class="title" style="margin-top:2vh;">
          <span class="kicker">Takeaway</span>
          <h1>The next interface is the room.</h1>
          <p style="color:var(--accent2); font-size:1.1em; margin-top:1em;">
            Spatial computing collapses the boundary between digital and physical —
            and it is arriving on the back of <strong>six maturing tech stacks</strong>,
            across <strong>nine industries</strong>, through <strong>nine flagship projects</strong>.
          </p>
          <p style="color:var(--fg); margin-top:1.3em;">
            The open work is in <strong>interoperability</strong>, <strong>privacy</strong>, and <strong>making it feel good to wear for eight hours</strong>.
          </p>
          <p class="source" style="margin-top:2em;">Yenduri et al. · arXiv 2402.07912 · January 2024</p>
        </div>"""
))

assert len(slides_html) == 30, f"expected 30 slides, got {len(slides_html)}"

# ---- Assemble final HTML ----
html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Spatial Computing — Concept, Applications, Challenges and Future Directions</title>
<style>
{reveal_css}
{CUSTOM_CSS}
</style>
</head>
<body>
<div class="reveal">
  <div class="slides">
{''.join(slides_html)}
  </div>
</div>
<div class="footer">Spatial Computing · Yenduri et al. (arXiv 2402.07912, 2024)</div>
<script>
{reveal_js}
</script>
<script>
Reveal.initialize({{
  hash: true,
  history: false,
  controls: true,
  progress: true,
  slideNumber: 'c/t',
  transition: 'slide',
  width: 1280,
  height: 720,
  margin: 0.04,
  minScale: 0.2,
  maxScale: 1.6
}});
</script>
</body>
</html>
"""

OUT_HTML.write_text(html, encoding="utf-8")
print(f"wrote: {OUT_HTML}  ({OUT_HTML.stat().st_size:,} bytes, {len(slides_html)} slides)")
