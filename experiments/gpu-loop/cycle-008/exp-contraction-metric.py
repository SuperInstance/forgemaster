#!/usr/bin/env python3
"""
Experiment: Is P = M (Contraction Metric)?

Lightweight version — reduced N and samples to avoid OOM.

Hypotheses:
  H1: M = I → γ+H = x^T x = ‖x‖²?
  H2: M = C^T C → ‖Cx‖² = γ+H?
  H3: M = α·C^T C + β·I → generalized metric?
  H4: M from J^T M J = M (null space of contraction condition)
  H5: M from conservation null space (best conserved quadratic form)
"""

import numpy as np
from scipy.optimize import minimize as sp_minimize
import warnings, json, os

warnings.filterwarnings("ignore")

SEED = 42
N = 6                # small to avoid OOM
N_STEPS = 200
N_SAMPLES = 15

np.random.seed(SEED)

def evolve_tanh(C, x0, n_steps):
    N = len(x0)
    xs = np.zeros((n_steps + 1, N))
    xs[0] = x0.copy()
    for t in range(n_steps):
        xs[t+1] = np.tanh(C @ xs[t])
    return xs

def compute_jacobian(C, x):
    pre_act = C @ x
    sech2 = 1.0 / np.cosh(pre_act)**2
    return np.diag(sech2) @ C

def conservation_cv(xs, M):
    """CV of x^T M x along trajectory."""
    quad = np.array([x @ M @ x for x in xs])
    mu = np.mean(np.abs(quad))
    if mu < 1e-30:
        return 0.0
    return float(np.std(quad) / mu)

def run_experiment(C):
    N = len(C)
    x0 = np.random.randn(N) * 0.5
    xs = evolve_tanh(C, x0, N_STEPS)
    I = np.eye(N)
    CtC = C.T @ C
    
    results = {}
    
    # H1: M = I
    results["M_I"] = conservation_cv(xs, I)
    
    # H2: M = C^T C
    results["M_CtC"] = conservation_cv(xs, CtC)
    
    # H3: M = α·C^T C + β·I (optimize)
    def cv_gen(params):
        M = params[0] * CtC + params[1] * I
        return conservation_cv(xs, M)
    
    res_opt = sp_minimize(cv_gen, [1.0, 1.0], method='Nelder-Mead',
                          options={'xatol': 1e-10, 'fatol': 1e-14, 'maxiter': 5000})
    results["M_generalized"] = conservation_cv(xs, res_opt.x[0] * CtC + res_opt.x[1] * I)
    results["gen_alpha"] = float(res_opt.x[0])
    results["gen_beta"] = float(res_opt.x[1])
    
    # H4: M from J^T M J = M at fixed point
    x_fp = np.random.randn(N) * 0.1
    for _ in range(2000):
        x_new = np.tanh(C @ x_fp)
        if np.linalg.norm(x_new - x_fp) < 1e-14:
            break
        x_fp = x_new
    
    J = compute_jacobian(C, x_fp)
    J_sr = float(np.max(np.abs(np.linalg.eigvals(J))))
    
    # Null space of (J^T ⊗ J^T - I)
    JJT = np.kron(J.T, J.T)
    A_mat = JJT - np.eye(N*N)
    s = np.linalg.svd(A_mat, compute_uv=False)
    
    # Test top null space vectors
    U_svd, s_svd, Vt_svd = np.linalg.svd(A_mat)
    best_null_cv = float('inf')
    for i in range(min(5, len(s_svd))):
        vec = Vt_svd[i]
        M_cand = vec.reshape(N, N)
        M_cand = (M_cand + M_cand.T) / 2
        cv = conservation_cv(xs, M_cand)
        if cv < best_null_cv:
            best_null_cv = cv
    
    results["M_nullspace"] = best_null_cv
    results["jacobian_sr_fp"] = J_sr
    results["null_singular_vals"] = s_svd[:3].tolist()
    
    # H5: Best conserved quadratic form (conservation null space)
    n_params = N * (N + 1) // 2
    idx_map = {}
    k = 0
    for i in range(N):
        for j in range(i, N):
            idx_map[(i, j)] = k
            k += 1
    
    def sym_to_params(S):
        params = np.zeros(n_params)
        for i in range(N):
            for j in range(i, N):
                params[idx_map[(i, j)]] = S[i, j]
        return params
    
    cons_matrix = np.zeros((N_STEPS, n_params))
    for t in range(N_STEPS):
        diff = np.outer(xs[t+1], xs[t+1]) - np.outer(xs[t], xs[t])
        diff = (diff + diff.T) / 2
        cons_matrix[t] = sym_to_params(diff)
    
    U_c, s_c, Vt_c = np.linalg.svd(cons_matrix, full_matrices=True)
    
    best_cons_cv = float('inf')
    best_cons_M = None
    tol = 1e-8 * max(s_c[0] if len(s_c) > 0 else 1, 1)
    null_dim = int(np.sum(s_c < tol))
    
    for i in range(n_params):
        if i >= len(s_c):
            params = Vt_c[i]
        elif s_c[i] < tol:
            params = Vt_c[i]
        else:
            continue
        
        M_cand = np.zeros((N, N))
        for ii in range(N):
            for jj in range(ii, N):
                M_cand[ii, jj] = params[idx_map[(ii, jj)]]
                M_cand[jj, ii] = params[idx_map[(ii, jj)]]
        
        cv = conservation_cv(xs, M_cand)
        if cv < best_cons_cv:
            best_cons_cv = cv
            best_cons_M = M_cand
    
    results["M_conservation_nullspace"] = best_cons_cv
    results["cons_null_dim"] = null_dim
    
    # Analyze structure of best_cons_M
    if best_cons_M is not None:
        P_flat = best_cons_M.flatten()
        CtC_flat = CtC.flatten()
        I_flat = I.flatten()
        
        corr_CtC = float(np.corrcoef(P_flat, CtC_flat)[0, 1]) if np.std(P_flat) > 1e-20 else 0.0
        corr_I = float(np.corrcoef(P_flat, I_flat)[0, 1]) if np.std(P_flat) > 1e-20 else 0.0
        
        comm = best_cons_M @ C - C @ best_cons_M
        comm_norm = float(np.linalg.norm(comm) / (np.linalg.norm(best_cons_M) * np.linalg.norm(C) + 1e-30))
        
        # Is P a polynomial in C?
        basis = np.column_stack([m.flatten() for m in [I, C, C.T, CtC, C @ C.T]])
        res_poly = np.linalg.lstsq(basis, P_flat, rcond=None)
        poly_res = float(np.linalg.norm(P_flat - basis @ res_poly[0]) / (np.linalg.norm(P_flat) + 1e-30))
        
        results["P_corr_CtC"] = corr_CtC
        results["P_corr_I"] = corr_I
        results["P_comm_C"] = comm_norm
        results["P_poly_residual"] = poly_res
    
    # Jacobian spectral radius along trajectory
    jr_along = [float(np.max(np.abs(np.linalg.eigvals(compute_jacobian(C, xs[t]))))) for t in range(0, N_STEPS, 10)]
    results["mean_traj_jacobian_sr"] = float(np.mean(jr_along))
    results["max_traj_jacobian_sr"] = float(np.max(jr_along))
    
    return results

def generate_C(N, mtype, scale=1.0):
    if mtype == "random":
        return np.random.randn(N, N) / np.sqrt(N)
    elif mtype == "random_scaled":
        return scale * np.random.randn(N, N) / np.sqrt(N)
    elif mtype == "hebbian":
        patterns = np.random.randn(N, 3)
        C = patterns @ patterns.T / N
        np.fill_diagonal(C, 0)
        return C
    elif mtype == "attention":
        Q = np.random.randn(N, N//2 + 1) / np.sqrt(N//2 + 1)
        K = np.random.randn(N, N//2 + 1) / np.sqrt(N//2 + 1)
        scores = Q @ K.T / np.sqrt(N//2 + 1)
        exp_s = np.exp(scores - scores.max(axis=1, keepdims=True))
        return exp_s / exp_s.sum(axis=1, keepdims=True)
    elif mtype == "symmetric":
        A = np.random.randn(N, N) / np.sqrt(N)
        return (A + A.T) / 2
    return np.random.randn(N, N) / np.sqrt(N)

def main():
    print("=" * 70)
    print("CONTRACTION METRIC EXPERIMENT (Cycle 8)")
    print("Testing: Is P = M (contraction metric)?")
    print("=" * 70)
    
    all_results = {}
    
    # ─── Exp 1: Architecture sweep ─────────────────────────────────────
    print("\n--- Exp 1: Metric CV by Architecture ---")
    
    for mtype in ["random", "hebbian", "attention", "symmetric"]:
        cvs = {k: [] for k in ["M_I", "M_CtC", "M_generalized", "M_nullspace", "M_conservation_nullspace"]}
        corr_CtC_list = []
        corr_I_list = []
        comm_list = []
        poly_res_list = []
        
        for trial in range(N_SAMPLES):
            C = generate_C(N, mtype, scale=1.5)
            r = run_experiment(C)
            for k in cvs:
                cvs[k].append(r[k])
            corr_CtC_list.append(r.get("P_corr_CtC", 0))
            corr_I_list.append(r.get("P_corr_I", 0))
            comm_list.append(r.get("P_comm_C", 0))
            poly_res_list.append(r.get("P_poly_residual", 1))
        
        print(f"\n  {mtype}:")
        for k, v in cvs.items():
            print(f"    {k:35s}: CV = {np.mean(v):.8f} ± {np.std(v):.8f}")
        print(f"    P structure: corr(C^TC)={np.mean(corr_CtC_list):.4f}, "
              f"corr(I)={np.mean(corr_I_list):.4f}, "
              f"|[P,C]|={np.mean(comm_list):.4f}, "
              f"poly_res={np.mean(poly_res_list):.4f}")
        
        all_results[mtype] = {
            "metric_cvs": {k: {"mean": float(np.mean(v)), "std": float(np.std(v))} for k, v in cvs.items()},
            "P_structure": {
                "corr_CtC": float(np.mean(corr_CtC_list)),
                "corr_I": float(np.mean(corr_I_list)),
                "comm_norm": float(np.mean(comm_list)),
                "poly_residual": float(np.mean(poly_res_list)),
            }
        }
    
    # ─── Exp 2: Scale dependence ───────────────────────────────────────
    print("\n--- Exp 2: Scale Dependence ---")
    
    scale_results = {}
    for scale in [0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]:
        cvs_I = []
        cvs_CtC = []
        cvs_gen = []
        cvs_cons = []
        jr_list = []
        
        for trial in range(N_SAMPLES):
            C = generate_C(N, "random", scale=scale)
            r = run_experiment(C)
            cvs_I.append(r["M_I"])
            cvs_CtC.append(r["M_CtC"])
            cvs_gen.append(r["M_generalized"])
            cvs_cons.append(r["M_conservation_nullspace"])
            jr_list.append(r["jacobian_sr_fp"])
        
        scale_results[scale] = {
            "M_I": float(np.mean(cvs_I)),
            "M_CtC": float(np.mean(cvs_CtC)),
            "M_gen": float(np.mean(cvs_gen)),
            "M_cons": float(np.mean(cvs_cons)),
            "jacobian_sr_fp": float(np.mean(jr_list)),
        }
        
        print(f"  scale={scale:.1f}: JR={np.mean(jr_list):.4f}, "
              f"CV(I)={np.mean(cvs_I):.6f}, CV(CtC)={np.mean(cvs_CtC):.6f}, "
              f"CV(gen)={np.mean(cvs_gen):.6f}, CV(cons)={np.mean(cvs_cons):.6f}")
    
    all_results["scale_dependence"] = scale_results
    
    # ─── Exp 3: Correlation between contraction rate and conservation ────
    print("\n--- Exp 3: Contraction Rate vs Conservation Quality ---")
    
    scales = list(scale_results.keys())
    jr_means = [scale_results[s]["jacobian_sr_fp"] for s in scales]
    cv_I_means = [scale_results[s]["M_I"] for s in scales]
    cv_cons_means = [scale_results[s]["M_cons"] for s in scales]
    
    corr_jr_cvI = float(np.corrcoef(jr_means, cv_I_means)[0, 1]) if len(scales) > 2 else 0
    corr_jr_cons = float(np.corrcoef(jr_means, cv_cons_means)[0, 1]) if len(scales) > 2 else 0
    
    print(f"  corr(jacobian_sr, CV(‖x‖²)) = {corr_jr_cvI:.4f}")
    print(f"  corr(jacobian_sr, CV(best_conserved)) = {corr_jr_cons:.4f}")
    
    all_results["contraction_conservation_corr"] = {
        "jr_vs_cvI": corr_jr_cvI,
        "jr_vs_cv_cons": corr_jr_cons,
    }
    
    # ─── Verdict ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    
    # Best metric across all architectures
    best_metric = None
    best_cv = float('inf')
    for mtype, data in all_results.items():
        if mtype == "scale_dependence" or mtype == "contraction_conservation_corr":
            continue
        for metric, vals in data["metric_cvs"].items():
            if vals["mean"] < best_cv:
                best_cv = vals["mean"]
                best_metric = f"{metric} ({mtype})"
    
    print(f"\nBest metric: {best_metric} (CV = {best_cv:.8f})")
    
    # Is the conservation null space metric always better than the fixed candidates?
    print("\nConservation null space vs fixed metrics (lower = better):")
    for mtype in ["random", "hebbian", "attention", "symmetric"]:
        d = all_results[mtype]["metric_cvs"]
        print(f"  {mtype:12s}: I={d['M_I']['mean']:.6f}, CtC={d['M_CtC']['mean']:.6f}, "
              f"gen={d['M_generalized']['mean']:.6f}, null={d['M_nullspace']['mean']:.6f}, "
              f"cons={d['M_conservation_nullspace']['mean']:.6f}")
    
    # P structure summary
    print("\nP matrix structure (correlation with C^T C):")
    for mtype in ["random", "hebbian", "attention", "symmetric"]:
        c = all_results[mtype]["P_structure"]["corr_CtC"]
        p = all_results[mtype]["P_structure"]["poly_residual"]
        print(f"  {mtype:12s}: corr(P, C^TC) = {c:.4f}, poly_residual = {p:.4f}")
    
    # Scale dependence verdict
    print("\nScale dependence (contraction rate → conservation):")
    for s, d in sorted(scale_results.items()):
        contracting = "YES" if d["jacobian_sr_fp"] < 1.0 else "NO"
        print(f"  s={s:.1f}: JR={d['jacobian_sr_fp']:.4f} (contracting={contracting}), "
              f"CV(I)={d['M_I']:.6f}, CV(cons)={d['M_cons']:.6f}")
    
    # Key question: does the contraction metric equal P?
    print("\n" + "=" * 70)
    print("KEY FINDINGS")
    print("=" * 70)
    
    # Check if cons_null_dim > 0 (there exist non-trivial conserved quadratic forms)
    cons_dims = []
    for trial in range(10):
        C = generate_C(N, "random", 1.5)
        r = run_experiment(C)
        cons_dims.append(r["cons_null_dim"])
    
    print(f"\nConservation null space dimension: {np.mean(cons_dims):.1f} (out of {N*(N+1)//2} params)")
    print(f"  This means: {np.mean(cons_dims):.1f} linearly independent quadratic forms are conserved")
    
    if np.mean(cons_dims) > 0:
        print("  ✓ Non-trivial conserved quadratic forms EXIST")
        print("  → The system has genuine quadratic invariants")
    else:
        print("  ✗ No non-trivial conserved quadratic forms")
    
    # Check if M = α·C^T C + β·I explains the conservation
    print("\nIs the best conserved quadratic form α·C^T C + β·I?")
    for mtype in ["random", "hebbian", "attention", "symmetric"]:
        d = all_results[mtype]["metric_cvs"]
        ratio = d["M_generalized"]["mean"] / (d["M_conservation_nullspace"]["mean"] + 1e-30)
        if ratio < 1.5:
            verdict = "YES (α·C^TC + β·I captures the conservation)"
        elif ratio < 5:
            verdict = "PARTIAL (α·C^TC + β·I is decent but not optimal)"
        else:
            verdict = "NO (conservation requires more than C^TC structure)"
        print(f"  {mtype:12s}: ratio={ratio:.2f}x → {verdict}")
    
    # Save
    output_dir = "/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-008"
    with open(os.path.join(output_dir, "contraction_metric_results.json"), "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\nResults saved to {output_dir}/contraction_metric_results.json")
    return all_results

if __name__ == "__main__":
    main()
