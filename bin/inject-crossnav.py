#!/usr/bin/env python3
"""Inject cross-navigation bar into all 7 demos."""
import re

NAV_DATA = {
    'constraint-demos/drift-race.html': {
        'hub': '../simulators/index.html',
        'related': [
            ('⬡ Hex Snap', '../constraint-demos/hex-snap-playground.html'),
            ('🌐 Fleet', '../simulators/fleet-topology.html'),
            ('🦾 Safe Arm', '../simulators/safe-arm.html'),
        ]
    },
    'constraint-demos/hex-snap-playground.html': {
        'hub': '../simulators/index.html',
        'related': [
            ('⚡ Drift Race', '../constraint-demos/drift-race.html'),
            ('⚙️ FLUX VM', '../simulators/flux-vm.html'),
            ('🦾 Safe Arm', '../simulators/safe-arm.html'),
        ]
    },
    'constraint-demos/constraint-funnel.html': {
        'hub': '../simulators/index.html',
        'related': [
            ('🌐 Fleet', '../simulators/fleet-topology.html'),
            ('⚙️ FLUX VM', '../simulators/flux-vm.html'),
            ('🏛️ Palace', '../penrose-memory-palace/index.html'),
        ]
    },
    'simulators/safe-arm.html': {
        'hub': 'index.html',
        'related': [
            ('⬡ Hex Snap', '../constraint-demos/hex-snap-playground.html'),
            ('⚙️ FLUX VM', 'flux-vm.html'),
            ('⚡ Drift Race', '../constraint-demos/drift-race.html'),
        ]
    },
    'simulators/flux-vm.html': {
        'hub': 'index.html',
        'related': [
            ('⬡ Hex Snap', '../constraint-demos/hex-snap-playground.html'),
            ('🦾 Safe Arm', 'safe-arm.html'),
            ('🔽 Funnel', '../constraint-demos/constraint-funnel.html'),
        ]
    },
    'simulators/fleet-topology.html': {
        'hub': 'index.html',
        'related': [
            ('⚡ Drift Race', '../constraint-demos/drift-race.html'),
            ('🔽 Funnel', '../constraint-demos/constraint-funnel.html'),
            ('🏛️ Palace', '../penrose-memory-palace/index.html'),
        ]
    },
    'penrose-memory-palace/index.html': {
        'hub': '../simulators/index.html',
        'related': [
            ('🌐 Fleet', '../simulators/fleet-topology.html'),
            ('🔽 Funnel', '../constraint-demos/constraint-funnel.html'),
            ('⬡ Hex Snap', '../constraint-demos/hex-snap-playground.html'),
        ]
    },
}

NAV_CSS = """
<style id="crossnav-style">
#crossnav{position:fixed;bottom:0;left:0;right:0;z-index:100;background:rgba(8,8,16,.92);backdrop-filter:blur(12px);border-top:1px solid #1a1a30;padding:6px 16px;display:flex;align-items:center;gap:12px;font-family:system-ui,sans-serif;font-size:11px}
#crossnav .hub{color:#7c5cfc;font-weight:700;text-decoration:none;padding:4px 12px;border-radius:6px;border:1px solid #7c5cfc40;background:#7c5cfc10;transition:all .2s;white-space:nowrap}
#crossnav .hub:hover{background:#7c5cfc30;border-color:#7c5cfc}
#crossnav .sep{color:#333}
#crossnav .link{color:#668;text-decoration:none;padding:3px 8px;border-radius:4px;transition:all .2s;white-space:nowrap}
#crossnav .link:hover{color:#aab;background:#ffffff08}
#crossnav .label{color:#444;font-size:10px;text-transform:uppercase;letter-spacing:1px}
body{padding-bottom:38px!important}
</style>
"""

def make_nav_html(data):
    links = ' '.join(f'<a class="link" href="{url}" target="_blank">{name}</a>' for name, url in data['related'])
    return f"""
<div id="crossnav">
  <a class="hub" href="{data['hub']}" target="_blank">⚒️ Universe</a>
  <span class="sep">·</span>
  <span class="label">Related</span>
  {links}
</div>
"""

for filepath, data in NAV_DATA.items():
    try:
        with open(filepath, 'r') as f:
            html = f.read()

        # Skip if already injected
        if 'crossnav' in html:
            print(f"  SKIP (already has crossnav): {filepath}")
            continue

        # Inject CSS before </head>
        html = html.replace('</head>', NAV_CSS + '\n</head>')

        # Inject nav HTML before </body>
        nav_html = make_nav_html(data)
        html = html.replace('</body>', nav_html + '\n</body>')

        with open(filepath, 'w') as f:
            f.write(html)
        print(f"  OK: {filepath}")

    except FileNotFoundError:
        print(f"  SKIP (not found): {filepath}")
