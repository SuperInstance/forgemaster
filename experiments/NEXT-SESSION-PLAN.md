**Prioritized Research Plan: Next Session**

**Must Do (Core Theory & Validation)**
1. **Organize Findings & Structure:** Use GLM-5.1 to map the 28 findings and 24 studies into a rigorous, publishable arXiv structure. Define the "Substitution Burden" mechanics and the pre-computation fix clearly.
2. **Define Minimum Pre-Computation:** Test the exact threshold required to bypass the Substitution Burden. Do we only need to inject final numerical answers into the prompt, or is full step-by-step intermediate logic required for the model to process the context correctly?
3. **Real-World PLATO Testing:** Move beyond synthetic benchmarks. Run the pre-computation pipeline against actual PLATO room tasks to validate real-world utility and uncover edge cases.
4. **ROI & Cost Benchmarking:** Quantify the economic value of the architecture. Calculate the exact dollar savings of our auto-translation/pre-computation routing versus defaulting 100% of complex queries to Seed-2.0-mini.

**Should Do (System Hardening & Scalability)**
5. **Harden Fleet Translator:** Integrate the proven pre-computation logic into `fleet_translator.py`. Add result caching and system monitoring to make it production-ready.
6. **Multi-Step Computation Chains:** Validate the Substitution Burden effect on complex, multi-step chains. Ensure the pre-computation fix holds up across extended reasoning sequences without degrading.
7. **Expand Stage 4 Roster:** Run standardized tests on other available frontier models. Determine if Seed-2.0-mini is a genuine anomaly or if other capable Stage 4 models currently exist.

**Nice To Have (Future Work)**
8. **Draft the Paper:** Write the full arXiv manuscript (highly dependent on completing the "Must Do" validation first).
9. **Cross-Lingual Testing:** Test if the Substitution Burden manifests similarly in structurally different languages like Chinese and Japanese.
10. **Fine-Tuning Exploration:** Investigate whether we can fine-tune a cheaper Stage 3 model to natively achieve Stage 4 domain computation capabilities.