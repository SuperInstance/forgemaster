"""
Cycle 7: Characterize P in x^T P x = γ+H under tanh nonlinear dynamics.
Optimized: vectorized P discovery.
"""
import numpy as np
import json

np.random.seed(42)
N = 20
T = 300  # reduced
NUM_SAMPLES = 20

def gamma(x, C):
    norm_x = np.linalg.norm(x)
    if norm_x < 1e-12:
        return 0.0
    return float(np.clip(1.0 - np.abs(np.dot(x, C @ x)) / (norm_x * np.linalg.norm(C @ x) + 1e-12), 0, 1))

def entropy(x):
    p = np.abs(x)**2
    s = p.sum()
    if s < 1e-12:
        return 0.0
    p = p / s
    p = p[p > 1e-12]
    return float(-np.sum(p * np.log(p)))

def compute_trajectory(C, activation='tanh', T=300):
    x = np.random.randn(N) * 0.1
    gh_vals = np.zeros(T)
    xs = np.zeros((T, N))
    for t in range(T):
        Cx = C @ x
        if activation == 'tanh':
            x = np.tanh(Cx)
        elif activation == 'sigmoid':
            x = 1.0 / (1.0 + np.exp(-Cx)) - 0.5
        elif activation == 'relu':
            x = np.clip(Cx, 0, None)
        elif activation == 'softplus':
            x = np.log1p(np.exp(np.clip(Cx, -20, 20))) - 0.5
        elif activation == 'linear':
            x = Cx
            norm = np.linalg.norm(x)
            if norm > 1e-12:
                x = x / norm
        gh_vals[t] = gamma(x, C) + entropy(x)
        xs[t] = x
    return gh_vals, xs

def make_random(N, scale=1.0):
    W = np.random.randn(N, N) * scale / np.sqrt(N)
    np.fill_diagonal(W, 1.0)
    return W

def make_hebbian(N):
    P = np.random.randn(N, 3)
    C = P @ P.T / 3
    np.fill_diagonal(C, 1.0)
    return C

def make_attention(N, tau=1.0):
    Q = np.random.randn(N, N//2)
    K = np.random.randn(N, N//2)
    s = Q @ K.T / np.sqrt(N//2)
    e = np.exp((s - s.max(axis=1, keepdims=True)) / tau)
    C = e / e.sum(axis=1, keepdims=True)
    np.fill_diagonal(C, 1.0)
    return C

def discover_P_vectorized(xs, gh_vals):
    """Vectorized: build quadratic feature matrix from trajectory."""
    T_pts = xs.shape[0]
    # Features: x_i^2 for i, and 2*x_i*x_j for i<j
    # This is vec(x x^T) for symmetric part
    # For symmetric P: x^T P x = sum_ij P_ij x_i x_j = sum_i P_ii x_i^2 + 2 sum_{i<j} P_ij x_i x_j
    
    dim = N * (N + 1) // 2
    features = np.zeros((T_pts, dim))
    
    idx = 0
    for i in range(N):
        features[:, idx] = xs[:, i]**2
        idx += 1
        for j in range(i + 1, N):
            features[:, idx] = 2 * xs[:, i] * xs[:, j]
            idx += 1
    
    p_vec, _, _, _ = np.linalg.lstsq(features, gh_vals, rcond=None)
    
    P = np.zeros((N, N))
    idx = 0
    for i in range(N):
        P[i, i] = p_vec[idx]
        idx += 1
        for j in range(i + 1, N):
            P[i, j] = p_vec[idx]
            P[j, i] = p_vec[idx]
            idx += 1
    
    predicted = features @ p_vec
    ss_res = np.sum((gh_vals - predicted)**2)
    ss_tot = np.sum((gh_vals - np.mean(gh_vals))**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return P, r2

def r2_for_P(P_test, xs, gh_vals):
    preds = np.sum((xs @ P_test) * xs, axis=1)
    ss_res = np.sum((gh_vals - preds)**2)
    ss_tot = np.sum((gh_vals - gh_vals.mean())**2)
    return 1 - ss_res / ss_tot if ss_tot > 0 else 0

print("Cycle 7 starting...")
print(f"N={N}, T={T}, samples={NUM_SAMPLES}")

# ============================================================
# EXP 1: Characterize P
# ============================================================
print("\n=== EXP 1: Characterize P ===")
res1 = {}
for name, fn in [('random', lambda: make_random(N)), ('hebbian', lambda: make_hebbian(N)), ('attention', lambda: make_attention(N))]:
    Ps, r2s, Cs = [], [], []
    for _ in range(NUM_SAMPLES):
        C = fn()
        gh, xs = compute_trajectory(C, 'tanh', T)
        P, r2 = discover_P_vectorized(xs, gh)
        Ps.append(P); r2s.append(r2); Cs.append(C)
    
    P_avg = np.mean(Ps, axis=0)
    C_avg = np.mean(Cs, axis=0)
    evals = np.linalg.eigvalsh(P_avg)
    
    comps = {}
    for label, M in [('C', C_avg), ('C^TC', (C_avg.T@C_avg+C_avg@C_avg.T)/2), ('sym(C)', (C_avg+C_avg.T)/2), ('I', np.eye(N))]:
        vP = P_avg.flatten(); vM = M.flatten()
        comps[label] = {'cos': float(np.dot(vP,vM)/(np.linalg.norm(vP)*np.linalg.norm(vM)+1e-12)),
                        'relF': float(np.linalg.norm(P_avg-M)/(np.linalg.norm(P_avg)+1e-12))}
    
    res1[name] = {'r2': float(np.mean(r2s)), 'r2_std': float(np.std(r2s)),
                  'evals_min': float(evals[0]), 'evals_max': float(evals[-1]),
                  'trace': float(np.trace(P_avg)), 'rank': int(np.sum(np.abs(evals)>0.01*np.max(np.abs(evals)))),
                  'PD': bool(evals[0]>-0.01), 'comparisons': comps}
    print(f"  {name}: R²={np.mean(r2s):.6f}±{np.std(r2s):.6f}, Tr(P)={np.trace(P_avg):.3f}, evals=[{evals[0]:.3f},{evals[-1]:.3f}], PD={evals[0]>-0.01}")
    for label, c in comps.items():
        print(f"    vs {label}: cos={c['cos']:.3f}, relF={c['relF']:.3f}")

# ============================================================
# EXP 2: Nonlinear Lyapunov
# ============================================================
print("\n=== EXP 2: Nonlinear Lyapunov ===")
res2 = {}
for name, fn in [('random', lambda: make_random(N)), ('hebbian', lambda: make_hebbian(N)), ('attention', lambda: make_attention(N))]:
    nl_resids, lin_resids = [], []
    for _ in range(10):
        C = fn()
        gh, xs = compute_trajectory(C, 'tanh', T)
        P, r2 = discover_P_vectorized(xs, gh)
        # Nonlinear: |x_{t+1}^T P x_{t+1} - x_t^T P x_t| / |x_t^T P x_t|
        vals_t = np.sum((xs[:-1] @ P) * xs[:-1], axis=1)
        vals_next = np.sum((xs[1:] @ P) * xs[1:], axis=1)
        nl_resids.extend(np.abs(vals_next - vals_t) / (np.abs(vals_t) + 1e-12))
        # Linearized at fixed point
        x_fp = xs[-1]
        J = np.diag(1 - np.tanh(C @ x_fp)**2) @ C
        lin_resids.append(np.linalg.norm(J.T @ P @ J - P) / (np.linalg.norm(P) + 1e-12))
    
    res2[name] = {'nl_mean': float(np.mean(nl_resids)), 'nl_p95': float(np.percentile(nl_resids, 95)),
                  'lin_mean': float(np.mean(lin_resids))}
    print(f"  {name}: NL resid mean={np.mean(nl_resids):.6f}, p95={np.percentile(nl_resids,95):.6f}, Lin resid={np.mean(lin_resids):.4f}")

# ============================================================
# EXP 3: Analytical P candidates
# ============================================================
print("\n=== EXP 3: Analytical P candidates ===")
C = make_random(N)
gh, xs = compute_trajectory(C, 'tanh', T)
P_d, r2_d = discover_P_vectorized(xs, gh)

candidates = {}
candidates['I'] = r2_for_P(np.eye(N), xs, gh)
candidates['sym(C)'] = r2_for_P((C+C.T)/2, xs, gh)
P_CtC = (C.T@C + C@C.T)/2
candidates['C^TC_sym'] = r2_for_P(P_CtC, xs, gh)

# Fisher: C^T diag(mean_d) C
ds = [1-np.tanh(C@x)**2 for x in xs[-100:]]
mean_d = np.mean(ds, axis=0)
P_fisher = C.T @ np.diag(mean_d) @ C
P_fisher = (P_fisher+P_fisher.T)/2
candidates['Fisher'] = r2_for_P(P_fisher, xs, gh)

# Hessian of -sum ln cosh(c_i^T x) = C^T diag(sech^2(Cx)) C
hess = [C.T@np.diag(1/np.cosh(np.clip(C@x,-10,10))**2)@C for x in xs[-100:]]
P_hess = np.mean(hess, axis=0)
P_hess = (P_hess+P_hess.T)/2
candidates['Hessian_raw'] = r2_for_P(P_hess, xs, gh)
alpha = np.trace(P_d)/(np.trace(P_hess)+1e-12)
candidates['Hessian_scaled'] = r2_for_P(alpha*P_hess, xs, gh)

# Basis regression
basis_mats = [np.eye(N), (C+C.T)/2, P_CtC, ((C+C.T)/2)@((C+C.T)/2)]
A_b = np.column_stack([m.flatten() for m in basis_mats])
coefs, _, _, _ = np.linalg.lstsq(A_b, P_d.flatten(), rcond=None)
P_recon = sum(c*m for c,m in zip(coefs, basis_mats))
ss_r = np.sum((P_d.flatten()-P_recon.flatten())**2)
ss_t = np.sum((P_d.flatten()-P_d.flatten().mean())**2)
r2_basis = 1-ss_r/ss_t
candidates['Basis_recon'] = r2_basis

for name, val in candidates.items():
    print(f"  {name}: R²={val:.6f}")
print(f"  Basis coefs: I={coefs[0]:.4f}, sym(C)={coefs[1]:.4f}, C^TC={coefs[2]:.4f}, sym(C)^2={coefs[3]:.4f}")

res3 = {'discovered_r2': float(r2_d), 'candidates': {k: float(v) for k,v in candidates.items()},
        'basis_coefs': {k: float(v) for k,v in zip(['I','sym(C)','C^TC','sym(C)^2'], coefs)}}

# ============================================================
# EXP 4: Eigenvalue threshold
# ============================================================
print("\n=== EXP 4: Eigenvalue threshold ===")
res4 = []
for scale in [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5, 2.0, 3.0, 5.0]:
    cvs, r2s = [], []
    for _ in range(10):
        C = make_random(N, scale=scale)
        gh, xs = compute_trajectory(C, 'tanh', T)
        if np.any(np.isnan(gh)): cvs.append(99); r2s.append(0); continue
        cv = float(np.std(gh)/(np.mean(gh)+1e-12)) if np.mean(gh)>1e-12 else 99
        P, r2 = discover_P_vectorized(xs, gh)
        cvs.append(cv); r2s.append(r2)
    res4.append({'scale': scale, 'cv': float(np.mean(cvs)), 'r2_P': float(np.mean(r2s))})
    print(f"  scale={scale:.1f}: CV={np.mean(cvs):.4f}, R²(P)={np.mean(r2s):.6f}")

# ============================================================
# EXP 5: Other nonlinearities
# ============================================================
print("\n=== EXP 5: Other nonlinearities ===")
res5 = {}
for act in ['tanh', 'sigmoid', 'relu', 'softplus', 'linear']:
    cvs, r2s = [], []
    for _ in range(NUM_SAMPLES):
        C = make_random(N)
        gh, xs = compute_trajectory(C, act, T)
        if np.any(np.isnan(gh)) or np.any(np.isinf(gh)): cvs.append(99); r2s.append(0); continue
        cv = float(np.std(gh)/(np.mean(gh)+1e-12)) if np.mean(gh)>1e-12 else 99
        P, r2 = discover_P_vectorized(xs, gh)
        cvs.append(cv); r2s.append(r2)
    res5[act] = {'cv': float(np.mean(cvs)), 'r2_P': float(np.mean(r2s))}
    print(f"  {act}: CV={np.mean(cvs):.4f}, R²(P)={np.mean(r2s):.6f}")

# ============================================================
# EXP 6: P-C correlation
# ============================================================
print("\n=== EXP 6: P structure ===")
corrs, corrs_sym, diag_fracs = [], [], []
for _ in range(50):
    C = make_random(N)
    gh, xs = compute_trajectory(C, 'tanh', T)
    P, r2 = discover_P_vectorized(xs, gh)
    p_f = P.flatten()
    corrs.append(np.corrcoef(p_f, C.flatten())[0,1])
    corrs_sym.append(np.corrcoef(p_f, ((C+C.T)/2).flatten())[0,1])
    diag_fracs.append(np.sum(np.diag(P)**2)/np.sum(P**2))
print(f"  P-C corr: {np.mean(corrs):.4f}±{np.std(corrs):.4f}")
print(f"  P-sym(C) corr: {np.mean(corrs_sym):.4f}±{np.std(corrs_sym):.4f}")
print(f"  Diag fraction: {np.mean(diag_fracs):.4f}±{np.std(diag_fracs):.4f}")
res6 = {'P_C_corr': float(np.mean(corrs)), 'P_symC_corr': float(np.mean(corrs_sym)), 'diag_frac': float(np.mean(diag_fracs))}

# ============================================================
# EXP 7: Hessian → P (multi-sample)
# ============================================================
print("\n=== EXP 7: Hessian → P across samples ===")
r2_hess_list = []
for _ in range(30):
    C = make_random(N)
    gh, xs = compute_trajectory(C, 'tanh', T)
    P, r2 = discover_P_vectorized(xs, gh)
    hs = [C.T@np.diag(1/np.cosh(np.clip(C@x,-10,10))**2)@C for x in xs[-50:]]
    H_avg = (np.mean(hs, axis=0))
    H_avg = (H_avg+H_avg.T)/2
    a = np.trace(P)/(np.trace(H_avg)+1e-12)
    ss_r = np.sum((P.flatten()-(a*H_avg).flatten())**2)
    ss_t = np.sum((P.flatten()-P.flatten().mean())**2)
    r2_hess_list.append(1-ss_r/ss_t if ss_t>0 else 0)
print(f"  R²(Hessian_scaled → P): {np.mean(r2_hess_list):.4f}±{np.std(r2_hess_list):.4f}")

# Continuous Lyapunov at fixed point
cl_resids = []
for _ in range(20):
    C = make_random(N)
    gh, xs = compute_trajectory(C, 'tanh', T)
    P, r2 = discover_P_vectorized(xs, gh)
    J = np.diag(1-np.tanh(C@xs[-1])**2) @ C
    cl_resids.append(float(np.linalg.norm(J.T@P+P@J)/(np.linalg.norm(P)+1e-12)))
print(f"  Cont. Lyapunov resid: {np.mean(cl_resids):.4f}±{np.std(cl_resids):.4f}")

res7 = {'hess_r2': float(np.mean(r2_hess_list)), 'cont_lyap_resid': float(np.mean(cl_resids))}

# ============================================================
# EXP 8: Stochastic Lyapunov
# ============================================================
print("\n=== EXP 8: Stochastic Lyapunov ===")
sl_resids = []
for _ in range(20):
    C = make_random(N)
    gh, xs = compute_trajectory(C, 'tanh', T)
    P, r2 = discover_P_vectorized(xs, gh)
    rhs = np.zeros((N,N))
    for x in xs[-50:]:
        D = np.diag(1-np.tanh(C@x)**2)
        rhs += C.T@D@P@D@C
    rhs /= 50
    sl_resids.append(float(np.linalg.norm(rhs-P)/(np.linalg.norm(P)+1e-12)))
print(f"  ||E[C^T D P D C] - P|| / ||P|| = {np.mean(sl_resids):.4f}±{np.std(sl_resids):.4f}")
res8 = {'stoch_lyap_resid': float(np.mean(sl_resids))}

# ============================================================
# Save
# ============================================================
all_res = {'exp1': res1, 'exp2': res2, 'exp3': res3, 'exp4': res4,
           'exp5': res5, 'exp6': res6, 'exp7': res7, 'exp8': res8}
with open('results.json', 'w') as f:
    json.dump(all_res, f, indent=2, default=str)
print("\nDone!")
