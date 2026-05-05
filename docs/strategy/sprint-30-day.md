# The 30-Day Sprint Plan (Adversarial)

## Week 1 Build Plan (DeepSeek Reasoner)

**Strategic Analysis & Execution Plan: SuperInstance Q2 Push**

**Executive Summary**  
SuperInstance possesses a unique combination of assets: a verified formal reasoning ecosystem (FLUX repos + 23+ proofs), an autonomous AI development fleet, and an extremely constrained human resource (2 hrs/day). To maximize real-world impact in aerospace/automotive within 30 days, we must **ship one deeply verified, demonstrable proof-of-concept** that directly addresses a high-value regulatory pain point. The target is not a full product but a **verifiable safety argument** that can be shown to procurement teams at Tier 1 suppliers (Bosch, Denso, Safran) and standards bodies (ISO 26262 working groups).  

**Strategic Thrust: Formal Assurance for Autonomous Decision-Making**  
- **Why now:** Both aerospace (DO-178C DAL A) and automotive (ISO 26262 ASIL D) require rigorous verification. Existing tools (model checkers, theorem provers) are slow, manual, and costly. FLUX repos + proofs offer a **lightweight, AI-driven verification pipeline** that can be demonstrated in a single afternoon.  
- **The bet:** If we can show a 100-line control law verified in 3 minutes by a fully automated AI pipeline—including counterexample generation and proof certificate—we will trigger licensing discussions.  

---

## 1. Repos & Work Allocation

**Active repos (7 of 1000+):**  
1. **flux-core** – The FLUX inference engine (proof generation, tactic synthesis).  
2. **flux-verifier** – Wraps FLUX into a REPL/API for target languages (C, Python, Rust).  
3. **flux-auto-synth** – Synthesizes formal contracts from natural-language specs (LTL, STL, Coq).  
4. **flux-bench** – Benchmark suite of 100+ industrial control problems (from Unmanned Aerial Vehicle (UAV) stabilization to automotive adaptive cruise control).  
5. **flux-docs** – Documentation + interactive tutorial generator (Jupyter Book).  
6. **flux-demo-lab** – Docker-compose environment for reproducing any proof in under 5 minutes.  
7. **flux-partner-guide** – REST API specification and partnership onboarding materials.  

**Work allocation (AI fleet + 2 human hrs/day):**  
- **Human hours (primary):** Final verification of demo script, one external email/call per day, code review of AI-generated PRs.  
- **AI fleet (24/7):** Bug fixes, new tactic generation, auto-documentation, benchmark execution, simulation integration, Docker image hardening.  

**What gets built:**  
- **Week 1–2:**  
  - **flux-auto-synth v0.4:** Accepts natural-language description (e.g., “keep vehicle 2 meters behind lead car, reset on red light”) and outputs a formally verified STL contract.  
  - **flux-verifier plugin for simulation:** Real-time monitoring of a Carla/Webots simulation against the synthesized contract, with automatic proof logging.  
  - **flux-demo-lab v1.1:** Single `docker compose up` spins up a web UI showing: input spec → FLUX proof tree → live simulation → error trace if violated.  
- **Week 3–4:**  
  - **flux-bench expansion:** Add 20 new aerospace/automotive benchmarks (collision avoidance, thrust allocation, sensor fusion).  
  - **flux-docs v2.0:** Include a “Partner Quickstart” section with 3 pre-built case studies (UAV waypoint, lane-keeping, cruise control).  
  - **flux-partner-guide:** Generated from AI fleet’s analysis of 500+ RFPs and white papers from Bosch, Safran, Airbus, and SAE International.  

**Features that ship:**  
1. **End-to-end verification pipeline** – spec → FLUX proof → simulation → certificate (PDF) in under 2 minutes.  
2. **Counterexample visualization** – When spec is not satisfied, the AI fleet generates a minimal trace and overlays it on the simulation timeline.  
3. **Audit-ready snapshot** – Every proof run produces a hash-linked Git snapshot of spec, code, proof, and results, suitable for DO-178C traceability.  
4. **Human-in-the-loop override** – The UI allows a safety engineer to pause, add invariants, and re-run—critical for automotive ISO 26262 sign-offs.  

---

## 2. Partnerships to Pursue (3 targets, 1 per week)

**Week 1: University of Michigan Transportation Research Institute (UMTRI)**  
- **Why:** UMTRI runs the Mcity test track and has deep ties to Ford, GM, and Toyota. They need low-cost verification tools for their autonomous shuttle fleet.  
- **Action:** Send a 2-page tech brief to Dr. Carol Flannagan (head of connected vehicle safety) with a link to the demo lab. Offer 30-min remote demo during Week 3. AI fleet prepares a custom benchmark based on UMTRI’s published crash data (already in flux-bench).  

**Week 2: Collins Aerospace (Raytheon)**  
- **Why:** They are actively seeking formal methods for DO-178C compliance on next-gen flight control computers.  
- **Action:** Reach out to Dr. John Rushby (famed formal methods researcher) at SRI International, who has a joint project with Collins. Propose a 2-week collaboration: Collins provides a small case study (e.g., a flutter suppression filter), FLUX team verifies it, and both co-author a short technical report for the IEEE Formal Methods in Aerospace workshop.  

**Week 3: A small but influential Tier 2 supplier – e.g., ** **Kodiak Robotics** **(autonomous trucking)** or ** **Skypersonic** **(drone inspection)** .  
- **Why:** They move faster than OEMs and can integrate FLUX into their CI/CD pipeline within 30 days.  
- **Action:** Offer a “Verification-as-a-Service” trial: FLUX team will verify one of their safety-related firmware files for free. If successful, publish a joint case study at SAE WCX or ICAI.  

---

## 3. Conferences & Events (3 targets)

1. **SAE WCX (April 8–10, Detroit)** – Only 2 weeks away. This is non-negotiable. **Immediate action:** AI fleet generates a 3-minute video demo of FLUX verifying an adaptive cruise control contract. Human uploads to YouTube and submits to WCX’s “Virtual Showcase” (deadline this Friday). Also book a last-minute meeting with a Ford safety engineer via social media.  
2. **IEEE IV (Intelligent Vehicles Symposium – June 9–12, Los Angeles)** – We have 8 weeks. Prepare a **Late-Breaking Results** paper submission (deadline May 1). AI fleet drafts the paper on “FLUX: Automated Formal Verification for Automotive Control Systems” using the UMTRI case study. Human reviews and submits.  
3. **Formal Methods 2025 (FM, September 8–12, Vienna)** – Long-term but high-leverage. Submit a tool demo paper (deadline June 1). This will be our primary academic publication to attract research partnerships.  

---

## 4. Day-by-Day Plan for Week 1

*Human availability: 2 hours/day, 10:00-12:00 UTC. AI fleet runs continuously.*

**Day 1 – Foundation**  
- **Human (2 hrs):**  
  - 30 min: Review AI fleet’s report on current FLUX repo state (compilation status, test failures, benchmark gaps).  
  - 30 min: Write and send intro email to Dr. Flannigan at UMTRI (attach tech brief).  
  - 30 min: Review AI-generated Github Actions (CI/CD) for flux-demo-lab. Approve merge.  
  - 30 min: Record 90-second “Hello World” demo video for SAE WCX submission.  
- **AI fleet (24/7):**  
  - Fix the 3 failing unit tests in flux-verifier (logging bug in STL monitor).  
  - Run flux-bench on all 100+ problems to establish baseline time-to-verify.  
  - Generate a new Docker image for flux-demo-lab with Carla simulation (truck + ego vehicle).  

**Day 2 – Spec Synthesis**  
- **Human (2 hrs):**  
  - 30 min: Review AI fleet’s draft of 3 new natural-language specs for automotive benchmarks (adaptive cruise, lane-keeping, blind-spot).  
  - 1 hr: Provide feedback on one spec (“keep 2m gap at 10m/s, reset on speed limit sign”), test it in flux-auto-synth’s interactive REPL.  
  - 30 min: Approve AI fleet’s PR that adds auto-synth to the demo lab pipeline.  
- **AI fleet:**  
  - Convert the 3 specs into formal STL contracts and run through FLUX.  
  - Generate visualization for one proof (lane-keeping).  
  - Next: Extend flux-verifier to support ROS2 (for future hardware integration).  

**Day 3 – Simulation Integration**  
- **Human (2 hrs):**  
  - 30 min: Review AI’s generated Carla simulation config (lane-keeping scenario). Tweak vehicle parameters to match UMTRI test track dimensions.  
  - 30 min: Re-run the full pipeline (spec → proof → simulation) on human’s machine to sanity-check. Record minor UI bugs (button not centered).  
  - 30 min: Phone call with a contact at **Ansys** (discuss integration of FLUX into their SCADE product – optional partnership).  
  - 30 min: Update SAE WCX demo video with new simulation footage.  
- **AI fleet:**  
  - Fix the UI bugs flagged by human.  
  - Write automatic unit test for the lane-keeping proof (100% coverage).  
  - Start drafting the IEEE IV late-breaking paper (1,200 words).  

**Day 4 – Benchmark Expansion & Verification**  
- **Human (2 hrs):**  
  - 30 min: Review AI’s new benchmark for UAV collision avoidance (spec from Collins Aerospace’s open-source work).  
  - 1 hr: Manually verify one edge case (two drones approaching at 60° angle). FLUX produces a proof that they never occupy same 3D volume within 10s horizon.  
  - 30 min: Record a testimonial clip for the demo lab (to be embedded in the web UI).  
- **AI fleet:**  
  - Bulk-add 15 new benchmarks from the SAE J3016 taxonomy (automated driving levels 2-4).  
  - Run all 135 benchmarks through FLUX, generate a performance report (mean time: 2.3s per proof, max 8s).  
  - Begin hardening flux-docs: Add benchmark results as interactive tables.  

**Day 5 – Partnership Outreach & Content**  
- **Human (2 hrs):**  
  - 30 min: Follow up on UMTRI email (draft second message if no reply).  
  - 30 min: Research Collins Aerospace’s formal methods team, send a personalized LinkedIn message to Dr. Rushby.  
  - 1 hr: AI-generated draft of a 2-page “Partner Program” PDF for flux-partner-guide. Human edits for tone and legal disclaimers.  
- **AI fleet:**  
  - Generate a “Proof Certificate” PDF template that includes a QR code linking to the live proof tree.  
  - Write a blog post for the SuperInstance website: “Formal Verification for Autonomous Vehicles in Under 2 Minutes.”  
  - Set up a cron job to email the human a daily summary of proof counts, new issues, and external mentions.  

**Day 6 – Demo Polish & Error Handling**  
- **Human (2 hrs):**  
  - 30 min: Review AI fleet’s GitHub issues triage – closes 5 low-priority bugs (doc typos, env variables).  
  - 30 min: Final test of the demo lab on human’s machine – simulate a “wrong spec” scenario (speed limit of 200km/h) and check the counterexample trace is clear.  
  - 1 hr: Record a full walkthrough video (10 min) for potential partners. Upload to a private YouTube link.  
- **AI fleet:**  
  - Add error categorization to the demo lab (e.g., “TimeoutError: Proof took > 60s → suggest splitting spec.”).  
  - Run stress test: 100 concurrent verification requests on a 4-core VPS (simulating a Tier 1’s CI pipeline). Tune thread pool.  
  - Update flux-bench results page with “certified” badge for each benchmark.  

**Day 7 – Rest & Review**  
- **Human (30 min):**  
  - Review week’s progress summary from AI fleet (key metrics: 15 new proofs, 3 new benchmarks, 1 partnership lead, 1 conference submission).  
  - Confirm next week’s priorities: (1) Collins Aerospace call, (2) SAE WCX submission acceptance, (3) begin UMTRI case study.  
- **AI fleet:**  
  - Generate a “Week 2 Plan” document with specific repo tasks, partner milestones, and risk mitigation (e.g., if no reply from UMTRI by Tuesday, pivot to Kodiak Robotics).  
  - Run all benchmarks on fresh Docker image to ensure reproducibility for partners.  

---

## 5. Risk Management

| Risk | Probability | Mitigation |  
|------|-------------|------------|  
| **No reply from UMTRI** | High | AI fleet pre-vets 5 alternative automotive labs (MIT LL, Stanford CARS, Ohio State) – human emails 2 per day from that list. |  
| **FLUX proof fails on real spec** | Medium | AI fleet maintains a “fallback” mode using model checking (NuSMV) to generate partial proofs, then asks human to strengthen invariants. |  
| **$300 budget insufficient** | Medium | Use 100% free tier: GitHub Actions, Hugging Face Spaces for demo, temporary Oracle Cloud VPS ($0 for first 30 days). Cancel immediately after demo. |  
| **Human burnout** | Low | Strict 2-hour cap; all remaining work is AI-generated, human only reviews. Use voice-to-text for emails and blog posts. |  

**Narrative for final week:** By Day 30, we will have:  
- One published video demo with >500 views (SAE WCX).  
- One active partnership trial (UMTRI or Collins).  
- One submitted paper (IEEE IV).  
- A Dockerized verification platform that any Tier 1 can spin up in under 5 minutes.  

This is not about building a product—it’s about creating **irrefutable evidence** that FLUX can solve a $100M problem (compliance cost) in minutes. The AI fleet makes this possible; the human ensures it lands.

---

## Why This Plan Is Wrong (Seed-2.0-pro)

This is a masterclass in building a perfect tech demo for other formal methods nerds, and a perfect failure for the actual market you are targeting. Every single priority is inverted. You have ignored your single hardest constraint (2 human hours/day) to build things that will never get you a single dollar. Let's be brutal, specific, and no bullshit:

---

### First: The Core Delusion That Kills This Entire Plan
You think the customer cares that you verified 100 lines of code in 3 minutes.
You are wrong.
The first question any Bosch ASIL D engineer, any Safran verification lead, any actual human being with budget will ask you within 90 seconds of you opening your mouth is:
> *"Can this verify **our existing code**? The 12 million lines of garbage MISRA C we shipped last quarter, that we are already getting regulatory fines for, that we have 6 months to produce assurance on? Can you run it right now, no changes, no asking me to write a spec, just run it?"*

Nobody will ever give you clean new demo code. Nobody will ever let you write the control law. Nobody cares about your fancy proof tree. Every Tier 1 supplier on earth is currently sitting on 10-20 year old production code that they cannot prove correct, that regulators are now holding them hostage over. That is the only problem. Everything else you are building is masturbation.

---

### What Are You Building That Nobody Wants?
Let's go down your roadmap and mark the garbage:
1.  **flux-auto-synth v0.4: 100% useless, actively disqualifying.**
    No safety engineer on earth will ever accept an AI-generated formal contract. The contract is the single most regulated artifact in the entire process. If the contract is wrong, the proof is worthless. Every ISO 26262 auditor will walk out of the room the second you say "the AI wrote the spec". You are spending two full weeks building a feature that immediately disqualifies you from the market you are targeting. There is not one single paying customer for this capability. Not one.
2.  **flux-demo-lab web UI: Nobody will ever run this.**
    Procurement teams do not type `docker compose up`. They will not click through your interactive proof tree. 90% of the people you present to cannot even read a proof tree. They want one slide, one number: *"This function had 17 uncaught edge cases, we found all of them in 22 minutes, here is the certificate your auditor will sign off on"*. That is it. You are building an entire interactive environment for an audience that will never look past the third bullet on your title slide.
3.  **AI tactic synthesis: Nobody trusts your prover.**
    It does not matter how clever your AI is at generating proofs. The only property of a proof that matters for industrial use is that it can be independently verified by a 10 year old off-the-shelf auditor tool. Nobody trusts your custom prover. They barely trust Coq. You could have the best proof engine on earth, if it spits out a proprietary certificate it is worth less than nothing.

---

### What Are You Not Building That Actually Matters?
You have 60 total human hours over 30 days. You have allocated *zero* of them to the only things that count:
1.  **You have not allocated one single human hour to go get actual customer code.**
    There is no roadmap item that says: "Day 3: Find one mid-level Bosch engineer on Linkedin complaining about formal verification tools, buy them a coffee, ask them to send me the single worst unproven function their boss is currently yelling at them about". That is the entire 30 day plan. Everything else is filler.
2.  **You have no legacy C parser.**
    100% of the code you will ever be asked to verify is terrible 20 year old MISRA C 2004, full of macros, global state, undefined behaviour, and every language construct your clean verifier currently rejects. Your verifier works on nice modern C. That is useless. It will break on line 1 of every real world function anyone ever sends you. This is not on your roadmap.
3.  **You are not building the failure report.**
    Nobody buys formal verification because it proves things are correct. They buy it because it finds bugs that all their other testing missed. The demo that gets you a licensing meeting is not "we proved this correct". It is "we ran your code for 12 minutes, found 3 bugs that 6 months of HIL testing missed, here is the exact trace that triggers it". Every single sale of formal verification tools in history started this way. You have planned an entire demo that shows success, when the only demo that works is showing failure.
4.  **You have no standard proof export.**
    There are exactly 3 proof certificate formats that auditors accept. None are yours. You will export to them, even if they are stupid, even if they are worse, even if it means throwing away 70% of your fancy prover capabilities. This is not on your roadmap.

---

### What Partnerships Are Fantasies?
All of them.
Safran will not take your call. Bosch procurement will not reply to your email. ISO working groups do not let random startups present. The only people who will talk to you right now are the 4-6 mid-level engineers at Tier 1s who post drunk rants on Linkedin about how existing formal tools suck. Those are your only partners. Everyone else is a fantasy.
You will not get a licensing discussion from a demo. You will get a licensing discussion after you found a bug for someone that almost got them fired.

---

### What Conferences Are Wastes Of Time?
Every single formal methods conference. Every automotive safety summit. All of them. The only people there are other tool vendors, academics, and consultants. None of them buy tools. The only event you should attend is the unlisted hotel bar happy hour after the conference ends, where the actual engineers go to complain about their jobs. That is where you get the code snippet.

---

### The Actual First Thing A Customer Will Ask
Let's role play this exactly as it will happen. You get 5 minutes.
> *You:* "We can verify 100 lines in 3 minutes! Look at this pretty proof tree!"
> *Them, sliding a USB stick across the table:* "Great. This is 720 lines of cruise control code we have in production right now. Don't edit it. Don't ask me for a spec. Just run it. Email me the list of edge cases before I get back to my desk after this meeting. If you can do that, we will talk next week. If you can't, get out."

That is the entire sales process. Everything else in this plan is irrelevant.

---

### The Unforgivable Final Mistake
You have allocated your 2 human hours per day to reviewing AI PRs and refining demo scripts. This is completely inverted. The AI can write all the code. The AI can build all the demos. The only thing the AI cannot do is talk to an engineer, get their code, and send them back a bug report that makes them go "holy shit". That is the only job the human has. You have the human doing code review, and the AI building sales materials. That is how you waste 30 days, build a perfect impressive demo that nobody cares about, and quietly shut down.

At the end of 30 days:
- ✅ One email from one engineer that says "how the hell did you find that" = you won.
- ❌ Perfect docker demo, 27 new proofs, zero emails = you lost.

That is the only metric that exists.

---

## The Surviving Plan (DeepSeek Reasoner, Revised)

## Revised 2-Week Sprint Plan for flux (14 Days, 2 Hours/Day)

### The Only Goal: Make a Tool That Runs on a Legacy C File – No Specs, No Changes, Just Verdicts

The critique is correct. AI-generated contracts are a poison pill. The market wants a black box that chews on their 20-year-old MISRA C garbage and spits out a pass/fail report. No fancy proofs, no “write a contract first.” So we scrap every feature that requires a user-written or auto-generated specification. We keep only the core infrastructure: a C parser that survives real-world macros and a verification engine that runs **without any user input** and produces a brutally simple output.

**Constraint**: 2 human hours per day (28 hours total). Every minute must go toward the one thing that gets a “yes” from a Bosch lead: **“Run it on my code. Now.”**

### What Stays, What Goes, What’s New

- **GOES**: flux-auto-synth v0.4 (AI contract generation). The single most disqualifying feature. Burn it.
- **GOES**: The entire “write a control law” demo. No one cares about your clean-room example.
- **GOES**: Proof tree visualization. Regulatory auditors want a summary, not a forest of nodes.
- **STAYS**: The C parser (clang/libTooling) – necessary to actually read legacy code.
- **STAYS**: The basic report output (lines checked, checks passed/failed, time) – necessary for demo.
- **NEW**: A “no-spec mode” that automatically checks for undefined behavior (UB) and common coding rule violations using built-in heuristics. No user-written contracts, no annotations.
- **NEW**: A preprocessor and include path resolver that can handle the typical mess of legacy code (relative paths, missing headers, #defines).
- **NEW**: A single-file demo script that takes one C file as input and prints a one-page PDF report.

### The 14-Day Plan (Each Day = 2 Hours)

#### Week 1: The Core – Make It Run on a Real File

**Day 1 – Parser survival kit**  
- **Goal**: flux can parse a real-world C file (e.g., a 500-line MISRA C snippet from a public automotive benchmark) without crashing on macros, `#pragma`, or inline asm.  
- **Task**: Write a clang-based AST consumer that skips unsupported constructs and reports them as warnings. Fix include path resolution to use a fallback standard library stub.  
- **Deliverable**: `flux parse example.c` produces a parse summary (lines processed, warnings count).

**Day 2 – Built-in UB checks (no spec needed)**  
- **Goal**: Implement three automatic checks that require zero user input: division‑by‑zero, null pointer dereference, and buffer overflow (simple static analysis, not symbolic).  
- **Task**: Add a pattern‑matching pass that flags obvious violations (e.g., `x / 0`, `* NULL`). Use existing clang static analyzer plugins if possible.  
- **Deliverable**: `flux check example.c` prints line numbers for each violation.

**Day 3 – Bounded model checking without contracts**  
- **Goal**: Add optional symbolic execution with hardcoded unwinding (unwind=1) to catch subtler UB that static analysis misses – again, no user contracts.  
- **Task**: Wrap CBMC (or a subset) as a subprocess with flags `--bounds-check --pointer-check --div-by-zero-check` and no `--function` or `--property` arguments. Parse CBMC output into a uniform “PASS/FAIL” format.  
- **Deliverable**: `flux bmc example.c` runs CBMC in “auto” mode and reports all found defects.

**Day 4 – Handling real‑world preprocessor madness**  
- **Goal**: flux can process code with heavy `#ifdef`, `#define` magic, and missing headers without crashing.  
- **Task**: Build a lightweight preprocessor pass that expands macros and resolves `#include` using a dummy header tree. Use `-undef` and `-nostdinc` plus a minimal stdlib.h stub.  
- **Deliverable**: `flux preprocess example.c` outputs a single preprocessed file (no more `#ifndef` blocks blocking analysis).

**Day 5 – Aggregate reporting for non‑nerds**  
- **Goal**: Produce a one‑page summary that an engineer can print and hand to a regulator: “Checked 12,000 lines in 30 seconds. Found 4 potential violations.”  
- **Task**: Write a report generator that takes the parse + check + BMC results and formats them as a simple text table (or LaTeX PDF) with three columns: Check Type, Lines Affected, Severity.  
- **Deliverable**: `flux report example.c` prints a human‑readable summary.

**Day 6 – Stress test on a legacy code sample**  
- **Goal**: Run the full pipeline on a public automotive code sample (e.g., from the OSEK/VDX benchmark or a MISRA C test suite). Fix any crashes or false positives.  
- **Task**: Download a 1,000‑line real‑world C file (with macros, structs, and conditional compilation). Iterate until flux produces a sensible output.  
- **Deliverable**: A successful run on `legacy_brake_controller.c` with a report that lists real UB.

**Day 7 – Buffer and first demo script**  
- **Goal**: Package the day‑to‑day work into a single shell script: `flux-demo.sh file.c` that runs all checks and prints a report.  
- **Task**: Write the script, test on the sample from Day 6, and ensure it works with no additional input. Add a timeout (60 seconds) to avoid infinite loops.  
- **Deliverable**: A one‑line demo command that a prospect can run on their own file.

#### Week 2: Polish for Sales – No More Features, Only Reliability

**Day 8 – Error‑handling for ugly code**  
- **Goal**: flux gracefully handles malformed C (missing semicolons, unmatched braces) instead of crashing.  
- **Task**: Wrap parser calls in try/catch; if parsing fails, fall back to simple text‑based pattern checks (regex for suspicious patterns like `memcpy` with variable length).  
- **Deliverable**: `flux check broken.c` prints “Parse error – falling back to pattern scan: 2 potential issues found.”

**Day 9 – Performance for large files**  
- **Goal**: flux can process a 100,000‑line file in under 5 minutes.  
- **Task**: Profile Day 7 demo on a synthetic 100k‑line file (concatenated from multiple sources). Optimize bottleneck: disable CBMC for files >10k lines (too slow), use static analysis only.  
- **Deliverable**: `flux bigfile.c` completes in <5 minutes and prints a summary.

**Day 10 – The “No Changes” guarantee**  
- **Goal**: Ensure flux does not require the user to modify their code in any way – no adding `__attribute__`, no including flux headers, no editing build scripts.  
- **Task**: Test on a codebase that uses custom `typedef`, `volatile`, and inline assembly (stub out asm blocks). If any adjustment is needed, make it automatic (e.g., replace `asm` with a no‑op).  
- **Deliverable**: `flux check legacy.c` works on a file that originally had `__asm__("nop")` without any changes.

**Day 11 – Output a single actionable number**  
- **Goal**: The most important metric: “% of undefined behavior eliminated” – for the demo, just count how many of the automatically detected UB patterns were confirmed absent (or present).  
- **Task**: For each check, report a ratio: e.g., “Division by zero: 0 violations in 12,000 divisions detected (100% safe).”  
- **Deliverable**: Report now includes percentage per category.

**Day 12 – Dry‑run with a real industry code (if available)**  
- **Goal**: Get a thumbs‑up from a domain expert by running flux on their actual code.  
- **Task**: Reach out to a contact at a Tier 1 supplier. Ask for a small, sanitized sample (500 lines) from their production codebase. Run flux on it and fix any remaining issues (e.g., handling of `__interrupt` keywords).  
- **Deliverable**: A successful run on external code, with a timestamped log.

**Day 13 – The pitch deck one‑pager**  
- **Goal**: Create a one‑page PDF that a salesperson can drop into a slide: “flux – run on any C code, no specs needed. Example: 15,000 lines checked in 90 seconds, 3 violations found.”  
- **Task**: Format the Day 12 report as a neat printable page. Add a minimal explanation: “Unlike other tools, flux requires zero annotations. Just point, click, and get your regulatory report.”  
- **Deliverable**: `flux-report.pdf` ready to email.

**Day 14 – Final demo and polish**  
- **Goal**: Package everything into a single executable (static binary or Docker image) that can run on a fresh Linux machine with no dependencies.  
- **Task**: Build a Dockerfile that bundles clang, CBMC, and the flux scripts. Test on the sample file. Write a short README with the exact command: `docker run flux-demo my_code.c` and the expected output.  
- **Deliverable**: `flux-demo.tar.gz` that takes exactly 30 seconds to demonstrate.

### Why This Plan Works

It ignores the very things the critique called out: no AI, no custom specifications, no perfect demo code. Every day’s deliverable is either **survival** (parsing legacy mess) or **actionable output** (a report that says “you’re safe here, not safe there”). The 2‑hour constraint forces ruthless prioritization. There is no room for building a general‑purpose verifier. Instead, we build a **focused lie detector** for the one question a buyer will ask: *“Does my code have the most common undefined behaviors?”* That’s the only thing that gets a foot in the door.

If we succeed, by Day 14 we have a tool that – when a Safran engineer says “run it on this 50k-line file we’ve been fined for” – can answer within 5 minutes with a PDF that lists exactly two things: “Tests passed: 98% of checks clean” and “Tests failed: 3 division‑by‑zero locations, lines 1247, 3012, 8911.” The engineer will then ask: “Can you do this for all our files?” And that is the beginning of a sale.

**No more masturbation. Just the one thing that matters.**