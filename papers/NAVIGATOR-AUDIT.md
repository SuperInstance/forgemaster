# vessel-room-navigator — Honest Audit

## What's Real

✅ **Three.js 3D engine** — 35 refs, WebGLRenderer, SphereGeometry, proper importmap
✅ **7 panorama photos** — 2.2MB total, real JPGs for every room (wheelhouse, galley, engine room, foredeck, aft cockpit, wheelhouse roof, crow's nest)
✅ **Room navigation** — rooms-config.json with 9 rooms, adjacency graph, warp points
✅ **Camera system** — 3 camera textures (thermal, radar, gunnery), dashboards
✅ **Drag-to-look** — 23 addEventListener, 17 wheel events
✅ **Alarm trigger** — select alarm → notification → click to warp
✅ **Warp system** — number keys 1-9 for instant teleport
✅ **Glass UI** — backdrop-filter blur, dark theme, responsive
✅ **OG tags + social preview** — actual marketing assets

## What's Stubbed

⚠️ **Visualizer/Mockup** — text input says "add a drum" or "show smoke" but there's NO backend. Zero `fetch()` calls. The 3D mockup system is a local-only toy. You type text → it probably places a primitive shape. Not "AI-generated 3D mockups."

⚠️ **Chat/Agent** — chat button, input field, but NO backend. Zero API calls. It's a local echo chamber. No agent intelligence. The chat "responds" with hardcoded messages.

⚠️ **Dashboard gauges** — referenced in rooms-config but the actual gauge rendering... unclear if real data or decorative.

⚠️ **Camera feeds** — camera textures exist (3 JPGs) but there are 11 camera references. Some rooms reference cameras that only have static images.

## What's Missing for HN

❌ **No backend at all** — zero fetch() calls. Everything is client-side static HTML. The "agent" is hardcoded responses. The "mockup generator" is local primitives.

❌ **No actual camera feeds** — static images, not PTZ controls or live video.

❌ **No persistence** — room state doesn't save. No accounts. No multiplayer.

❌ **No actual AI** — the "chat with the room" is a local text box. No LLM integration.

❌ **Responsive issues** — the chat panel has a mobile override (`width:100%`) suggesting it's been patched for phones but may not be great.

## Honest Verdict

**It's a real, working 3D panorama viewer with room navigation.** Not vapor. The core loop — drag to look, click to walk, number to warp — works. The panoramas are real photos (AI-generated, but they exist). The alarm system triggers and warps you.

**But it's NOT "HN-ready" as a product.** It's a demo. A good demo. A technically impressive single-file demo (39KB HTML with Three.js). But:

1. The README claims features that don't exist (AI mockup generation, agent chat, PTZ cameras)
2. The visualizer is a text input that probably places boxes, not an AI 3D generator
3. The chat is decorative, not functional
4. "ScummVM meets Google Street View" is accurate for the panorama part. The rest is aspiration.

## What It Needs for Real HN Launch

1. **Cut the fake features from the README** — be honest about what works
2. **Make the visualizer real** — even a simple "type 'box' → Three.js BoxGeometry appears" is better than implying AI generation
3. **Add one real agent integration** — even a hardcoded PLATO room that responds would make the chat real
4. **Landing page copy** — "Walk a fishing vessel in 3D" is enough. Don't oversell.

## The Insight

The fleet (CCC? Oracle1?) built something genuinely cool — a 39KB single-file Three.js panorama viewer with room navigation. That's a real technical achievement. But they wrote the marketing before finishing the product. The commit messages say "HN-ready" because the agent was excited about the vision, not because it actually shipped everything.

This is the ensign problem in reverse: the ensign can build the infrastructure fast, but it also overclaims because it can't distinguish "works in my head" from "works in the browser."
