#!/bin/bash
# Wait until 12:30 AKDT then fire Claude Code
while [ $(date +%H%M) -lt 1230 ]; do sleep 30; done
cd /home/phoenix/.openclaw/workspace
claude --print --permission-mode bypassPermissions -p "
Read for-fleet/2026-05-03-deep-strategic-analysis.md and for-fleet/2026-05-03-opus-gtm-strategy.md.

Now write the definitive synthesis: for-fleet/2026-05-03-definitive-synthesis.md

You are synthesizing analysis from 22 AI models across 6 rounds of research. This is the document Casey reads to decide the company's future.

Structure:
1. THE HONEST TRUTH: What is actually novel (score each claim) vs what is engineering
2. THE KILLER APP: Independent Runtime Assurance Monitors for autonomous aviation — why this, not something else
3. THE MOAT: Three specific things that prevent Cadence/Siemens from cloning in 18 months
4. WHAT NEEDS DEVELOPMENT: Ranked by impact, with estimated time/cost
5. THE 90-DAY CRITICAL PATH: Specific actions, specific people to talk to, specific milestones
6. THE PAPER: What to write, what venue, what experiments to run
7. THE PATENTS: Which claims survive scrutiny, which don't
8. WHAT KILLS THIS: Honest assessment with mitigations
9. THE GO/NO-GO DECISION: What must be true for Casey to go all-in

Be the best strategic advisor in the world. This document changes everything.
" > /tmp/claude-synthesis-output.txt 2>&1
echo "Claude synthesis complete at $(date)" >> /tmp/claude-synthesis-output.txt
