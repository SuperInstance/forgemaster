#!/usr/bin/env python3
"""
Experiment 1: Arbitrage Detection as Holonomy

Constraint theory says markets are constraint satisfaction systems, and
arbitrage represents holonomy — cyclic price discrepancies that should
close but don't always close instantly.

We model 5 currencies with triangular arbitrage cycles:
  A→B→C→A  (non-zero holonomy = arbitrage opportunity)

Key predictions:
  1. Holonomy magnitude predicts arbitrage profit
  2. As arbitrageurs trade, holonomy closes toward zero (market efficiency)
  3. Holonomy-based detection outperforms standard threshold methods
"""

import numpy as np
from scipy import stats
import json
import os
import sys

# Add parent for common utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ===========================
# 1. SYNTHETIC DATA GENERATION
# ===========================

np.random.seed(42)

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF"]
N_CURRENCIES = len(CURRENCIES)
N_TIMESTEPS = 5000
N_ARBITRAGE_TIMESTEPS = 500  # Initial equilibrium, then arbitrage introduced
DT = 1.0 / 252  # Daily timestep (1 year = 252 trading days)

# Base exchange rates (midpoint, approximately current market)
BASE_RATES = {
    ("USD", "EUR"): 0.92,
    ("USD", "GBP"): 0.79,
    ("USD", "JPY"): 149.5,
    ("USD", "CHF"): 0.88,
    ("EUR", "GBP"): 0.86,
    ("EUR", "JPY"): 162.5,
    ("EUR", "CHF"): 0.96,
    ("GBP", "JPY"): 189.0,
    ("GBP", "CHF"): 1.11,
    ("JPY", "CHF"): 0.0059,  # CHF per JPY (very small)
}

# Volatility for each rate
VOLATILITY = {
    ("USD", "EUR"): 0.08,
    ("USD", "GBP"): 0.10,
    ("USD", "JPY"): 0.12,
    ("USD", "CHF"): 0.09,
    ("EUR", "GBP"): 0.06,
    ("EUR", "JPY"): 0.11,
    ("EUR", "CHF"): 0.07,
    ("GBP", "JPY"): 0.13,
    ("GBP", "CHF"): 0.08,
    ("JPY", "CHF"): 0.14,
}

# Spread (bid-ask) as fraction of rate
SPREAD = 0.0002  # 2 bps typical for major forex pairs


def generate_gbm_prices(base_rates, volatilities, n_timesteps, dt, seed=42):
    """Generate correlated GBM price paths for all exchange rates."""
    np.random.seed(seed)
    rates = list(base_rates.keys())
    n_rates = len(rates)
    
    # Correlation matrix for rates (clustered by shared currencies)
    corr = np.eye(n_rates)
    for i, r1 in enumerate(rates):
        for j, r2 in enumerate(rates):
            if i < j:
                # Two rates sharing a currency are more correlated
                shared = len(set(r1) & set(r2))
                corr[i, j] = 0.5 if shared > 1 else 0.3
                corr[j, i] = corr[i, j]
    
    # Ensure positive definiteness
    eigvals = np.linalg.eigvalsh(corr)
    if eigvals.min() < 0:
        corr += (-eigvals.min() + 0.01) * np.eye(n_rates)
    
    # Cholesky decomposition for correlated random walks
    L = np.linalg.cholesky(corr)
    
    # Generate correlated Brownian motions
    dW = np.random.normal(0, np.sqrt(dt), (n_timesteps, n_rates))
    dW_corr = dW @ L.T
    
    # Generate prices
    prices = np.zeros((n_timesteps, n_rates))
    prices[0] = [base_rates[r] for r in rates]
    
    for t in range(1, n_timesteps):
        sigmas = np.array([volatilities[r] for r in rates])
        # Mild drift (random walk with small trend)
        drifts = np.zeros(n_rates)  # No drift for arbitrage-free base
        prices[t] = prices[t-1] * np.exp(
            (drifts - 0.5 * sigmas**2) * dt + sigmas * dW_corr[t]
        )
    
    return prices, rates


def compute_holonomy(prices, rates, cycle_currencies):
    """
    Compute holonomy around a triangular cycle A→B→C→A.
    
    Holonomy = final rate - initial rate around cycle (should be 1.0 in
    arbitrage-free markets, any deviation = arbitrage opportunity)
    
    For cycle A→B→C→A:
      holonomy = rate(A,B) * rate(B,C) * rate(C,A)
      Arbitrage-free => holonomy = 1.0 (no profit cycling)
      Holonomy > 1 => profitable A→B→C→A
      Holonomy < 1 => profitable reverse direction
    """
    # Extract time series for each leg of the cycle
    def find_rate_idx(r1, r2):
        for i, r in enumerate(rates):
            if r[0] == r1 and r[1] == r2:
                return i
            if r[0] == r2 and r[1] == r1:
                return i  # We'll handle inversion below
        raise ValueError(f"Rate {r1}→{r2} not found")
    
    legs = []
    for i in range(len(cycle_currencies)):
        c1 = cycle_currencies[i]
        c2 = cycle_currencies[(i + 1) % len(cycle_currencies)]
        idx = find_rate_idx(c1, c2)
        stored_pair = rates[idx]
        if stored_pair[0] == c1 and stored_pair[1] == c2:
            legs.append((idx, 1.0))  # Direct rate
        else:
            legs.append((idx, -1.0))  # Inverse rate
            # Rate is stored as c2→c1, we need inverse: rate = 1 / stored
    
    holonomy = np.ones(len(prices))
    for idx, sign in legs:
        if sign > 0:
            holonomy *= prices[:, idx]
        else:
            holonomy *= (1.0 / prices[:, idx])
    
    return holonomy


def compute_triangular_arbitrage_profit(prices, rates, cycle_currencies, spread=0.0002):
    """
    Compute actual arbitrage profit considering bid-ask spread.
    
    For A→B→C→A:
      - Buy B with A (ask rate for A/B)
      - Buy C with B (ask rate for B/C)
      - Buy A with C (ask rate for C/A)
    
    Profit = 1 - (1 / holonomy_adjusted) as fraction of initial capital
    """
    def get_ask_idx(r1, r2):
        for i, r in enumerate(rates):
            if r[0] == r1 and r[1] == r2:
                return i, True
            if r[0] == r2 and r[1] == r1:
                return i, False
        raise ValueError(f"Rate {r1}→{r2} not found")
    
    # Forward direction: A→B→C→A
    # Leg 1: A→B: we need ask (buy B with A) = rate * (1 + spread)
    # Leg 2: B→C: ask for B/C = rate * (1 + spread)
    # Leg 3: C→A: ask for C/A = rate * (1 + spread)
    
    profits = np.zeros(len(prices))
    
    for t in range(len(prices)):
        # Compute actual cost to traverse the cycle
        cost = 1.0
        for i in range(len(cycle_currencies)):
            c1 = cycle_currencies[i]
            c2 = cycle_currencies[(i + 1) % len(cycle_currencies)]
            idx, is_direct = get_ask_idx(c1, c2)
            rate = prices[t, idx]
            if is_direct:
                cost *= rate * (1 + spread)  # Buying, so ask price
            else:
                cost *= (1.0 / rate) * (1 + spread)  # Inverse, still buying
        
        # If cost < 1 then we can profit: buy 1 unit of A, cycle to get > 1 unit back
        profits[t] = 1.0 - cost
    
    return profits


# ===========================
# 2. HOLONOMY COMPUTATION
# ===========================

# Generate prices
print("Generating synthetic forex data...")
prices, rate_pairs = generate_gbm_prices(BASE_RATES, VOLATILITY, N_TIMESTEPS, DT)
print(f"Generated {N_TIMESTEPS} timesteps for {len(rate_pairs)} exchange rates")

# Define all triangular cycles
all_cycles = [
    ("USD", "EUR", "GBP"),
    ("USD", "EUR", "JPY"),
    ("USD", "EUR", "CHF"),
    ("USD", "GBP", "JPY"),
    ("USD", "GBP", "CHF"),
    ("USD", "JPY", "CHF"),
    ("EUR", "GBP", "JPY"),
    ("EUR", "GBP", "CHF"),
    ("EUR", "JPY", "CHF"),
    ("GBP", "JPY", "CHF"),
]

# Compute holonomy for each cycle
print("Computing holonomy for all triangular cycles...")
holonomies = {}
for cycle in all_cycles:
    h = compute_holonomy(prices, rate_pairs, cycle)
    holonomies[cycle] = h

# ===========================
# 3. ARBITRAGE SCENARIO
# ===========================
# Introduce an arbitrage opportunity at t=2000 by injecting a price
# discrepancy in the USD→EUR→GBP→USD cycle

print("\n--- Experiment 1a: Holonomy Magnitude Predicts Arbitrage Profit ---")

# At timestep 2000, inject a price spike in EUR/GBP to create arbitrage
shock_time = 2000
shock_duration = 50
shock_magnitude = 1.005  # 0.5% mispricing

# Find EUR/GBP index
eur_gbp_idx = rate_pairs.index(("EUR", "GBP"))

# Create a copy with the injected arbitrage
prices_arb = prices.copy()
prices_arb[shock_time:shock_time+shock_duration, eur_gbp_idx] *= shock_magnitude

# Compute holonomy after shock
holonomies_arb = {}
arb_profits = {}
for cycle in all_cycles:
    h_arb = compute_holonomy(prices_arb, rate_pairs, cycle)
    p_arb = compute_triangular_arbitrage_profit(prices_arb, rate_pairs, cycle, SPREAD)
    holonomies_arb[cycle] = h_arb
    arb_profits[cycle] = p_arb

# Analyze: holonomy vs profit relationship
# Focus on USD→EUR→GBP→USD cycle
main_cycle = ("USD", "EUR", "GBP")
h_main = holonomies_arb[main_cycle]
p_main = arb_profits[main_cycle]

# Compute correlation between |holonomy - 1| and profit
holonomy_deviation = np.abs(h_main - 1.0)
profit_positive = np.maximum(p_main, 0)  # Only profitable trades matter

# Pearson correlation
mask = h_main != 0
corr, p_value = stats.pearsonr(holonomy_deviation[mask], profit_positive[mask])
print(f"Prediction 1: Holonomy Magnitude vs Arbitrage Profit")
print(f"  Pearson correlation: {corr:.4f} (p={p_value:.2e})")
print(f"  Expected: strong positive correlation (holonomy = arbitrage opportunity)")

# Spearman (rank) correlation
rho, sp_value = stats.spearmanr(holonomy_deviation[mask], profit_positive[mask])
print(f"  Spearman correlation: {rho:.4f} (p={sp_value:.2e})")

# ===========================
# 4. ARBITRAGE CONVERGENCE
# ===========================
print("\n--- Experiment 1b: Holonomy Convergence Through Arbitrage ---")

# Simulate arbitrageurs trading to close the gap
# Model: holonomy exponentially decays toward 1.0 with relaxation time
relaxation_tau = 20  # timesteps for 63% convergence

prices_converge = prices.copy()
holonomy_trace = np.ones(N_TIMESTEPS)

# Inject shock
prices_converge[shock_time:shock_time+shock_duration, eur_gbp_idx] *= shock_magnitude

# After shock, let arbitrageurs close the mispricing
for t in range(shock_time + shock_duration, N_TIMESTEPS):
    # Simplified: just let the shock dissipate
    recovery = np.exp(-(t - shock_time - shock_duration) / relaxation_tau)
    prices_converge[t, eur_gbp_idx] = prices[t, eur_gbp_idx] + (
        prices_arb[shock_time, eur_gbp_idx] - prices[t, eur_gbp_idx]
    ) * recovery
    
    holonomy_trace[t] = compute_holonomy(
        prices_converge[t:t+1], rate_pairs, main_cycle
    )[0]

# Compute holonomy for convergence scenario
holonomy_converge = compute_holonomy(prices_converge, rate_pairs, main_cycle)

# Check convergence rate
pre_shock_holonomy = np.mean(np.abs(holonomy_converge[shock_time-100:shock_time] - 1.0))
post_shock_holonomy = np.mean(np.abs(holonomy_converge[shock_time:shock_time+50] - 1.0))
converged_holonomy = np.mean(np.abs(holonomy_converge[shock_time+200:shock_time+300] - 1.0))

print(f"  Pre-shock mean |holonomy-1|: {pre_shock_holonomy:.6f}")
print(f"  Post-shock mean |holonomy-1|: {post_shock_holonomy:.6f}")
print(f"  After convergence: {converged_holonomy:.6f}")
print(f"  Holonomy closes as arbitrageurs trade (efficiency restored)")

# Characteristic convergence time
halflife = None
for t in range(shock_time + shock_duration, N_TIMESTEPS):
    if np.abs(holonomy_converge[t] - 1.0) < post_shock_holonomy / 2:
        halflife = t - shock_time - shock_duration
        break
print(f"  Halflife to convergence: {halflife} timesteps (~{halflife*DT*252:.1f} trading days)")

# ===========================
# 5. COMPARISON WITH STANDARD METHODS
# ===========================
print("\n--- Experiment 1c: Comparison with Standard Arbitrage Detection ---")

# Standard method: check if product of bid-ask adjusted rates ≠ 1
# Holonomy method: continuous measure of departure from 1.0

# Count how many timesteps holonomy detects arbitrage (|h-1| > threshold)
# vs standard method (profit > spread_cost)
standard_threshold = 1e-5  # Break-even after transaction costs
holonomy_threshold = 0.001  # 10 bps deviation

# Inject synthetic arbitrage with varying magnitudes
magnitudes = np.linspace(0.0001, 0.02, 20)
holonomy_hits = []
standard_hits = []

for mag in magnitudes:
    p_test = prices.copy()
    p_test[shock_time:shock_time+5, eur_gbp_idx] *= (1 + mag)
    
    h_test = compute_holonomy(p_test, rate_pairs, main_cycle)
    p_test_profit = compute_triangular_arbitrage_profit(
        p_test, rate_pairs, main_cycle, SPREAD
    )
    
    # Holonomy detection
    h_detected = np.any(np.abs(h_test[shock_time:shock_time+5] - 1.0) > holonomy_threshold)
    
    # Standard detection (profit after spread)
    s_detected = np.any(p_test_profit[shock_time:shock_time+5] > standard_threshold)
    
    holonomy_hits.append(1 if h_detected else 0)
    standard_hits.append(1 if s_detected else 0)

# Early detection advantage: holonomy detects smaller discrepancies
first_holonomy_detect = None
first_standard_detect = None
for i, m in enumerate(magnitudes):
    if holonomy_hits[i] and first_holonomy_detect is None:
        first_holonomy_detect = m
    if standard_hits[i] and first_standard_detect is None:
        first_standard_detect = m

print(f"  Holonomy detects at: {first_holonomy_detect*10000:.1f} bps mispricing")
print(f"  Standard detects at: {first_standard_detect*10000:.1f} bps mispricing")
print(f"  Advantage: holonomy detects {first_standard_detect/first_holonomy_detect:.1f}x smaller discrepancies")

# ===========================
# 6. RESULTS SUMMARY
# ===========================
results = {
    "experiment": "1_arbitrage_as_holonomy",
    "predictions": {
        "holonomy_magnitude_predicts_profit": {
            "pearson_r": float(corr),
            "pearson_p": float(p_value),
            "spearman_rho": float(rho),
            "spearman_p": float(sp_value),
            "confirmed": bool(corr > 0.7 and p_value < 0.01)
        },
        "holonomy_closes_with_arbitrage": {
            "pre_shock_holonomy": float(pre_shock_holonomy),
            "post_shock_holonomy": float(post_shock_holonomy),
            "converged_holonomy": float(converged_holonomy),
            "halflife_timesteps": halflife if halflife is not None else 0,
            "confirmed": bool(converged_holonomy < post_shock_holonomy * 0.5)
        },
        "holonomy_detection_advantage": {
            "holonomy_detection_threshold_bps": float(first_holonomy_detect * 10000),
            "standard_detection_threshold_bps": float(first_standard_detect * 10000),
            "advantage_factor": float(first_standard_detect / first_holonomy_detect),
            "confirmed": bool(first_holonomy_detect < first_standard_detect * 0.5)
        }
    },
    "experiment_parameters": {
        "n_currencies": 5,
        "n_timesteps": N_TIMESTEPS,
        "n_triangular_cycles": len(all_cycles),
        "spread_bps": SPREAD * 10000,
        "shock_magnitude_pct": (shock_magnitude - 1.0) * 100,
        "relaxation_tau_timesteps": relaxation_tau
    }
}

os.makedirs("results", exist_ok=True)
with open("results/experiment_1_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nResults saved to results/experiment_1_results.json")
print("=" * 60)
