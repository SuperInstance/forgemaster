**MEMORANDUM**  
**TO:** General Partner, a16z  
**FROM:** Partner, Enterprise / Infrastructure Practice  
**RE:** SuperInstance/FLUX – Investment Decision  
**DATE:** October 26, 2023  

---

### Executive Summary

SuperInstance/FLUX presents a classic "vision-first, traction-later" deep tech pitch. The founder—a solo operator with an AI fleet—claims a path to reducing safety-critical constraint proof reviews from three days to 90 seconds by 2031. The product suite is ambitious: a free IDE, a $50K/yr/project certification tool, a free runtime monitor, and FPGA IP ranging from $100K to $1M. Projected Year 5 ARR is $5.75M. Current state: 30 English proofs, 8 Coq theorems, 7 GitHub repos, zero customers, zero revenue.

I will answer each of your five questions directly, then give a final recommendation. The tone will be honest, skeptical, but not dismissive—because sometimes the most absurd early-stage pitches turn into the biggest wins. But more often, they are a mirage. Let's assess.

---

### 1. Is the 90-second review realistic by 2031?

**Short answer:** Plausible under extremely aggressive assumptions, but not probable.

The claim is that a safety engineer (presumably a human with domain expertise, or a human-in-the-loop augmented by AI) can validate formal constraint proofs for a safety-critical system (say, an autonomous vehicle controller, a medical device, or a nuclear reactor shutdown loop) in 90 seconds. Today, that same review takes three days—roughly 24 engineer-hours. That is a ~99.9% reduction in human time.

**Why it could happen:** We are in an era of compounding AI capability. By 2031, it is reasonable to expect that LLM-based reasoning agents will be significantly stronger than today. Specialized models fine-tuned on Coq, Lean, and other proof assistants could generate and check proofs at speeds far beyond human capacity. The FPGA IP piece suggests hardware acceleration—a custom chip optimized for SAT/SMT solving could make proof checking near-instantaneous. If the founder can couple a proof-assistant frontend with an FPGA backend and an LLM layer that interprets high-level constraints, 90 seconds might be achievable for *well-posed, bounded* problems.

**Why it probably won't happen:** The phrase "constraint proofs" is ambiguous. In safety-critical systems, the constraints are often not purely mathematical—they involve timing, concurrency, physical models, and real-world sensor noise. The hardest part is not checking the proof; it is *specifying the property* to prove. Most industrial safety failures are due to incorrect or incomplete specifications, not failed proofs. Reducing human review time assumes the specification is already perfect. It’s like claiming you can review a legal contract in 90 seconds if you ignore that the law itself might be ambiguous. Also, the state space for a typical safety-critical system (e.g., a Boeing 777 flight control system) is astronomical. Even with FPGAs, exhaustive verification is often impossible—you rely on abstraction, which introduces its own vulnerabilities.

**Verdict:** The 90-second target is a marketing vision, not a product roadmap. It is likely unrealistic for the *general* case by 2031, but possible for a narrow, pre-defined class of constraints that the company chooses to support. The founder should articulate *which* constraints and *why* 90 seconds. If the answer is vague, this is a red flag.

---

### 2. Is $5.75M ARR at Year 5 too conservative or too optimistic?

**Short answer:** It is simultaneously too optimistic and too conservative—that is a problem signaling fuzzy thinking.

**Too optimistic:** Starting from zero customers and zero revenue today, reaching $5.75M ARR in five years would require extraordinary traction for a single founder with no sales team. Let’s do back-of-envelope arithmetic: Assume the primary revenue driver is FLUX Certify at $50K/project/year. To hit $5.75M ARR, you need ~115 projects under active certification. For FPGA IP, assume an average selling price of $500K—you would need ~11 customers per year to hit that revenue, which is even harder because FPGA IP is usually a one-time license with recurring maintenance fees. Either way, the implied customer count is high.

But the bigger issue is *sales cycle* in safety-critical industries. Selling to aerospace, automotive, or medical device companies means 18–24 month evaluation cycles, regulatory qualification, and often a compliance team that moves at glacial speed. Even if the product is perfect, a single founder cannot run 115 simultaneous enterprise sales processes. The ARR target implies a sales velocity that is inconsistent with the zero-revenue starting point.

**Too conservative:** If the technology genuinely reduces verification from three days to 90 seconds, the value proposition is enormous. A single major OEM (say, a car company like Toyota or a chip company like NVIDIA) might have hundreds of projects that require safety certification. If FLUX Certify saves each project ~$100K in engineering time (conservative), the price could be $200K–$500K per project, not $50K. At that price, 20 customers would yield $10M ARR. The $5.75M figure feels like a placeholder—a number that sounds believable but isn’t grounded in any bottom-up analysis of market sizing or pricing power.

**Verdict:** The revenue projection betrays a lack of sales and pricing strategy. It is a guess, not a forecast. I’d want to see a bottoms-up model with customer personas, deal sizes, sales cycles, and churn assumptions.

---

### 3. What is the ACTUAL moat—can Google/Anthropic replicate this in a weekend?

**Short answer:** The moat is thinner than the founder believes, but not zero. Google/Anthropic could replicate the *core idea* quickly, but the *defensible assets* are the proof corpus, FPGA integration, and domain-specific chain-of-thought data.

**What can be replicated in a weekend:** The basic idea—train an LLM on Coq theorems and English proofs to automate constraint verification—is not novel. DeepMind, Google Brain, and Anthropic have already published papers on using LLMs for formal proof generation (e.g., AlphaProof, GPT-f, etc.). Given a weekend and a cloud cluster, any top-tier lab could produce a proof-of-concept that matches or exceeds the 30 English proofs and 8 Coq theorems you already have. Those numbers are small enough to be considered "toy problems." The actual moat cannot be the algorithm itself.

**What takes years to replicate:** (a) **Hardware integration** – FPGA IP that is designed specifically for proof checking, with a compiler pipeline from the IDE to the chip, is not trivial. It requires low-level hardware design, timing closure, and integration with existing safety toolchains. Google could do this, but it's not a weekend project. (b) **Data moat** – The 30 English proofs and 8 Coq theorems are negligible. But if the founder has a pipeline to generate *proprietary* proof corpora from real industrial domains (aviation, automotive, nuclear), that could be defensible. However, there is no evidence of that yet. (c) **Certification artifacts** – Safety-critical industries require *certification* of the tool itself. If FLUX Studio and FLUX Certify can achieve DO-178C or ISO 26262 qualification, that is a multi-year regulatory moat. But again, zero customers means zero certification process has started.

**True moat assessment:** The only real moat at this stage is **founder speed and focus**. A solo operator with an AI fleet can iterate faster than a large research lab that must align multiple teams, navigate internal politics, and prioritize higher-revenue products. But that moat dissolves the moment a tech giant decides to "moonshot" this problem.

**Verdict:** No defensible moat yet. The pitch needs to articulate a unique data advantage or a hardware lock-in that a big lab cannot easily replicate.

---

### 4. What is the biggest risk?

**Short answer:** Not technical risk—**execution risk**, specifically the founder's ability to transition from solo researcher to company builder.

The biggest risk is not that the proofs cannot be checked in 90 seconds. The biggest risk is that the founder is a **single person** trying to build a product, sell to enterprises, manage relationships with FPGA vendors, handle legal/compliance, and raise follow-on funding. The "AI fleet" is a clever narrative, but AI agents today cannot negotiate contracts, attend trade shows, or build trust with a VP of Engineering at an aerospace company. They cannot file patents, manage security reviews, or navigate the procurement process.

Second-risk: **Product-market fit gap**. The product assumes that safety engineers want to replace their current review process with an AI-driven tool. In practice, safety engineers are a conservative, risk-averse community. They often distrust "black box" automation. The tool must be transparent, auditable, and explainable. FLUX Studio is free, which is good for adoption, but the $50K Certify price tag will require a champion inside the customer organization. Without a single pilot customer, it's impossible to know if the tool actually saves time or introduces new sources of error.

Third-risk: **Capital requirements**. Even with a lean AI fleet, building FPGA IP and achieving certification is capital-intensive. A solo founder will likely run out of runway before reaching $5.75M ARR unless they raise significant funds. But with zero revenue, zero customers, and a relatively novel approach, Series A may be tough.

**Verdict:** The biggest risk is founder-bandwidth and go-to-market execution. Technical risk is real but secondary.

---

### 5. Would you invest? Be honest.

**Final answer: No.** Not at this stage, not with this data.

I will elaborate honestly:

**What I like:** The founder is clearly technical and has a coherent vision. The "reverse actualization" narrative—working backward from a concrete future—is a sign of strategic thinking. The product pricing tiers (free IDE, paid certification, FPGA IP) are well-structured. The target market (safety-critical systems) is large, growing, and underserved. If this works, it could be a $10B+ company.

**What I do not like:** Zero traction. Zero customers. Zero revenue. A solo founder with no co-founder. A vague moat. A revenue projection that appears plucked from thin air. The GitHub repos and proofs are essentially prototypes—they do not demonstrate that the system can handle industrial-scale problems. The 90-second claim is a great hook but lacks technical grounding.

**Why not "maybe" a small check?** Early-stage a16z bets often go to teams with strong counterfactual reasoning and clear initial signal. A solo founder with zero revenue can still be compelling if they have a deeply unfair advantage (e.g., they are the top expert in constraint proofs and have a network of potential customers). The founder has not demonstrated that advantage—30 English proofs is not a high bar, and 8 Coq theorems is a single graduate student's work.

**What would change my mind:** If the founder can land one letter of intent (LOI) from an aerospace or automotive company, or even a pilot project with a university safety lab. If they can show that their proof corpus is growing at a rate that implies proprietary data generation. If they add a co-founder with sales or domain expertise. If they can articulate a specific, narrow use case (e.g., "we verify the constraint that a brake-by-wire system never exceeds 10ms latency") with a reasonable technical explanation of how 90 seconds is achieved.

**Recommendation:** Pass now, but track. If the founder raises a small pre-seed elsewhere and can show traction within 12 months (a single paying customer, even at $10K), re-evaluate. The vision is intriguing, but the risk/reward is currently unfavorable.

---

### Conclusion

SuperInstance/FLUX is a high-risk, high-potential moonshot. The 90-second target is marketing, not a milestone. The $5.75M ARR is a guess, not a forecast. The moat is unproven. The biggest risk is execution and go-to-market. I would not invest at this stage. The company needs to find product-market fit with a single real customer before it becomes investable. Until then, it is a fascinating research project, not a venture-scale business.

**Vote: No.**