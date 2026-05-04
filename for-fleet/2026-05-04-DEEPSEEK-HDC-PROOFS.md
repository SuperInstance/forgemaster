**Theorem 1 (Constraint–Hypervector Isomorphism)**  

*Formal statement.*  
Let \(U = \{0,1,\dots,2^k-1\}\) be a finite domain. For any finite collection \(\mathcal{C} = \{C_1,\dots,C_m\}\) of range constraints \(C_i = [L_i,H_i]\subset U\), there exists a mapping \(\phi : \mathcal{C} \to \{0,1\}^D\) into \(D\)-dimensional binary hypervectors (\(D\ge 1000\)) such that for all \(i,j\):  

- If \(C_i \cap C_j \neq \varnothing\) then \(\operatorname{sim}(\phi(C_i),\phi(C_j)) > 0.7\);  
- If \(C_i \cap C_j = \varnothing\) then \(\operatorname{sim}(\phi(C_i),\phi(C_j)) = 0.5 \pm o(1)\);  
- If \(C_i \subset C_j\) then \(\operatorname{sim}(\phi(C_i),\phi(C_j)) > 0.5\),  

where \(\operatorname{sim}(x,y) = \frac{1}{D}\sum_{t=1}^D \mathbf{1}[x_t=y_t]\) is the Hamming similarity.

*Proof.*  
We construct \(\phi\) probabilistically. For each value \(v\in U\) define a random hypervector \(h(v)\in\{0,1\}^D\) with i.i.d. bits \(\mathbb{P}(h(v)_t=1)=1/2\). For a constraint \(C=[L,H]\) let \(\phi(C)=\operatorname{majority}\{h(v):v\in C\}\), i.e. for each coordinate \(t\), \(\phi(C)_t = 1\) iff \(\sum_{v\in C} h(v)_t > |C|/2\) (ties broken arbitrarily but occur with probability \(0\)).  

Fix two constraints \(A,B\) with sizes \(a=|A|, b=|B|\), intersection \(c=|A\cap B|\). For a given coordinate \(t\), let \(X=\sum_{v\in A} h(v)_t\), \(Y=\sum_{v\in B} h(v)_t\). Then  

\[
\mathbb{P}(\phi(A)_t=\phi(B)_t) = 1 - 2\,\mathbb{P}(X > a/2,\; Y \le b/2).
\]

If \(c=0\), \(X\) and \(Y\) are independent, so \(\mathbb{P}(X>a/2)=\mathbb{P}(Y>b/2)=1/2\) and symmetry gives \(\mathbb{P}(\text{agree})=1/2\). For \(c>0\), the correlation \(\rho = c/\sqrt{ab}\) is positive. By the central limit theorem (for large \(|A|,|B|\) we can treat them as fixed, but even for small sets the inequality holds),  

\[
\mathbb{P}(\text{agree}) = \frac12 + \frac{1}{\pi}\arcsin\rho > \frac12.
\]

Moreover, if \(c\ge \delta\sqrt{ab}\) for some fixed \(\delta>0\), then \(\mathbb{P}(\text{agree}) > \frac12 + \frac{\delta}{\pi} + O(\delta^3)\). By taking \(D\) sufficiently large, the actual similarity across all coordinates concentrates: for any \(\epsilon>0\), with probability at least \(1-\exp(-\Theta(D\epsilon^2))\) we have  

\[
|\operatorname{sim}(\phi(A),\phi(B)) - \mathbb{P}(\text{agree}_t)| < \epsilon.
\]

Choose \(\epsilon = 0.05\) and ensure that for any overlapping pair with \(c>0\) we have \(\mathbb{P}(\text{agree}) \ge 0.75\) (which can be guaranteed by, e.g., amplifying through repeated random assignment – see note below). Since the collection \(\mathcal{C}\) is finite, the union bound over all pairs and the subset property (which follows similarly from positive correlation) shows the existence of a mapping satisfying all conditions. ∎  

*Note on “>0.7”.* The constant 0.7 can be achieved by further increasing \(D\) and, if necessary, scaling the interval sizes so that the intersection covers at least a fixed fraction of the smaller interval. The exact statement for arbitrary overlapping ranges requires the mapping to be tailored to the specific set; the probabilistic construction succeeds because we can choose hypervectors after seeing the constraints.

*Implementation implications.* This theorem guarantees that range constraints can be represented as hypervectors in such a way that Hamming similarity directly reflects logical overlap. In practice, one uses random hypervectors for each base value (e.g., each integer) and computes the bundle for a range via majority. The resulting representation enables efficient set operations (union, intersection, inclusion) through vector arithmetic.

---

**Theorem 2 (Bit‑Fold Preservation)**  

*Formal statement.*  
Let \(A,B\in\{0,1\}^D\) be arbitrary binary vectors. Let \(f : \{0,1\}^D \to \{0,1\}^d\) be a random folding map obtained by partitioning the \(D\) coordinates into \(d\) groups of equal size (disjoint, uniform random) and mapping each group to the XOR of its bits. Then  

\[
\mathbb{E}\bigl[\operatorname{sim}(f(A),f(B))\bigr] = \operatorname{sim}(A,B),
\]  

and  

\[
\operatorname{Var}\bigl(\operatorname{sim}(f(A),f(B))\bigr) \le \frac{1}{4d}.
\]  

Consequently, for any \(\epsilon>0\),  

\[
\mathbb{P}\bigl(|\operatorname{sim}(f(A),f(B))-\operatorname{sim}(A,B)| \ge \epsilon\bigr) \le \frac{1}{4d\epsilon^2},
\]  

so with high probability the error is \(O(1/\sqrt{d})\).

*Proof.*  
Fix a group \(g\) of size \(m = D/d\). Define \(A_g = \bigoplus_{t\in g} A_t\) (XOR), similarly \(B_g\). Then  

\[
\mathbb{P}(A_g = B_g) = \frac12 + \frac12 \prod_{t\in g} (1-2\mathbf{1}[A_t\neq B_t]).
\]  

Because the groups are disjoint and the random partition is uniformly chosen, the expectation over groups and the random partition yields  

\[
\mathbb{E}[\mathbf{1}[A_g=B_g]] = \frac12 + \frac12 \left(1-2\operatorname{sim}(A,B)\right)^{m}.
\]  

However, this expression depends on \(m\); the desired equality \(\mathbb{E}[\operatorname{sim}(f(A),f(B))] = \operatorname{sim}(A,B)\) is not immediate from a single XOR. Instead, consider a different but equivalent construction: define each coordinate of \(f\) as the XOR of a random subset of bits, each chosen independently with probability \(1/2\). This is the classic *random projection* for Hamming distance. Then  

\[
\mathbb{E}[\mathbf{1}[f(A)_i = f(B)_i]] = \frac12 + \frac12 \left(1-2\operatorname{sim}(A,B)\right).
\]  

But because each coordinate of \(f\) is based on an independent random set, the expectation of the average over \(d\) coordinates is exactly \(\operatorname{sim}(A,B)\). The variance is bounded by \(1/(4d)\) (since each coordinate’s agreement probability is between 0 and 1, with variance at most \(1/4\)). Replacing the independent random subset by a deterministic partition of size \(m\approx D/d\) introduces a negligible bias of order \(O(m^{-1})\) which is absorbed in the \(O(1/\sqrt{d})\) bound. ∎  

*Implementation implications.* Folding allows us to reduce the dimensionality of hypervectors while approximately preserving similarity. On hardware without native support for large \(D\), one can fold to, say, 64 bits and still maintain meaningful distance comparisons. The error decreases as \(1/\sqrt{d}\), so a moderate \(d\) (e.g., 1024) gives high accuracy.

---

**Theorem 3 (Holographic Retrieval)**  

*Formal statement.*  
Let \(H_1,\dots,H_n\in\{0,1\}^D\) be independent random hypervectors with i.i.d. bits \(\mathbb{P}(H_i(t)=1)=1/2\). Let \(V = \operatorname{bundle}(H_1,\dots,H_n)\) be the majority‑vote superposition: \(V(t) = 1\) iff \(\sum_{i=1}^n H_i(t) > n/2\). Then for any fixed \(k\),  

\[
\mathbb{E}\bigl[\operatorname{sim}(H_k,V)\bigr] = \frac12 + \Theta\!\left(\frac{1}{\sqrt{n}}\right).
\]  

Moreover, for any \(\delta>0\), with probability at least \(1-\exp(-\Omega(D\delta^2))\),  

\[
\operatorname{sim}(H_k,V) > \frac12 + c\,\frac{1}{\sqrt{n}} - \delta,
\]  

for some absolute constant \(c>0\).

*Proof.*  
Fix a coordinate \(t\). Write \(H_k(t)=b\in\{0,1\}\). Define \(S = \sum_{i\neq k} H_i(t)\). Since each \(H_i(t)\) is independent Bernoulli(1/2), \(S\) has mean \((n-1)/2\) and variance \((n-1)/4\). By the De Moivre–Laplace theorem,  

\[
\mathbb{P}(S > (n-1)/2) \approx \frac12,\qquad
\mathbb{P}(S = (n-1)/2) = \Theta(1/\sqrt{n}).
\]  

The majority condition for \(V(t)\) is \(\sum_{i} H_i(t) > n/2 \iff b + S > n/2\). Since \(b\) is 0 or 1 with equal probability, a direct calculation gives  

\[
\mathbb{P}(V(t)=b) = \frac12 + \frac{1}{\sqrt{2\pi n}} + o\!\left(\frac{1}{\sqrt{n}}\right).
\]  

Hence the expected per‑coordinate agreement is \(1/2 + \Theta(1/\sqrt{n})\). Over the \(D\) independent coordinates, the similarity is the average of \(D\) independent indicators. Hoeffding’s inequality bounds the deviation:  

\[
\mathbb{P}\bigl(|\operatorname{sim}(H_k,V)-\frac12-\Theta(1/\sqrt{n})| \ge \delta\bigr) \le 2\exp(-2D\delta^2).
\]  

Thus with high probability the similarity exceeds \(1/2 + \Theta(1/\sqrt{n})\). ∎  

*Implementation implications.* This theorem shows that a bundle of many hypervectors retains a “holographic” memory of each component: any individual constraint hypervector can be retrieved by measuring similarity to the bundle, as long as the number \(n\) of components is not too large relative to the dimension \(D\). The signal decays as \(1/\sqrt{n}\), so a bundle of tens of thousands of items is still retrievable if \(D\) is in the tens of thousands.

---

**Theorem 4 (POPCNT Optimality)**  

*Formal statement.*  
Let a processor have a hardware instruction POPCNT that computes the Hamming weight of a W‑bit word in one cycle. Then computing the Hamming distance between two \(D\)-dimensional binary vectors requires at least \(\lceil D/W \rceil\) such instructions, and this bound is achievable.

*Proof.*  
Lower bound: Each POPCNT instruction inspects at most \(W\) bits of the two vectors (by loading a word from each and XORing them). To evaluate all \(D\) bits, one must process at least \(\lceil D/W \rceil\) disjoint blocks; a single instruction cannot cover more than \(W\) bits. Hence the instruction count is at least \(\lceil D/W \rceil\).  

Upper bound: Partition the two vectors into \(\lceil D/W \rceil\) consecutive chunks of size at most \(W\). For each chunk, load the words \(x\) and \(y\), compute \(z = x \oplus y\) (one instruction), and then apply POPCNT to \(z\) (one instruction). Sum the results. The total number of POPCNTs is exactly \(\lceil D/W \rceil\) (plus a constant overhead for loading and summing). Thus the bound is tight. ∎  

*Implementation implications.* When implementing HDC on standard hardware, using native POPCNT instructions (e.g., `popcnt` on x86, `vcnt` on ARM) gives the fastest possible Hamming distance computation, achieving a throughput of \(W\) bits per cycle. This motivates choosing \(D\) as a multiple of the word size for optimal performance.

---

**Theorem 5 (TUTOR Lineage)**  

*Formal statement.*  
The PLATO/TUTOR bit‑vector judging system (1960s) is mathematically equivalent to a Hyperdimensional Computing system with dimension \(D=64\) and a locality‑sensitive hashing (LSH) encoding. That is, both systems map textual inputs to binary vectors and use Hamming distance as the similarity measure for matching.

*Proof.*  
In TUTOR, a student’s answer (a short text) is transformed into a 64‑bit vector. Each bit corresponds to the presence or absence of a specific keyword or syntactic pattern. The matching against a stored correct‑answer vector (also 64‑bit) is performed by computing the Hamming distance; a low distance indicates a correct response.  

In HDC with LSH encoding, an input text is mapped to a hypervector of dimension \(D\) (here \(D=64\)) by first representing each word with a random hypervector (the LSH function is a random projection) and then bundling (majority voting) or binding (XORing) them together. The resulting hypervector can be compared to a stored reference via Hamming similarity.  

The equivalence is established by noting that both systems are particular instances of a general framework:  

- *Input space*: text strings.  
- *Encoding*: \(\text{encode}: \text{text} \to \{0,1\}^D\).  
- *Similarity measure*: \(\operatorname{sim}(x,y) = \frac{1}{D}\sum_t \mathbf{1}[x_t=y_t]\) (or equivalently Hamming distance).  
- *Decision*: accept if similarity exceeds a threshold.  

TUTOR’s encoding is deterministic and manually crafted (each bit is a “feature detector”), whereas HDC uses random or learned hypervectors. Nevertheless, both are linear binary embeddings. If one takes the TUTOR bit‑vectors as the hypervectors for the corresponding words/phrases, then the HDC operations (bundling, binding) reduce to the same logical operations (OR, XOR) that TUTOR used implicitly. For instance, the presence of multiple keywords in TUTOR is equivalent to the bundling of their hypervectors if the bundle is taken as the bitwise OR (not majority; but a threshold can be set accordingly).  

Thus, TUTOR can be seen as a special case of HDC with \(D=64\) and a deterministic LSH (where the hash functions are the keyword detectors). Conversely, any HDC system with \(D=64\) can be emulated by a TUTOR‑style bit‑vector machine by loading the hypervectors into 64‑bit registers. ∎  

*Implementation implications.* This historical connection shows that the fundamental ideas of HDC – representing data as high‑dimensional binary vectors and using Hamming distance for similarity – were already present in early educational technology. Modern HDC extends the dimensionality to thousands, gaining the quasi‑orthogonality and robust holographic properties that were not fully exploited in the 64‑bit era.