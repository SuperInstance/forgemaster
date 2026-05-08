# Demo Research: Interactive Math & Technology Demonstrations

Compiled 2026-05-07. Sources: web searches, direct page fetches, awesome-interactive-math repo.

---

## 1. Best Interactive Math Visualizations (2020-2025)

### Bartosz Ciechanowski — Tesseract
- **URL:** https://ciechanow.ski/tesseract/
- **What makes it unforgettable:** Takes an impossibly abstract concept (4D geometry) and makes it visceral through step-by-step interactive sliders. You drag sliders to "stretch" dimensions one at a time (point → line → square → cube → tesseract). Each step has a fully interactive 3D widget. The article is essentially a scroll-driven interactive textbook.
- **Technology:** Custom WebGL/Canvas, hand-crafted animations, no framework
- **Interactive element:** Drag 3D objects to rotate, drag sliders to transform between dimensions
- **Load time:** Instant. Pure static site. No build step.
- **Other Ciechanowski demos:** Float Exposed (https://float.exposed/) — bit-level IEEE 754 explorer

### Jez Swanson — Interactive Introduction to Fourier Transforms
- **URL:** https://www.jezzamon.com/fourier/index.html
- **What makes it unforgettable:** The "draw your own wave" section — you doodle any shape and watch it get decomposed into sine waves via epicycles. This single interaction explains Fourier transforms better than any textbook. Went massively viral.
- **Technology:** Canvas 2D, vanilla JavaScript
- **Interactive element:** Draw any waveform, drag sliders to control number of sine waves, watch epicycles trace your drawing
- **Load time:** Instant. Lightweight static page.

### Marc ten Bosch — Let's Remove Quaternions from Every 3D Engine
- **URL:** https://marctenbosch.com/quaternions
- **What makes it unforgettable:** Every single diagram is interactive. Proves that geometric algebra rotors are superior to quaternions by *showing* you rather than telling you. The bivector visualization alone changed how thousands of game devs think about rotation.
- **Technology:** Custom WebGL, interactive diagrams synced with embedded video
- **Interactive element:** Drag 3D vectors, play video segments that correspond to article sections, manipulate bivectors
- **Load time:** Fast

### Steven Wittens — How to Fold a Julia Fractal
- **URL:** https://acko.net/blog/how-to-fold-a-julia-fractal/
- **What makes it unforgettable:** Scroll-triggered WebGL animations that visualize complex number arithmetic as geometric folding. The "turning numbers" metaphor makes imaginary numbers click physically. Set the standard for math explorable articles.
- **Technology:** Three.js, custom GLSL shaders, scroll-driven animation
- **Interactive element:** Scroll to progress through the explanation; embedded interactive widgets
- **Load time:** Moderate (loads Three.js)

### Distill.pub — Why Momentum Really Works
- **URL:** https://distill.pub/2017/momentum/
- **What makes it unforgettable:** Interactive SVG plots that show gradient descent vs momentum in real-time. You drag the step-size and momentum sliders and watch the optimization path change. Made optimization theory feel like a physics simulation.
- **Technology:** D3.js, SVG, custom interactive plots
- **Interactive element:** Sliders for step-size (α) and momentum (β); watch gradient descent animate
- **Load time:** Fast

### Setosa.io — Pythagorean Theorem
- **URL:** https://setosa.io/pythagorean/
- **What makes it unforgettable:** Euclid's proof told through interactive geometry. You watch the proof unfold step by step with animated constructions. Minimalist but laser-focused.
- **Technology:** D3.js, SVG
- **Interactive element:** Step-through proof with animated geometric constructions
- **Load time:** Instant

### Juan Carlos Ponce Campuzano — Complex Analysis
- **URL:** https://complex-analysis.com/
- **What makes it unforgettable:** An entire interactive textbook on complex analysis with embedded applets for domain coloring, conformal mappings, Riemann surfaces. Academic quality, free access.
- **Technology:** Custom JavaScript applets, MathJax
- **Interactive element:** Interactive function plotters, domain coloring tools, drag-to-explore complex maps
- **Load time:** Fast

### ConceptViz — 10 Interactive Math Webpages (2025)
- **URL:** https://conceptviz.github.io/
- **What makes it unforgettable:** Covers Steinmetz Solid, saddle points, dual polyhedra, cross product, Fourier series, conic sections, fractal trees — each as a standalone interactive widget
- **Technology:** WebGL, JavaScript
- **Interactive element:** Drag, rotate, parametrize each mathematical object
- **Load time:** Fast

---

## 2. Explorable Explanations (Bret Victor Tradition)

### Hub & Community
- **URL:** https://explorabl.es/
- **What:** Hub for the "explorable explanations" movement. Curated list of interactive learning demos across math, science, policy. Randomly shows 3 explorables each visit.
- **Philosophy:** "Learning through play" — every demo assumes the user will touch things

### Key Pattern from Bret Victor demos:
1. **No equations first.** Start with a visual or interaction, then reveal the math.
2. **Direct manipulation.** The user touches the thing being explained.
3. **Progressive disclosure.** Complexity builds incrementally through interaction.
4. **Immediate feedback.** Every drag/slider produces instant visual response.
5. **Scroll-driven narrative.** The page IS the explanation, not a container for it.

### Notable Explorable Explanations:
- **Immersive Linear Algebra** — http://immersivemath.com/ila/ — Full interactive linear algebra textbook where every figure is draggable
- **Seeing Circles, Sines and Signals** — https://jackschaedler.github.io/circles-sines-signals — Signal processing made tangible
- **Complexity Explorables** — https://www.complexity-explorables.org/ — Emergent behavior playground (waves, synchronization, flocking)
- **Polyhedra Viewer** — https://polyhedra.tessera.li — 3D polyhedra with real-time transformations
- **Elliptic Curve Explorer** — https://samuelj.li/elliptic-curve-explorer — Drag points on elliptic curves, see group law

---

## 3. 3Blue1Brown-Style Web Demos & Tools

### Tools people use:
| Tool | Type | Notes |
|------|------|-------|
| **Mafs** (https://mafs.dev/) | React components | Opinionated math viz components. Declarative. Good for React apps. |
| **MathBox** (https://github.com/unconed/mathbox) | WebGL library | Presentation-quality math diagrams. Three.js-based. Used by Steven Wittens. |
| **Manim** (Python) | Animation framework | What 3B1B actually uses. Not web-native — outputs video. |
| **D3.js** | Data viz | Go-to for 2D interactive math diagrams. SVG-based. |
| **CindyJS** (https://cindyjs.org/) | Framework | Designed for interactive math content. Good geometry support. |
| **JSXGraph** (http://jsxgraph.org/) | Library | Cross-browser interactive geometry, function plotting |
| **Grafar** (https://thoughtspile.github.io/grafar/) | React+WebGL | Reactive 3D math visualization. Three.js underneath. |
| **Observable** (https://observablehq.com/) | Platform | Notebook-style interactive explorables. Many math demos hosted here. |
| **p5.js** | Creative coding | General creative coding, accessible for artists |
| **MathCell** (https://mathcell.org/) | Simple embed | Straightforward way to include interactive math in a web page |
| **Three.js** | 3D engine | Foundation for most 3D math visualizations |

### For Rust/WASM approach:
- Use `wasm-bindgen` + `web-sys` for DOM/WebGL access
- Render with WebGL2 directly or via `wgpu` (WebGPU backend)
- Consider `wasm-pack` for building

---

## 4. Best WASM Demos (Rust → Browser)

### WAVE: WebAssembly Voxel Engine
- **URL:** https://github.com/skishore/wave
- **What makes it memorable:** Full voxel engine with LOD, dynamic lighting, and smooth performance on old hardware. Started as a rewrite of noa-engine, now WASM-native. 2x-5x speedup over JS original.
- **Technology:** TypeScript + WebAssembly (likely Rust or C++ compiled), WebGL2 custom shaders, run-length encoded chunks
- **Interactive element:** Walk around a procedurally generated voxel world
- **Load time:** Fast (WASM initializes quickly)
- **Key technique:** Custom WebGL2 shaders optimized for voxel terrain; 2D texture arrays for single-draw-call chunk rendering

### Other notable WASM demos:
- **Figma** — Production WASM app. Their entire rendering pipeline is C++ → WASM
- **Google Earth** — Full 3D globe in browser via WASM
- **AutoCAD Web** — Full CAD in browser
- **Various game ports** — Doom, Quake, etc. running in browser via WASM
- **FuzzySearch** — Rust WASM for fast similarity search in browser

### WASM performance patterns:
- Greedy meshing: 5-10x faster in WASM vs JS
- Marching Cubes: 10-50x faster (Rust → WASM vs pure JS)
- Cellular automata (lighting): significant speedup
- Isosurface extraction: major WASM win

---

## 5. Hex Voxel Renderer Feasibility

**Verdict: Entirely feasible, and there's prior art to learn from.**

### Existing work:
- **WAVE engine** (above) — cubic voxels but the architecture would transfer
- **voxel.js** (https://voxel.github.io/voxeljs-site/) — modular browser voxel framework
- **Hex voxel render system** — Reddit post on hexagon vertex shader approach: render cubes as hexagon billboards, then vertex shader transforms them
- **Hex Engine** (https://hex-engine.dev/) — 2D hex grid game engine in TypeScript

### Key challenges for hex voxels:
1. **Mesh generation:** Hex faces instead of axis-aligned quads. More complex geometry per cell.
2. **Data structures:** Run-length encoding works for columns of same-type blocks; hex grids need adapted structures
3. **Shaders:** Can use vertex shaders to project regular geometry as hexagonal — cheaper than generating hex meshes
4. **Greedy meshing:** Needs adaptation for hex adjacency (6 neighbors instead of 4 per face)

### Recommended approach:
- Rust core → WASM for mesh generation, world data
- WebGL2 or WebGPU for rendering
- Custom vertex shaders for hex projection (billboard approach)
- LOD system from WAVE engine

---

## 6. Hex Grid Interactive Visualizations (Existing Work)

### Key resources:
- **Red Blob Games hex grid guide** — https://www.redblobgames.com/grids/hexagons/ — THE definitive reference. Interactive diagrams for every hex grid algorithm (axial coordinates, pixel conversion, pathfinding, line drawing). Built with hand-crafted interactive diagrams.
- **Complexity Explorables** — Some hex-grid based emergent behavior demos
- **HyperRogue** — http://www.roguetemple.com/z/hyper/ — Full game on hyperbolic geometry (hex-like tiling)

### Red Blob Games pattern (the gold standard):
- Every algorithm has an interactive diagram
- Hover/click to see coordinate transformations in real-time
- Tables update live as you move the cursor
- Pure static HTML/JS — no build, instant load
- This is the template for "how to present hex grid math"

---

## 7. Redbean & Show HN Demo Pages

### What makes the best Show HN demos work:
1. **Zero-install.** Click a link, see the thing immediately.
2. **Interactive in <3 seconds.** If the user can't touch it in 3 seconds, they bounce.
3. **One "wow" moment.** Single interaction that makes you say "holy shit."
4. **Progressive depth.** The wow moment is the hook; depth keeps them exploring.
5. **Minimal text.** The demo IS the explanation.
6. **Mobile-hostile is fine.** Most HN readers are on desktop.

### Redbean specifically:
- Single-binary web server (justnode.co) that serves a complete web app
- The demo IS the product — you run the binary and it serves itself
- For a crate landing page: the pattern is "serve the demo from the thing itself"

### Best Rust crate landing pages:
- **Tokio** — https://tokio.rs — Clean, minimal, code-first. Interactive examples inline.
- **Bevy** — https://bevyengine.org — Eye-catching hero animation, interactive 3D demo
- **Dioxus** — https://dioxuslabs.com — Live playground where you can edit code and see results
- **Tauri** — https://v2.tauri.app — Feature comparison table, code samples, dark theme

### Pattern for memorable crate pages:
- Working code example above the fold (not a screenshot — actual runnable code)
- One killer visual that communicates "what this does" in 2 seconds
- Performance benchmarks if relevant (visual, not tables)
- Dark theme is standard for Rust ecosystem

---

## 8. Eisenstein Integer Visualization

### Has anyone done this before?
**Partially, but NOT as a standalone interactive web visualization.**

### What exists:
- **Academic papers** — Eisenstein integers appear in number theory papers with static diagrams of the hexagonal lattice
- **Wolfram MathWorld** — Static images of the lattice
- **Xah Lee's page** — http://xahlee.info/math/Schmidt_Arrangement_Eisenstein_integer_algebra_integer.html — Static diagrams of Schmidt arrangements on Eisenstein integer rings
- **Complex analysis sites** — Mention Eisenstein integers theoretically but don't visualize them interactively
- **YouTube** — Some Numberphile/3B1B-adjacent videos mention them but no dedicated interactive demo

### The gap:
**There is NO prominent interactive web visualization of Eisenstein integers.** This is a wide-open niche. An explorable that shows:
- The hexagonal lattice forming from a + bω
- Eisenstein primes (the analog of prime numbers in this ring)
- Factorization visualized geometrically
- The six-fold rotational symmetry
- Connection to hexagonal crystallography

...would be genuinely novel.

---

## 9. Crystallography Interactive Demos

### Existing work:
- **American Crystallographic Association** — Some Java applets (outdated)
- **CCP14** — Static crystallography resources
- **VESTA** — Desktop app, not web
- **CrystalMaker** — Commercial desktop software
- **Web-based crystallography** is surprisingly thin

### Opportunity:
Crystallography uses the SAME math as Eisenstein integers (hexagonal lattices, symmetry groups). A demo that bridges number theory → crystallography via interactive visualization would serve two communities simultaneously.

---

## Summary: What Makes a Demo Unforgettable

### Common patterns across ALL viral math demos:

1. **Direct manipulation beats animation.** Let users drag, not just watch.
2. **Progressive disclosure.** Start simple, reveal complexity through interaction.
3. **Instant feedback.** Zero latency between input and visual response.
4. **One "aha moment."** Design the whole page around making ONE concept click.
5. **Static hosting.** The best demos are pure HTML/JS/CSS — no server, no build step, no framework. Just open and go.
6. **Canvas/WebGL > SVG for 3D.** SVG for 2D diagrams, Canvas/WebGL for anything with depth.
7. **Vanilla JS wins.** The most impressive demos use minimal dependencies. Three.js is the only common dependency for 3D work.
8. **Scroll-driven narratives.** The page itself is the timeline. No buttons, no menus — just scroll.
9. **Mobile is secondary.** Desktop-first for math demos. Mouse precision matters.
10. **Dark theme optional.** Some of the best (Ciechanowski) use light theme. It's about clarity, not aesthetics.

### Technology stack for a hex lattice / Eisenstein integer demo:

**Recommended: Rust + WASM + WebGL2**
- Rust core for lattice math (prime testing, factorization, neighbor finding)
- WASM via wasm-bindgen for browser integration
- WebGL2 with custom shaders for hex cell rendering
- Vanilla JS for UI controls (sliders, zoom, pan)
- Zero dependencies beyond wasm-bindgen
- Host as static files (serve from redbean or GitHub Pages)

**Alternative: Pure JS + Canvas2D**
- Faster to build, no WASM complexity
- Good enough for 2D hex grid rendering
- Would work for initial prototype
- Upgrade to WASM+WebGL for 3D voxel version

---

## Quick Reference: URLs

| Demo | URL | Tech |
|------|-----|------|
| Ciechanowski Tesseract | https://ciechanow.ski/tesseract/ | Custom WebGL |
| Fourier Transform | https://www.jezzamon.com/fourier/ | Canvas 2D |
| Remove Quaternions | https://marctenbosch.com/quaternions | WebGL + Video |
| Julia Fractal | https://acko.net/blog/how-to-fold-a-julia-fractal/ | Three.js + GLSL |
| Why Momentum Works | https://distill.pub/2017/momentum/ | D3.js + SVG |
| Pythagorean Theorem | https://setosa.io/pythagorean/ | D3.js + SVG |
| Complex Analysis | https://complex-analysis.com/ | Custom JS applets |
| ConceptViz | https://conceptviz.github.io/ | WebGL |
| Hex Grid Guide (Red Blob) | https://www.redblobgames.com/grids/hexagons/ | HTML/JS |
| WAVE Voxel Engine | https://github.com/skishore/wave | WASM + WebGL2 |
| Explorable Explanations | https://explorabl.es/ | Hub |
| Awesome Interactive Math | https://github.com/ubavic/awesome-interactive-math | List |
| Immersive Linear Algebra | http://immersivemath.com/ila/ | Custom WebGL |
| Mafs (React math viz) | https://mafs.dev/ | React |
| MathBox | https://github.com/unconced/mathbox | Three.js |
| Polyhedra Viewer | https://polyhedra.tessera.li | WebGL |
| Float Exposed | https://float.exposed/ | JS |
| Complexity Explorables | https://www.complexity-explorables.org/ | D3.js |
| Elliptic Curve Explorer | https://samuelj.li/elliptic-curve-explorer | JS |
| Eisenstein Integer (static) | http://xahlee.info/math/Schmidt_Arrangement_Eisenstein_integer_algebra_integer.html | Static |
