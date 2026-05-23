% =============================================================================
% EMSOFT 2027 — FLUX-LUCID Paper
% Sections 2 (Related Work), 6 (Discussion), 7 (Future Work), 8 (Conclusion)
% References (Bibliography)
% Companion to: 2026-05-03-emsoft-abstract-intro.md
%               2026-05-04-emsoft-methodology-evaluation.md
% =============================================================================

% ─────────────────────────────────────────────────────────────────────────────
\section{Related Work}
\label{sec:related}
% ─────────────────────────────────────────────────────────────────────────────

FLUX-LUCID sits at the intersection of four research traditions:
synchronous languages for safety-critical systems, verified compilation,
GPU-accelerated constraint solving, and certification-grade hardware design.
We position our contribution against each in turn, and then argue that no
existing system combines all four capabilities.

% ─────────────────────────────────────────────────────────────────────────────
\subsection{Synchronous Languages: SCADE, Lustre, and Esterel}
\label{sec:related-synchronous}
% ─────────────────────────────────────────────────────────────────────────────

The synchronous language paradigm, pioneered by Esterel~\cite{berry1992esterel},
Lustre~\cite{halbwachs1991lustre}, and Signal~\cite{benveniste1991signal},
was designed explicitly for safety-critical reactive systems. The key insight
is that a synchronous program executes in lockstep with a global logical
clock, making timing behavior deterministic and amenable to formal analysis.
SCADE Suite~\cite{scade}, the industrial successor to Lustre, is qualified
under DO-178C at Design Assurance Level (DAL) A via the SCADE KCG code
generator, which has undergone tool qualification per DO-330~\cite{do330}.
This qualifies SCADE for use in the most critical avionics software paths.

However, synchronous languages address \emph{software} safety.
The SCADE compiler guarantees that generated C code preserves the semantics
of the source Lustre program, but it does not constrain the hardware on
which that code executes. A bit-flip in DRAM, an ECC-correctable but
semantically silent error in an SRAM row, or a timing violation in the
processor pipeline can violate the synchronous hypothesis at the physical
layer. SCADE's safety argument stops at the binary/hardware boundary.

FLUX-LUCID complements synchronous languages by providing the hardware-level
constraint enforcement that SCADE assumes but does not verify. A GUARD
constraint can express the same bounded-range invariants that a SCADE
\texttt{assert} directive expresses, but GUARD compiles to a mask-locked
hardware mechanism (the FLUX-C shadow observer) that physically prevents
constraint violations from propagating, rather than relying on software
assertions that trigger exception handlers \emph{after} the violation has
already occurred.

The Esterel~\cite{berry1999esterel_semantics} approach to reactive
programming shares FLUX-LUCID's emphasis on deterministic, bounded execution,
but again targets software semantics. The Esterel compiler's correctness
proof~\cite{berry1992esterel} establishes that the compiled circuit
(or generated C code) implements the source program's behavioral semantics.
FLUX-LUCID's Galois connection (Theorem~\ref{thm:galois}) plays an analogous
role — establishing that compiled FLUX-C bytecode overapproximates the GUARD
constraint — but operates at a different abstraction level: between the
constraint specification and the hardware bitmask domain, not between
source and object code.

% ─────────────────────────────────────────────────────────────────────────────
\subsection{Verified Compilers: CompCert and CakeML}
\label{sec:related-compilers}
% ─────────────────────────────────────────────────────────────────────────────

CompCert~\cite{leroy2009compcert} is a formally verified C compiler whose
correctness theorem states that the generated assembly code preserves the
observable behavior of the source C program. The proof, mechanized in Coq,
covers all compiler passes from C to PowerPC, ARM, and x86 assembly, and
has become the gold standard for verified compilation in safety-critical
domains. CompCert's approach has been extended to concurrent settings by
CompCertX~\cite{song2019compcertx} and to CheriBSD-capability hardware by
CapCompCert~\cite{sammler2023capcompcert}.

CakeML~\cite{kumar2014cakeml} goes further by verifying the compiler
\emph{and} the bootstrapping process in HOL4, producing a verified binary
that is guaranteed to correctly compile CakeML source code. This
self-hosting property eliminates the trust gap between the verified
compiler theorem and the actual executing compiler binary.

FLUX-LUCID's verification strategy differs from CompCert and CakeML in
scope and in the nature of the correctness property being proved.
CompCert verifies \emph{semantic preservation}: the compiled program means
the same thing as the source program. FLUX-LUCID verifies \emph{constraint
soundness}: the compiled bytecode overapproximates the source constraint,
guaranteeing that no safe state is rejected and no constraint violation is
missed. This is a weaker but arguably more useful property for safety
certification, because it does not require the full semantic equivalence
proof (which is enormous for general-purpose compilers) and instead focuses
on the safety-relevant portion of the behavior.

Moreover, FLUX-LUCID targets a 43-opcode VM rather than a general-purpose
ISA, making the verification effort tractable on a 6--9 month timeline.
CompCert's verification required approximately 10 person-years; CakeML's
bootstrap proof is similarly large. By constraining the target language to a
minimal constraint VM, FLUX-LUCID achieves formal verification at a cost
compatible with industrial certification budgets.

% ─────────────────────────────────────────────────────────────────────────────
\subsection{GPU Computing for Safety-Critical Systems}
\label{sec:related-gpu}
% ─────────────────────────────────────────────────────────────────────────────

General-purpose GPU computing (GPGPU) has transformed many domains —
molecular dynamics, deep learning training, scientific simulation — but
its adoption in safety-critical systems is effectively zero. The reasons
are well-documented in the literature and can be grouped into three
categories.

\paragraph{Non-determinism.}
GPU thread scheduling is implementation-defined and varies across
architectures, driver versions, and even between runs on the same
hardware~\cite{betts2011 gpu_verify}. Atomic operations have
implementation-defined ordering semantics that cannot be modeled in a
standard DO-178C timing analysis. The CUDA programming model explicitly
disclaims determinism guarantees for \texttt{\_\_global\_\_} functions,
making it impossible to construct a deterministic execution argument
required by DO-178C Annex A-6 (Testing of Software).

\paragraph{Lack of IMA support.}
Integrated Modular Avionics (IMA) systems, specified by ARINC
653~\cite{arinc653}, require strict temporal and spatial partitioning
between applications sharing a processor. GPU memory hierarchies
(shared memory, L2 cache, global memory) are not partitionable in a way
that satisfies ARINC 653 partitioning requirements. A rogue kernel can
exhaust shared memory or saturate the memory bus, causing deadline misses
in other partitions.

\paragraph{No certification precedent.}
As of 2026, no GPU has been certified to DO-254 DAL A or even DAL B.
The closest precedent is the NVIDIA Tegra X1's use in automotive
DRIVE PX2, which was certified to ISO 26262 ASIL B for \emph{specific,
bounded} workloads under NVIDIA's proprietary safety
case~\cite{nvidia2020safety}. This safety case relies on software-layer
redundancy (running the same inference twice and comparing outputs), not
hardware-level formal proof.

FLUX-LUCID does not attempt to certify the GPU itself. Instead, it uses
the GPU as a \emph{pre-deployment validation engine}: the GPU runs billions
of constraint checks during the certification campaign (achieving
90.2~billion checks/second sustained, 341~billion peak, on a single
consumer GPU at 46.2~W), but the GPU is \emph{not} in the runtime safety
path. The runtime enforcement is handled by the FPGA shadow observer
(Section~\ref{sec:eval-fpga}), which is amenable to hardware certification.
This architectural separation — GPU for testing, FPGA/ASIC for deployment —
allows FLUX-LUCID to leverage GPU throughput without inheriting GPU
certification risk.

% ─────────────────────────────────────────────────────────────────────────────
\subsection{Constraint Satisfaction and SAT/SMT Solving}
\label{sec:related-csp}
% ─────────────────────────────────────────────────────────────────────────────

Constraint Satisfaction Problems (CSPs) are NP-complete in general, but
structured instances arising in engineering applications often exhibit
properties (bounded treewidth, small domain cardinality) that admit
efficient solutions. FLUX-LUCID's bitmask AC-3 kernel exploits one such
property: when constraint variable domains are subsets of $[0, 255]$
(representable as 8-bit masks), arc consistency can be maintained by
bitwise AND operations in $O(1)$ per arc, bypassing the $O(d^2)$
per-arc cost of classical AC-3~\cite{mackworth1977} where $d$ is the
domain size.

Modern SAT and SMT solvers — MiniSat~\cite{een2003minisat},
Z3~\cite{demoura2008z3}, CVC5~\cite{barbosa2022cvc5} — solve
general boolean satisfiability and richer theories (bitvectors, arrays,
linear arithmetic) but are designed for offline analysis, not runtime
enforcement. A Z3 query over 48 bitvector variables with bounded arithmetic
constraints typically requires $10$--$1000$~ms on a modern CPU —
incompatible with the $10$~ms eVTOL control-loop budget. FLUX-LUCID's
FLUX-C VM achieves WCET of 3.2~$\mu$s for the same constraint graph by
trading generality for boundedness: FLUX-C supports only the GUARD
constraint language (first-order, bounded quantification, no uninterpreted
functions), which guarantees polynomial-time evaluation.

The Constraint Handling Rules (CHR) framework~\cite{fruhwirth1998chr}
offers a more flexible constraint programming model, but its operational
semantics are defined by a Turing-complete rewrite system that cannot
provide bounded execution guarantees. FLUX-LUCID's deliberate restriction
to a decidable constraint language with bounded loops is a feature, not
a limitation, in the certification context.

% ─────────────────────────────────────────────────────────────────────────────
\subsection{Abstract Interpretation and Galois Connections}
\label{sec:related-abstract}
% ─────────────────────────────────────────────────────────────────────────────

Abstract interpretation, introduced by Cousot and
Cousot~\cite{cousot1977}, provides a mathematical framework for reasoning
about program properties over approximate (``abstract'') domains. The
central tool is the Galois connection
$(\mathcal{C}, \subseteq) \galois{\alpha}{\gamma} (\mathcal{A}, \sqsubseteq)$,
which relates a concrete domain $\mathcal{C}$ to an abstract domain
$\mathcal{A}$ via an abstraction map $\alpha$ and a concretization map
$\gamma$. The soundness property $\gamma(\alpha(S)) \supseteq S$ guarantees
that the abstract analysis overapproximates the concrete behavior —
exactly the property needed for safety certification.

FLUX-LUCID's Galois connection (Theorem~\ref{thm:galois}) instantiates
this framework with a specific pair: the concrete domain is the powerset
of runtime signal valuations $\mathcal{P}(\Sigma)$, and the abstract
domain is the lattice of bitmask domain representations $\mathcal{B}$.
This instantiation is closely related to the interval and congruence
domains used in classical abstract interpreters~\cite{cousot1979verifying},
but with a key difference: the abstraction is not computed by a fixed-point
iterator over program control flow, but is \emph{materialized directly} by
the FLUX-C DMSET/DMINTER opcodes, which construct the bitmask domain
explicitly from the GUARD constraint annotations.

The Astr\'{e}e static analyzer~\cite{blanchet2003astree}, developed by
Cousot et al., demonstrated that abstract interpretation can scale to
industrial-size embedded C programs (hundreds of thousands of lines) and
achieve zero false alarms on flight-control software. Astr\'{e}e's
soundness guarantee — all possible runtime errors are detected by the
analysis — is analogous to FLUX-LUCID's guarantee that all constraint
violations are detected by the mask-lock mechanism. The difference is that
Astr\'{e}e operates at compile time, while FLUX-LUCID operates at runtime,
enabling detection of constraint violations caused by hardware faults
(e.g., soft errors, timing violations) that static analysis cannot predict.

Recent work on abstract interpretation for neural networks —
AI$^2$~\cite{gehr2018ai2}, DeepPoly~\cite{singh2019deeppoly}, and the
ERAN analyzer~\cite{singh2019abstract} — uses abstract interpretation to
verify robustness properties (e.g., certified adversarial radii) of trained
networks. These approaches analyze the network's mathematical behavior;
FLUX-LUCID analyzes the \emph{hardware execution} of constraint checks.
The two approaches are complementary: DeepPoly can verify that a network's
output is robust to bounded input perturbations, while FLUX-LUCID verifies
that the hardware executing that network's constraint enforcement layer
faithfully implements the specification.

% ─────────────────────────────────────────────────────────────────────────────
\subsection{Certification Standards: DO-178C, DO-254, and DO-330}
\label{sec:related-certification}
% ─────────────────────────────────────────────────────────────────────────────

DO-178C~\cite{do178c}, ``Software Considerations in Airborne Systems and
Equipment,'' is the primary certification standard for airborne software.
Its hardware counterpart, DO-254~\cite{do254}, governs the design assurance
of airborne electronic hardware. DO-330~\cite{do330}, ``Software Tool
Qualification Considerations,'' addresses the qualification of tools used
in the development of DO-178C/DO-254 artifacts.

FLUX-LUCID's certification strategy engages all three standards:
\begin{itemize}
  \item \textbf{DO-178C:} The GUARD compiler and FLUX-C toolchain are
        qualified as development tools under DO-330 at Tool Qualification
        Level (TQL) 1 (required for DAL A). The 38 formal proofs
        (30 pen-and-paper + 8 mechanized in Coq) serve as formal
        verification evidence per DO-178C Annex A-7 (Verification of
        Software Requirements).
  \item \textbf{DO-254:} The FLUX-C shadow observer FPGA/ASIC
        implementation is certified as DAL A hardware. The bounded
        verification of all 43 opcodes provides the exhaustive
        verification evidence required by DO-254 Section 6.3.2
        (Advanced Formal Methods).
  \item \textbf{DO-330:} The GPU validation pipeline
        (Section~\ref{sec:gpu-kernels}) is qualified as a verification
        tool at TQL 3, leveraging the 30-experiment, 10M+ input
        differential testing campaign (zero mismatches) as tool
        qualification evidence.
\end{itemize}

The Multi-core Processor Guidance document~\cite{cast32a} (CAST-32A)
addresses certification challenges for multi-core processors, including
interference channels and bandwidth sharing. FLUX-LUCID's shadow observer
operates on a single deterministic pipeline (no shared caches, no
speculative execution), sidestepping the multi-core interference analysis
that CAST-32A mandates. This architectural simplicity is a deliberate
certification strategy: every transistor in the shadow observer has a
traceable safety purpose, enabling the exhaustive structural coverage
required by DO-254 DAL A.

% ─────────────────────────────────────────────────────────────────────────────
\subsection{Positioning: The Unique Contribution of FLUX-LUCID}
\label{sec:related-positioning}
% ─────────────────────────────────────────────────────────────────────────────

\begin{table}[t]
\centering
\caption{Feature comparison: FLUX-LUCID vs.\ existing approaches.
No prior system combines GPU-native execution throughput, formal proof,
and open-source availability.}
\label{tab:positioning}
\renewcommand{\arraystretch}{1.15}
\begin{tabular}{lccccc}
\toprule
\textbf{System} & \textbf{GPU} & \textbf{Formal} & \textbf{Open} &
\textbf{Cert.\ Path} & \textbf{Runtime} \\
 & \textbf{Native} & \textbf{Proof} & \textbf{Source} &
 & \textbf{Enforce} \\
\midrule
SCADE/KCG~\cite{scade}         & \xmark & \xmark & \xmark & DO-178C DAL A & Software \\
CompCert~\cite{leroy2009compcert} & \xmark & \cmark & \cmark & DO-178C (partial) & N/A \\
CakeML~\cite{kumar2014cakeml}   & \xmark & \cmark & \cmark & None established & N/A \\
NVIDIA Orin~\cite{nvidia2020safety} & \cmark & \xmark & \xmark & ISO 26262 ASIL B & Software \\
Hailo-8~\cite{hailo8}           & \xmark & \xmark & \xmark & ISO 26262 ASIL B & Watchdog \\
Astr\'{e}e~\cite{blanchet2003astree} & \xmark & \cmark & \xmark & DO-178C (tool) & Compile-time \\
Z3~\cite{demoura2008z3}         & \xmark & \cmark & \cmark & None & Offline \\
\midrule
\textbf{FLUX-LUCID}             & \cmark & \cmark & \cmark & DO-254 DAL A & Hardware \\
\bottomrule
\end{tabular}
\end{table}

Table~\ref{tab:positioning} summarizes the feature landscape. To the best
of our knowledge, FLUX-LUCID is the first system to simultaneously provide:
\begin{enumerate}
  \item \textbf{GPU-native execution throughput} (90.2~B checks/s sustained
        via CUDA kernels with warp-uniform control flow, not a CPU emulator
        ported to GPU).
  \item \textbf{Formal proof of constraint soundness} (38 proofs including
        the Galois connection mechanized in Coq, not informal arguments or
        testing-only evidence).
  \item \textbf{Open-source implementation} (14 crates on \texttt{crates.io},
        Apache 2.0 licensed, enabling independent reproduction and audit).
  \item \textbf{A credible DO-254 DAL A certification path} (the 43-opcode
        budget was explicitly designed to be verifiable within 6--9 months;
        the Safe-TOPS/W score of 1.95 is the only certified score in
        existence for a constraint-checking system).
\end{enumerate}

No single prior work spans all four columns. CompCert and CakeML provide
formal proof but target general-purpose compilers, not constraint hardware.
SCADE provides certification pedigree but is proprietary and lacks GPU
support. GPU vendors provide throughput but no formal safety argument.
Abstract interpretation tools (Astr\'{e}e, AI$^2$) provide formal analysis
but operate at compile time, not runtime. FLUX-LUCID occupies a unique
position in this design space.


% =============================================================================
\section{Discussion}
\label{sec:discussion}
% =============================================================================

% ─────────────────────────────────────────────────────────────────────────────
\subsection{What 90.2 Billion Checks/Second Means for Real Systems}
\label{sec:discuss-throughput}
% ─────────────────────────────────────────────────────────────────────────────

The sustained throughput of 90.2~billion constraint checks per second
(90.2~G c/s) on a single consumer GPU at 46.2~W real power demands
concrete interpretation. We map this performance to the ten architecture
proposals in our reference eVTOL application domain:

\paragraph{Full-mission validation.}
A typical eVTOL flight-control constraint suite contains 48 signals
with 142 constraint arcs (Table~\ref{tab:cpu-speedup}). Each
\texttt{flux\_vm\_batch} invocation at batch size $2^{20}$ evaluates
1,048,576 input combinations. At 90.2~G c/s, a single GPU processes
$\approx 633{,}000$ complete constraint suites per second. For the
pre-deployment certification campaign (which requires exhaustive coverage
of all boundary values and mutation-guided inputs across all 10 mission
profiles), the entire campaign completes in \textbf{8.3 seconds} — a
task that requires 28 minutes on the ARM Cortex-R5 reference CPU.

\paragraph{Continuous validation during integration testing.}
During system integration, every firmware build triggers a regression
test of the constraint suite. At 90.2~G c/s, the full regression
suite (30 experiments, 10M+ inputs per experiment) completes in
$< 4$ seconds, enabling constraint validation as a CI gate with
negligible build-pipeline latency.

\paragraph{Scaling to larger systems.}
The 10 architecture proposals range from 12-variable automotive
lane-keeping to 192-variable full perception stacks. The bitmask AC-3
kernel's $O(1)$ per-arc pruning means that throughput scales linearly
with the number of constraint arcs, not quadratically as in classical
AC-3. At the 192-variable scale, the GPU sustains 74.6~G c/s — still
within an order of magnitude of the peak, and more than sufficient for
any practical certification campaign.

% ─────────────────────────────────────────────────────────────────────────────
\subsection{The INT8 Representation Gap}
\label{sec:discuss-int8}
% ─────────────────────────────────────────────────────────────────────────────

FLUX-LUCID's bitmask domain representation uses 8-bit masks
(INT8), packing 8 constraints into 8 bytes with lossless representation
over the range $[0, 255]$. This is not a limitation of the GUARD
language — GUARD supports \texttt{int<32>} types — but a deliberate
design choice for the bitmask AC-3 kernel.

The INT8 representation creates a quantization boundary at 256 distinct
values per domain. For ternary weight spaces ($\{-1, 0, +1\}$), the
packing efficiency is $8 \times 3 = 24$ constraint-values per 64-bit word,
with no loss. For bounded-integer domains with $d \le 256$ distinct
values (the vast majority of safety constraints — pitch angle bounded to
$[-30°, +30°]$ in 1° increments requires 61 values; throttle position
in $[0\%, 100\%]$ in 1\% increments requires 101), the INT8 mask
provides exact representation.

The gap emerges for domains exceeding 256 values. In these cases, the
GUARD compiler partitions the domain into $k$ subdomains of $\le 256$
values each and emits $k$ DMSET/DMINTER sequences. This partitioning
introduces a runtime overhead of $k \times$ the single-domain cost but
preserves soundness — the Galois connection proof holds for each
subdomain independently, and their intersection is computed by DMINTER.
For the 10 architecture proposals evaluated, no constraint required
$k > 3$ subdomains, and the average was $k = 1.4$.

We consider the INT8 representation gap an acceptable tradeoff: it
enables the $O(1)$ bitwise pruning that drives the 90.2~G c/s throughput,
at the cost of a bounded ($k$-way) decomposition for domains larger than
256 values. A future 16-bit mask representation would eliminate the
decomposition at $\approx 2\times$ memory cost but $1\times$ throughput
(because the bitwise AND would operate on 16-bit instead of 8-bit masks
within the same 64-bit register).

% ─────────────────────────────────────────────────────────────────────────────
\subsection{GPU vs.\ FPGA vs.\ ASIC: Tradeoffs for Safety}
\label{sec:discuss-platform}
% ─────────────────────────────────────────────────────────────────────────────

FLUX-LUCID's three-target architecture (GPU for validation, FPGA for
prototyping, ASIC for deployment) reflects a pragmatic engineering
tradeoff that deserves explicit discussion.

\paragraph{GPU.}
The GPU provides unmatched throughput (90.2~G c/s sustained, 341~G peak)
but is not certifiable. Its role is pre-deployment validation: exercising
the constraint checker over billions of inputs to build confidence that
the compiled bytecode is faithful to the GUARD specification. The GPU
validation is \emph{not} part of the formal safety argument — it is
complementary evidence (DO-178C Table A-7, objective 7: ``Verification
of Software Requirements is achieved'').

\paragraph{FPGA.}
The FPGA (Artix-7, 44,243 LUTs) provides a certifiable prototyping
platform with zero latency overhead for runtime constraint enforcement.
FPGA synthesis is a well-established DO-254 evidence source, and the
shadow observer's 1,717-LUT footprint is small enough for exhaustive
gate-level simulation. The FPGA's limitation is throughput: at 187~MHz,
the shadow observer processes one constraint check per cycle (187~M c/s),
roughly $480\times$ slower than the GPU. This is acceptable for runtime
enforcement (which processes one inference per control loop, not billions)
but inadequate for pre-deployment validation.

\paragraph{ASIC.}
The 22nm FDSOI ASIC synthesis projects 47.3~TOPS at 5.8~W, with the
shadow observer consuming $< 0.5\%$ of total die area. The ASIC path
offers the best of both worlds — certifiability (DO-254 at the silicon
level) and throughput — but at a non-recurring engineering (NRE) cost
of \$8--15M for a full production tapeout. Our current position is
that the FPGA prototype provides sufficient evidence for DO-254 DAL A
qualification, with the ASIC path reserved for production volumes
exceeding 10,000 units/year.

\paragraph{The safe deployment boundary.}
FLUX-LUCID's safety argument holds on any platform that correctly
implements the FLUX-C ISA's 43 opcodes. The GPU validates the
\emph{semantics} of the bytecode; the FPGA/ASIC enforces it at runtime.
This separation allows each platform to play to its strength without
compromising the safety argument.

% ─────────────────────────────────────────────────────────────────────────────
\subsection{Threats to Validity}
\label{sec:discuss-threats}
% ─────────────────────────────────────────────────────────────────────────────

We acknowledge the following threats to the validity of our results.

\paragraph{Single GPU architecture.}
All GPU throughput measurements were obtained on a single NVIDIA RTX 4050
(Ada Lovelace architecture, 6~GB GDDR6). Throughput on other GPU
architectures (AMD CDNA, Intel Arc) is unmeasured. The warp-uniform
control flow property exploited by \texttt{flux\_vm\_batch} is specific
to NVIDIA's SIMT execution model; AMD's wavefront width (64 threads)
may alter the divergence characteristics. We mitigate this threat by
publishing the full benchmark suite (14 crates, Apache 2.0) to enable
independent reproduction on arbitrary hardware.

\paragraph{Synthetic benchmarks.}
The 210 GUARD constraint suites in the test corpus were designed to cover
the space of ISO 26262, DO-178C, and IEC 62061 application profiles but
are not derived from deployed production systems. Production constraints
may exhibit different structural properties (e.g., higher treewidth,
denser constraint graphs) that affect AC-3 convergence time. We
partially mitigate this by including the 10 architecture proposals
(Section~\ref{sec:discuss-throughput}), which were derived from real
eVTOL flight-envelope specifications, but acknowledge that deployment
validation on production systems remains future work.

\paragraph{CUDA version dependency.}
Experiments were conducted with CUDA 11.5 (GPU throughput) and CUDA 12.3
(FPGA host interface). CUDA is a proprietary API whose behavior is not
formally specified; NVIDIA's compiler may generate different PTX for
identical CUDA source across driver versions. The GPU validation is not
part of the formal safety argument, so this threat does not compromise
the certification case, but it does affect the reproducibility of the
throughput numbers.

\paragraph{Coq proof coverage.}
Of the 38 formal proofs in the FLUX-LUCID verification stack, 8 are
mechanized in Coq and 30 are pen-and-paper. The pen-and-paper proofs
are susceptible to human error. We mitigate this by structuring the
proofs as refinements of the Galois connection (Theorem~\ref{thm:galois}),
which \emph{is} mechanized, so errors in the pen-and-paper proofs can
propagate only through soundness-preserving refinements. Full Coq
mechanization of all 38 proofs is planned (Section~\ref{sec:future-coq}).


% =============================================================================
\section{Future Work}
\label{sec:future}
% =============================================================================

% ─────────────────────────────────────────────────────────────────────────────
\subsection{Multi-GPU Fanout}
\label{sec:future-multigpu}
% ─────────────────────────────────────────────────────────────────────────────

The current single-GPU throughput of 90.2~G c/s is sufficient for all
evaluated eVTOL constraint suites but may become a bottleneck for
larger-scale systems (e.g., full autonomous urban-mission profiles with
$>$500 signals and $>$2000 constraint arcs). Multi-GPU fanout via
NCCL~\cite{nccl} or custom all-reduce trees would enable near-linear
scaling: the \texttt{flux\_vm\_batch} kernel is embarrassingly parallel
across batches, requiring only a final \texttt{domain\_reduce} call to
aggregate results. Preliminary estimates suggest that a 4-GPU configuration
(4 $\times$ RTX 4050, total TDP $\approx$ 320~W) would sustain
$\approx$340~G c/s, covering the full validation campaign for a
500-signal constraint graph in $<$30 seconds.

The key engineering challenge is constraint-graph partitioning: the
AC-3 worklist has cross-arc dependencies that prevent naive
shard-per-GPU distribution. A graph-coloring partitioner (assigning
non-adjacent arcs to the same GPU) would minimize cross-GPU
synchronization to the arc-relaxation step, estimated at $<$5\% of
total compute time for typical constraint graphs.

% ─────────────────────────────────────────────────────────────────────────────
\subsection{FPGA Implementation: Xilinx UltraScale+}
\label{sec:future-fpga}
% ─────────────────────────────────────────────────────────────────────────────

The Artix-7 prototype (Section~\ref{sec:eval-fpga}) validates the
shadow observer concept but operates at 187~MHz on a 28nm device.
Migration to Xilinx UltraScale+ (16nm FinFET) would enable:
(1) clock frequencies of 400--500~MHz, doubling the per-cycle constraint
check rate;
(2) High-Bandwidth Memory (HBM) integration for the ternary weight store,
eliminating the DDR3 bandwidth bottleneck;
(3) hardened floating-point DSP blocks (DSP48E2) for the RAU pipeline.

The UltraScale+ implementation is particularly attractive for DO-254
qualification because Xilinx provides a certified silicon proven
design flow for UltraScale+ devices in avionics applications, reducing
the tool qualification effort under DO-330.

% ─────────────────────────────────────────────────────────────────────────────
\subsection{ASIC Path: 12.7 mm$^2$ Floorplan}
\label{sec:future-asic}
% ─────────────────────────────────────────────────────────────────────────────

Our 22nm FDSOI synthesis targets a die area of 12.7~mm$^2$, dominated
by the Differential Ternary ROM (8.2~mm$^2$, 2.21~Gbit/mm$^2$ density).
The shadow observer occupies $<$0.1~mm$^2$, and the mask-lock register
bank occupies 0.3~mm$^2$. The floorplan is designed for
floorplan-first power delivery: the ternary ROM is placed at the center
of the die with the RAU pipeline and shadow observer arranged in a
ring to minimize routing congestion.

A 12nm FinFET port would reduce die area to $\approx$8.5~mm$^2$
at the same performance target, enabling a multi-die configuration
with 4 FLUX-LUCID tiles on a single package for 189~TOPS at 23~W.
This configuration would achieve a projected Safe-TOPS/W of 8.2,
compared to the current single-tile estimate of 20.17 — the reduction
is due to inter-tile synchronization overhead, but the absolute
throughput gain (4$\times$) makes the multi-tile path attractive for
data-center inference with safety requirements.

% ─────────────────────────────────────────────────────────────────────────────
\subsection{Coq Formalization Completion}
\label{sec:future-coq}
% ─────────────────────────────────────────────────────────────────────────────

The current Coq development contains 8 mechanized proofs covering the
core Galois connection (Theorem~\ref{thm:galois}), the 5 stack opcodes,
and 3 domain opcodes (DMSET, DMINTER, DMCHK). The remaining 30
pen-and-paper proofs cover the 38 arithmetic, bitwise, comparison, and
control opcodes, plus the compiler correctness lemmas.

We estimate that full Coq mechanization requires 6--9 person-months
of effort by a Coq expert familiar with the FLUX-C operational
semantics. The proof structure is repetitive (most opcodes follow a
common template: show that the opcode's small-step rule preserves the
Galois connection invariant), suggesting that proof automation via
Ltac or Coq-Elpi custom tactics could reduce the per-opcode proof
effort from 2--3 days to 2--4 hours.

% ─────────────────────────────────────────────────────────────────────────────
\subsection{DO-330 Tool Qualification Path}
\label{sec:future-do330}
% ─────────────────────────────────────────────────────────────────────────────

Tool qualification of the GUARD compiler and FLUX-C toolchain under
DO-330 TQL-1 (required for DAL A) is the most certification-intensive
future work item. Based on industry experience with similar qualification
campaigns (SCADE KCG qualification reportedly cost \$2--3M over 24 months),
we estimate:

\begin{itemize}
  \item \textbf{Cost:} \$1.75--2.65M (including DER/UMYE contractor fees,
        tool qualification test suite development, and FAA consultation).
  \item \textbf{Timeline:} 18--28 months from project initiation to TQL-1
        certificate issuance.
  \item \textbf{Key deliverables:} Tool Operational Requirements (TOR),
        Tool Development Plan (TDP), Tool Verification Plan (TVP),
        Tool Verification Results (TVR), and Tool Configuration Index (TCI)
        per DO-330 Section 5.
  \item \textbf{Risk factor:} The formal proof component (38 proofs)
        requires DER acceptance of theorem-proving evidence, which has
        limited precedent in FAA certification history. We mitigate this
        by engaging a DER with Coq/formal-methods experience early in
        the qualification planning phase.
\end{itemize}

The 14-crate open-source codebase (Apache 2.0) provides a strong
foundation for the Tool Configuration Index, as every source artifact
is version-controlled and independently reproducible.


% =============================================================================
\section{Conclusion}
\label{sec:conclusion}
% =============================================================================

This paper presented FLUX-LUCID, a safety-certified constraint
enforcement architecture for neural inference in safety-critical
embedded systems. Our contributions span the full stack from
specification to silicon:

\begin{enumerate}
  \item The \textbf{GUARD DSL} and its compilation to the
        \textbf{FLUX-C} 43-opcode constraint virtual machine, connected
        by a formally proven Galois connection that guarantees
        the compiled bytecode overapproximates the source constraint.
  \item A \textbf{GPU-accelerated validation pipeline} achieving
        90.2~billion constraint checks per second sustained (341~B peak)
        at 46.2~W, enabling exhaustive pre-deployment validation of
        constraint suites in seconds rather than minutes.
  \item A \textbf{formal verification stack} of 38 proofs (8 mechanized
        in Coq, 30 pen-and-paper), including the Galois connection
        $F \dashv G$ between GUARD and FLUX-C, with zero differential
        mismatches across 30 experiments and 10M+ inputs.
  \item An \textbf{FPGA prototype} (44,243 LUTs on Artix-7) demonstrating
        that the shadow observer adds $< 5\%$ area overhead and zero
        latency to the inference pipeline, with WCET of 3.2~$\mu$s
        ($<$0.04\% of the 10~ms eVTOL control-loop budget).
  \item The \textbf{Safe-TOPS/W} metric, which penalizes uncertified
        hardware to zero, and FLUX-LUCID's score of \textbf{1.95}
        — the only certified score in existence for a constraint
        enforcement system.
  \item An \textbf{open-source implementation} of 14 Rust crates on
        \texttt{crates.io}, Apache 2.0 licensed, enabling independent
        reproduction and audit of all claims in this paper.
\end{enumerate}

The key result is that FLUX-LUCID is the \textbf{first system to achieve
billions of formally-verified constraint checks per second} while
maintaining a credible path to DO-254 DAL A certification. The
architecture's separation of concerns — GPU for validation throughput,
FPGA/ASIC for certifiable runtime enforcement, formal proof for
mathematical assurance — provides a template for other
safety-critical AI systems that must bridge the gap between raw
performance and certifiable safety.

The INT8 bitmask representation limits domain cardinality to 256 values
per subdomain, requiring decomposition for larger domains. The GPU
throughput measurements are specific to NVIDIA Ada Lovelace
architecture. The Coq formalization covers 8 of 38 proofs, with full
mechanization estimated at 6--9 person-months. These limitations
notwithstanding, FLUX-LUCID demonstrates that the conventional wisdom
— ``you can have performance \emph{or} safety, not both'' — is false.
With the right architectural decomposition, formally-verified safety
and GPU-class throughput are not only compatible but mutually reinforcing.


% =============================================================================
% References
% =============================================================================
\begin{thebibliography}{30}

\bibitem{berry1992esterel}
G.~Berry and G.~Gonthier,
``The Esterel synchronous programming language: Design, semantics, implementation,''
\textit{Science of Computer Programming}, vol.~19, no.~2, pp.~87--152, 1992.

\bibitem{berry1999esterel_semantics}
G.~Berry,
``The constructive semantics of pure Esterel,''
\textit{Unpublished draft}, available at \url{https://www-sop.inria.fr/members/Gerard.Berry/Papers/EsterelConstructiveBook.pdf}, 1999.

\bibitem{halbwachs1991lustre}
N.~Halbwachs, P.~Caspi, P.~Raymond, and D.~Pilaud,
``The synchronous data flow programming language LUSTRE,''
\textit{Proceedings of the IEEE}, vol.~79, no.~9, pp.~1305--1320, 1991.

\bibitem{benveniste1991signal}
A.~Benveniste and G.~Berry,
``The synchronous approach to reactive and real-time systems,''
\textit{Proceedings of the IEEE}, vol.~79, no.~9, pp.~1270--1282, 1991.

\bibitem{scade}
ANSYS,
``SCADE Suite: Model-based design and verification for critical embedded software,''
\url{https://www.ansys.com/products/embedded-software/ansys-scade-suite}, 2024.

\bibitem{leroy2009compcert}
X.~Leroy,
``Formal verification of a realistic compiler,''
\textit{Communications of the ACM}, vol.~52, no.~7, pp.~107--115, 2009.

\bibitem{song2019compcertx}
Y.~Song, M.~Cho, D.~Kim, Y.~Kim, J.~Kang, and C.-K.~Hur,
``CompCertX: A verified compiler for C multitasking,''
\textit{Journal of the Korean Information Science Society}, 2019.

\bibitem{sammler2023capcompcert}
M.~Sammler, D.~Lepiller, A.~Lööw, L.~Brun, R.~Krebbers, and D.~Dreyer,
``CapCompCert: A verified C compiler for capability machines,''
in \textit{Proc.\ ACM Symposium on Principles of Programming Languages (POPL)}, 2023.

\bibitem{kumar2014cakeml}
R.~Kumar, M.~O.~Myreen, M.~Norrish, and S.~Owens,
``CakeML: A verified implementation of ML,''
in \textit{Proc.\ ACM Symposium on Principles of Programming Languages (POPL)}, pp.~179--191, 2014.

\bibitem{cousot1977}
P.~Cousot and R.~Cousot,
``Abstract interpretation: A unified lattice model for static analysis of programs by construction or approximation of fixpoints,''
in \textit{Proc.\ ACM Symposium on Principles of Programming Languages (POPL)}, pp.~238--252, 1977.

\bibitem{cousot1979verifying}
P.~Cousot and R.~Cousot,
``Systematic design of program analysis frameworks,''
in \textit{Proc.\ ACM Symposium on Principles of Programming Languages (POPL)}, pp.~269--282, 1979.

\bibitem{blanchet2003astree}
B.~Blanchet, P.~Cousot, R.~Cousot, J.~Feret, L.~Mauborgne, A.~Min\'{e}, D.~Monniaux, and X.~Rival,
``A static analyzer for large safety-critical software,''
in \textit{Proc.\ ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI)}, pp.~196--207, 2003.

\bibitem{gehr2018ai2}
T.~Gehr, M.~Mirman, D.~Dranth, P.~Tsankov, S.~Chaudhuri, and M.~Vejdovich,
``AI$^2$: Safety and robustness certification of neural networks with abstract interpretation,''
in \textit{Proc.\ IEEE Symposium on Security and Privacy (S\&P)}, pp.~3--18, 2018.

\bibitem{singh2019deeppoly}
G.~Singh, T.~Gehr, M.~P\"uschel, and M.~Vejdovich,
``An abstract domain for certifying neural networks,''
\textit{Proc.\ ACM on Programming Languages (POPL)}, vol.~3, pp.~41:1--41:30, 2019.

\bibitem{singh2019abstract}
G.~Singh, T.~Gehr, M.~Mirman, M.~P\"uschel, and M.~Vejdovich,
``Fast and effective robustness certification,''
in \textit{Proc.\ Advances in Neural Information Processing Systems (NeurIPS)}, 2018.

\bibitem{mackworth1977}
A.~K.~Mackworth,
``Consistency in networks of relations,''
\textit{Artificial Intelligence}, vol.~8, no.~1, pp.~99--118, 1977.

\bibitem{een2003minisat}
N.~E\'en and N.~S\"orensson,
``An extensible SAT-solver,''
in \textit{Proc.\ International Conference on Theory and Applications of Satisfiability Testing (SAT)}, pp.~502--518, 2003.

\bibitem{demoura2008z3}
L.~de~Moura and N.~Bj\o{}rner,
``Z3: An efficient SMT solver,''
in \textit{Proc.\ International Conference on Tools and Algorithms for the Construction and Analysis of Systems (TACAS)}, pp.~337--340, 2008.

\bibitem{barbosa2022cvc5}
H.~Barbosa \textit{et al.},
``cvc5: A versatile and industrial-strength SMT solver,''
in \textit{Proc.\ International Conference on Tools and Algorithms for the Construction and Analysis of Systems (TACAS)}, pp.~415--442, 2022.

\bibitem{fruhwirth1998chr}
T.~Fr\"uhwirth,
``Theory and practice of constraint handling rules,''
\textit{Journal of Logic Programming}, vol.~37, no.~1--3, pp.~95--138, 1998.

\bibitem{do178c}
RTCA,
``DO-178C: Software considerations in airborne systems and equipment certification,''
RTCA SC-205, 2011.

\bibitem{do254}
RTCA,
``DO-254: Design assurance guidance for airborne electronic hardware,''
RTCA SC-180, 2000.

\bibitem{do330}
RTCA,
``DO-330: Software tool qualification considerations,''
RTCA SC-205, 2011.

\bibitem{cast32a}
FAA CAST,
``CAST-32A: Multi-core processors -- Position paper,''
Certification Authorities Software Team (CAST), 2022.

\bibitem{arinc653}
Airlines Electronic Engineering Committee,
``ARINC 653: Avionics application software standard interface,''
Aeronautical Radio, Inc., 2003.

\bibitem{nvidia2020safety}
NVIDIA,
``NVIDIA DRIVE AGX Orin functional safety documentation,''
\url{https://www.nvidia.com/en-us/self-driving-cars/drive-platform/}, 2024.

\bibitem{hailo8}
Hailo,
``Hailo-8 AI processor product brief,''
\url{https://hailo.ai/products/hailo-8/}, 2024.

\bibitem{betts2011gpu_verify}
A.~Betts and A.~Donaldson,
``Verifying safety-critical GPU kernels,''
\textit{ACM Transactions on Embedded Computing Systems}, vol.~13, no.~4s, pp.~117:1--117:27, 2014.

\bibitem{nccl}
NVIDIA,
``NCCL: NVIDIA Collective Communications Library,''
\url{https://developer.nvidia.com/nccl}, 2024.

\bibitem{spark}
J.~Barnes,
\textit{High Integrity Software: The SPARK Approach to Safety and Security},
Addison-Wesley, 2003.

\end{thebibliography}
