"""
VR Seat Reservation Pooling Simulation — Scenario D
=====================================================

Only Y% of seat capacity per leg may be committed to immediate customer
seat choice. All other passengers are pooled and seated optimally at departure.

Reuses the same demand generation, booking curves, and random seeds as the
earlier decomposed simulation so results are directly comparable.

Expects:
  - VR Excel data file (booking curves, trains)
  - fragmentation_decomposed.csv (A/B/C results from earlier run)
"""

from __future__ import annotations

import os
import math
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import linprog

# ============================================================
# GLOBAL SETTINGS
# ============================================================
STATIONS = ["A", "B", "C", "D", "E", "F", "G"]
NUM_LEGS = len(STATIONS) - 1

TOTAL_SEATS = 200
WINDOW_SEATS = 100  # seats 0-99 = window, 100-199 = aisle

SEED = 42
NUM_SIMS = 200

OD_VOLUMES = {
    (0,1):1000, (0,2):900, (0,3):800, (0,4):700, (0,5):600, (0,6):500,
    (1,2):900,  (1,3):800, (1,4):700, (1,5):600, (1,6):500,
    (2,3):800,  (2,4):700, (2,5):600, (2,6):500,
    (3,4):700,  (3,5):600, (3,6):500,
    (4,5):600,  (4,6):500,
    (5,6):500,
}

REFERENCE_LEG_LOADS = np.zeros(NUM_LEGS, dtype=float)
for (o, d), v in OD_VOLUMES.items():
    REFERENCE_LEG_LOADS[o:d] += v
REFERENCE_PEAK = REFERENCE_LEG_LOADS.max()


# ============================================================
# HELPERS
# ============================================================
def interval_to_mask(o: int, d: int) -> int:
    mask = 0
    for leg in range(o, d):
        mask |= (1 << leg)
    return mask


def popcount(x: int) -> int:
    return int(bin(x).count("1"))


# ============================================================
# BOOKING CURVES — same logic as your existing code
# ============================================================
def load_booking_pmfs(xlsx_path: str) -> dict[tuple[int,int], tuple[np.ndarray, np.ndarray]]:
    df = pd.read_excel(xlsx_path, sheet_name="Booking_curves")
    pmfs = {}

    for leg, g in df.groupby("Journey_leg"):
        g = g.sort_values("Days_before_departure")
        days = g["Days_before_departure"].to_numpy(dtype=int)
        cum = g["Cumulative_reservations_percentage"].to_numpy(dtype=float)

        masses = np.zeros_like(cum, dtype=float)
        if len(cum) > 1:
            masses[0] = 1.0 - cum[1]
            for i in range(1, len(cum) - 1):
                masses[i] = cum[i] - cum[i + 1]
            masses[-1] = cum[-1]
        else:
            masses[0] = 1.0

        masses = np.clip(masses, 0, None)
        if masses.sum() == 0:
            raise ValueError(f"Booking curve for {leg} produced zero mass.")
        masses = masses / masses.sum()

        a, b = leg.split("-")
        pmfs[(STATIONS.index(a), STATIONS.index(b))] = (days, masses)

    by_length = {}
    for (o, d), (_, probs) in pmfs.items():
        by_length.setdefault(d - o, []).append(probs)
    avg_by_length = {L: np.mean(np.vstack(v), axis=0) for L, v in by_length.items()}

    all_days = np.arange(0, 91)
    for o in range(NUM_LEGS):
        for d in range(o + 1, len(STATIONS)):
            if (o, d) not in pmfs:
                pmfs[(o, d)] = (all_days, avg_by_length[d - o])

    return pmfs


# ============================================================
# DEMAND GENERATION — same logic as your existing code
# ============================================================
def generate_requests(
    target_peak_load: float,
    booking_pmfs: dict[tuple[int,int], tuple[np.ndarray, np.ndarray]],
    rng: np.random.Generator,
    poisson_counts: bool = True,
) -> pd.DataFrame:
    scale = (TOTAL_SEATS * target_peak_load) / REFERENCE_PEAK

    rows = []
    for (o, d), base_vol in OD_VOLUMES.items():
        mean_n = base_vol * scale
        n = rng.poisson(mean_n) if poisson_counts else int(round(mean_n))

        days, probs = booking_pmfs[(o, d)]
        sampled_days = rng.choice(days, size=n, p=probs)
        frac = rng.random(n)
        booking_time = sampled_days + frac
        mask = interval_to_mask(o, d)
        nlegs = d - o

        for bt in booking_time:
            rows.append((bt, o, d, nlegs, mask))

    req = pd.DataFrame(rows, columns=["booking_time", "o", "d", "nlegs", "mask"])
    req = req.sort_values("booking_time", ascending=False).reset_index(drop=True)
    return req


# ============================================================
# LP SOLVER — reused for both full LP and pool LP
# ============================================================
def solve_lp_max_pax_km(nlegs_arr, o_arr, d_arr, capacity_per_leg):
    """
    Maximize sum(x_i * nlegs_i) subject to leg capacity constraints.
    Returns boolean array of accepted passengers.
    """
    n = len(nlegs_arr)
    if n == 0:
        return np.array([], dtype=bool), 0.0

    A = np.zeros((NUM_LEGS, n), dtype=float)
    for i in range(n):
        A[o_arr[i]:d_arr[i], i] = 1.0

    b = np.array(capacity_per_leg, dtype=float)
    c = -np.array(nlegs_arr, dtype=float)

    res = linprog(c=c, A_ub=A, b_ub=b, bounds=[(0, 1)] * n, method="highs")

    if res.status != 0:
        raise RuntimeError(f"LP failed: {res.message}")

    accepted = res.x > 0.5
    served_km = float(np.array(nlegs_arr)[accepted].sum())
    return accepted, served_km


# ============================================================
# SCENARIO D: POOLED RESERVATION
# ============================================================
def simulate_pooled_reservation(req: pd.DataFrame, y_pct: float, rng: np.random.Generator) -> dict:
    """
    Simulate the pooled reservation policy for a given Y percentage.

    Phase 1: Booking — early reservers vs pool
    Phase 2: Departure — LP + greedy fitting for pooled passengers
    """
    early_limit = round(y_pct / 100.0 * TOTAL_SEATS)

    # --- Phase 1: Booking phase ---
    seat_masks = np.zeros(TOTAL_SEATS, dtype=np.uint8)
    reserved_leg_count = np.zeros(NUM_LEGS, dtype=int)

    early_pax_km = 0
    early_count = 0

    # Pool storage: lists of (o, d, nlegs, mask)
    pool_o = []
    pool_d = []
    pool_nlegs = []
    pool_mask = []

    for row in req.itertuples(index=False):
        o = int(row.o)
        d = int(row.d)
        nlegs = int(row.nlegs)
        req_mask = int(row.mask)

        # Check eligibility: all legs under early_limit?
        eligible = True
        for leg in range(o, d):
            if reserved_leg_count[leg] >= early_limit:
                eligible = False
                break

        if eligible and early_limit > 0:
            # Find feasible seats
            free = (seat_masks & req_mask) == 0
            free_idx = np.where(free)[0]

            if len(free_idx) == 0:
                # No physical seat available despite cap not reached — send to pool
                pool_o.append(o)
                pool_d.append(d)
                pool_nlegs.append(nlegs)
                pool_mask.append(req_mask)
                continue

            # Choose seat: window preference, otherwise random
            window_free = free_idx[free_idx < WINDOW_SEATS]
            if len(window_free) > 0:
                chosen = int(window_free[rng.integers(len(window_free))])
            else:
                chosen = int(free_idx[rng.integers(len(free_idx))])

            # Lock the seat
            seat_masks[chosen] |= req_mask
            for leg in range(o, d):
                reserved_leg_count[leg] += 1

            early_pax_km += nlegs
            early_count += 1
        else:
            # Not eligible or Y=0 — goes to pool
            pool_o.append(o)
            pool_d.append(d)
            pool_nlegs.append(nlegs)
            pool_mask.append(req_mask)

    pool_count = len(pool_o)

    # --- Phase 2: Departure assignment for pooled passengers ---

    # Compute remaining capacity per leg from actual seat occupancy
    remaining_capacity = np.zeros(NUM_LEGS, dtype=float)
    for leg in range(NUM_LEGS):
        leg_bit = 1 << leg
        occupied_on_leg = np.sum((seat_masks & leg_bit) > 0)
        remaining_capacity[leg] = TOTAL_SEATS - occupied_on_leg

    # Step 2a: LP accept/reject for pooled passengers
    if pool_count > 0:
        pool_o_arr = np.array(pool_o, dtype=int)
        pool_d_arr = np.array(pool_d, dtype=int)
        pool_nlegs_arr = np.array(pool_nlegs, dtype=int)
        pool_mask_arr = np.array(pool_mask, dtype=int)

        pool_accepted, pool_accepted_km = solve_lp_max_pax_km(
            pool_nlegs_arr, pool_o_arr, pool_d_arr, remaining_capacity
        )

        pool_accepted_count = int(pool_accepted.sum())
        pool_rejected_count = pool_count - pool_accepted_count
        pool_rejected_km = float(pool_nlegs_arr[~pool_accepted].sum())
    else:
        pool_accepted = np.array([], dtype=bool)
        pool_accepted_km = 0.0
        pool_accepted_count = 0
        pool_rejected_count = 0
        pool_rejected_km = 0.0
        pool_o_arr = np.array([], dtype=int)
        pool_d_arr = np.array([], dtype=int)
        pool_nlegs_arr = np.array([], dtype=int)
        pool_mask_arr = np.array([], dtype=int)

    # Step 2b: Greedy seat fitting for accepted pooled passengers
    # Sort by journey length descending (longest first — hardest to fit)
    if pool_accepted_count > 0:
        accepted_indices = np.where(pool_accepted)[0]
        accepted_nlegs = pool_nlegs_arr[accepted_indices]
        sort_order = np.argsort(-accepted_nlegs)
        accepted_indices = accepted_indices[sort_order]

        pool_fitted_km = 0
        pool_fitted_count = 0
        fitting_failure_km = 0
        fitting_failure_count = 0

        for idx in accepted_indices:
            req_mask = int(pool_mask_arr[idx])
            o = int(pool_o_arr[idx])
            d = int(pool_d_arr[idx])
            nlegs = int(pool_nlegs_arr[idx])

            # Find feasible seats
            free = (seat_masks & req_mask) == 0
            free_idx = np.where(free)[0]

            if len(free_idx) > 0:
                # Best-fit greedy: prefer seat with most other legs occupied (maximize reuse)
                best_score = -1
                best_seat = free_idx[0]
                for s in free_idx:
                    score = popcount(seat_masks[s])
                    if score > best_score:
                        best_score = score
                        best_seat = s

                seat_masks[best_seat] |= req_mask
                pool_fitted_km += nlegs
                pool_fitted_count += 1
            else:
                # Fitting failure: LP said yes but no actual seat available
                fitting_failure_km += nlegs
                fitting_failure_count += 1
    else:
        pool_fitted_km = 0
        pool_fitted_count = 0
        fitting_failure_km = 0
        fitting_failure_count = 0

    total_served_km = early_pax_km + pool_fitted_km

    return {
        "early_pax_km": early_pax_km,
        "early_count": early_count,
        "pool_count": pool_count,
        "pool_accepted_km": pool_accepted_km,
        "pool_accepted_count": pool_accepted_count,
        "pool_fitted_km": pool_fitted_km,
        "pool_fitted_count": pool_fitted_count,
        "pool_rejected_km": pool_rejected_km,
        "pool_rejected_count": pool_rejected_count,
        "fitting_failure_km": fitting_failure_km,
        "fitting_failure_count": fitting_failure_count,
        "total_served_km": total_served_km,
    }


# ============================================================
# STATISTICS HELPER
# ============================================================
def summarize(series):
    arr = np.asarray(series, dtype=float)
    mean = arr.mean()
    std = arr.std(ddof=1) if len(arr) > 1 else 0.0
    ci95 = 1.96 * std / math.sqrt(len(arr)) if len(arr) > 1 else 0.0
    return mean, std, ci95


# ============================================================
# EXPERIMENT RUNNER
# ============================================================
def run_experiment(
    xlsx_path: str,
    demand_grid=np.arange(0.8, 2.05, 0.1),
    y_values=(0, 10, 20, 30, 40, 50),
    num_sims: int = NUM_SIMS,
    seed: int = SEED,
) -> pd.DataFrame:

    booking_pmfs = load_booking_pmfs(xlsx_path)
    master_rng = np.random.default_rng(seed)

    results = []
    total_combos = len(demand_grid) * len(y_values)
    combo_count = 0

    for dm in demand_grid:
        # Pre-generate all sim seeds for this demand level
        # so that each Y sees the exact same passengers
        sim_seeds = [int(master_rng.integers(0, 2**31 - 1)) for _ in range(num_sims)]

        for y_pct in y_values:
            combo_count += 1
            early_limit = round(y_pct / 100.0 * TOTAL_SEATS)
            print(f"  [{combo_count}/{total_combos}] dm={dm:.1f} Y={y_pct}% (cap={early_limit} seats/leg) ...",
                  end=" ", flush=True)

            metrics_lists = {
                "total_served_km": [],
                "early_pax_km": [],
                "early_count": [],
                "pool_count": [],
                "pool_accepted_km": [],
                "pool_fitted_km": [],
                "pool_rejected_km": [],
                "fitting_failure_km": [],
                "fitting_failure_count": [],
            }

            for sim_idx in range(num_sims):
                sim_seed = sim_seeds[sim_idx]
                rng_req = np.random.default_rng(sim_seed)
                rng_d = np.random.default_rng(sim_seed + 2)  # +2 to not collide with B/C seeds

                req = generate_requests(dm, booking_pmfs, rng_req, poisson_counts=True)
                res = simulate_pooled_reservation(req, y_pct, rng_d)

                for k in metrics_lists:
                    metrics_lists[k].append(res[k])

            # Summarize
            row = {"demand_multiplier": dm, "y_pct": y_pct, "early_limit": early_limit}
            for k, vals in metrics_lists.items():
                m, s, ci = summarize(vals)
                row[f"{k}_mean"] = m
                row[f"{k}_std"] = s
                row[f"{k}_ci95"] = ci

            print(f"served={row['total_served_km_mean']:.0f}  "
                  f"early={row['early_pax_km_mean']:.0f}  "
                  f"pool_fitted={row['pool_fitted_km_mean']:.0f}  "
                  f"pool_rejected={row['pool_rejected_km_mean']:.0f}  "
                  f"fit_fail={row['fitting_failure_count_mean']:.1f}")

            results.append(row)

    return pd.DataFrame(results)


# ============================================================
# PLOTTING
# ============================================================
def make_plots(
    results: pd.DataFrame,
    abc_path: str | None = None,
    xlsx_path: str | None = None,
    out_prefix: str = "pooled_reservation",
):
    # Load A/B/C reference data if available
    abc = None
    if abc_path and os.path.exists(abc_path):
        abc = pd.read_csv(abc_path)
        print(f"Loaded A/B/C reference from {abc_path}")

    # Load real train data for context
    trains = None
    if xlsx_path and os.path.exists(xlsx_path):
        trains = pd.read_excel(xlsx_path, sheet_name="Trains")
        trains["load_factor"] = trains["Max_pax"] / trains["Capacity"]

    y_values = sorted(results["y_pct"].unique())
    dm_values = sorted(results["demand_multiplier"].unique())

    fig, axes = plt.subplots(2, 3, figsize=(18, 11))
    fig.suptitle("VR Pooled Reservation Policy: How Much Early Seat Commitment Is Safe?",
                 fontsize=14, fontweight="bold")

    # ---- Chart 1: Throughput vs demand multiplier ----
    ax = axes[0, 0]
    if abc is not None:
        ax.plot(abc["demand_multiplier"], abc["lp_served_mean"], "k-o", ms=4, lw=2,
                label="A: LP optimum", zorder=10)
        ax.plot(abc["demand_multiplier"], abc["seq_opt_served_mean"], "gray", ls="--",
                ms=3, lw=1.5, label="B: Sequential baseline")

    colors_y = {0: "#2ecc71", 10: "#3498db", 20: "#9b59b6", 30: "#e67e22", 40: "#e74c3c", 50: "#95a5a6"}
    for y_pct in y_values:
        sub = results[results["y_pct"] == y_pct].sort_values("demand_multiplier")
        color = colors_y.get(y_pct, "gray")
        ax.plot(sub["demand_multiplier"], sub["total_served_km_mean"],
                marker="s", ms=3, lw=1.5, color=color, label=f"D: Y={y_pct}%")

    ax.set_xlabel("Demand multiplier")
    ax.set_ylabel("Served passenger-km")
    ax.set_title("Throughput by Policy")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)

    # ---- Chart 2: Throughput vs Y at selected demand levels ----
    ax = axes[0, 1]
    demand_highlights = [1.0, 1.4, 2.0]
    dm_colors = {1.0: "#2ecc71", 1.4: "#e67e22", 2.0: "#e74c3c"}
    for dm_target in demand_highlights:
        dm_actual = min(dm_values, key=lambda x: abs(x - dm_target))
        sub = results[results["demand_multiplier"] == dm_actual].sort_values("y_pct")
        color = dm_colors.get(dm_target, "gray")
        ax.plot(sub["y_pct"], sub["total_served_km_mean"], "-o", ms=5, lw=2,
                color=color, label=f"Demand={dm_actual:.1f}x")
        # Add LP reference as horizontal line
        if abc is not None:
            lp_row = abc[abc["demand_multiplier"].round(1) == round(dm_actual, 1)]
            if len(lp_row) > 0:
                ax.axhline(y=lp_row.iloc[0]["lp_served_mean"], color=color,
                           ls=":", alpha=0.5)

    ax.set_xlabel("Y (% of leg capacity for early reservation)")
    ax.set_ylabel("Served passenger-km")
    ax.set_title("Degradation as Early Commitment Increases")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # ---- Chart 3: Composition stacked bar at demand=1.5 ----
    ax = axes[0, 2]
    dm_target = 1.5
    dm_actual = min(dm_values, key=lambda x: abs(x - dm_target))
    sub = results[results["demand_multiplier"] == dm_actual].sort_values("y_pct")

    bar_width = 4
    ax.bar(sub["y_pct"], sub["early_pax_km_mean"], width=bar_width,
           label="Early reservers", color="#3498db", alpha=0.85)
    ax.bar(sub["y_pct"], sub["pool_fitted_km_mean"], width=bar_width,
           bottom=sub["early_pax_km_mean"],
           label="Pool: seated at departure", color="#2ecc71", alpha=0.85)
    ax.bar(sub["y_pct"], sub["pool_rejected_km_mean"], width=bar_width,
           bottom=sub["early_pax_km_mean"] + sub["pool_fitted_km_mean"],
           label="Pool: rejected (no capacity)", color="#e74c3c", alpha=0.85)
    ax.bar(sub["y_pct"], sub["fitting_failure_km_mean"], width=bar_width,
           bottom=sub["early_pax_km_mean"] + sub["pool_fitted_km_mean"] + sub["pool_rejected_km_mean"],
           label="Fitting failure", color="#e67e22", alpha=0.85)

    ax.set_xlabel("Y (% early reservation)")
    ax.set_ylabel("Passenger-km")
    ax.set_title(f"Composition at Demand={dm_actual:.1f}x")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3, axis="y")

    # ---- Chart 4: Fitting failures ----
    ax = axes[1, 0]
    for dm_target in [1.0, 1.2, 1.5, 2.0]:
        dm_actual = min(dm_values, key=lambda x: abs(x - dm_target))
        sub = results[results["demand_multiplier"] == dm_actual].sort_values("y_pct")
        ax.plot(sub["y_pct"], sub["fitting_failure_count_mean"], "-o", ms=4, lw=1.5,
                label=f"Demand={dm_actual:.1f}x")

    ax.set_xlabel("Y (% early reservation)")
    ax.set_ylabel("Fitting failures (count)")
    ax.set_title("LP Accepted but No Seat Found")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # ---- Chart 5: % of LP optimum recovered ----
    ax = axes[1, 1]
    if abc is not None:
        for y_pct in y_values:
            sub_d = results[results["y_pct"] == y_pct].sort_values("demand_multiplier")
            merged = pd.merge(
                sub_d[["demand_multiplier", "total_served_km_mean"]],
                abc[["demand_multiplier", "lp_served_mean"]],
                on="demand_multiplier", how="inner",
            )
            if len(merged) > 0:
                pct_of_lp = 100 * merged["total_served_km_mean"] / merged["lp_served_mean"]
                color = colors_y.get(y_pct, "gray")
                ax.plot(merged["demand_multiplier"], pct_of_lp, "-o", ms=3, lw=1.5,
                        color=color, label=f"Y={y_pct}%")

        # Also plot sequential baseline as reference
        seq_pct = 100 * abc["seq_opt_served_mean"] / abc["lp_served_mean"]
        ax.plot(abc["demand_multiplier"], seq_pct, "gray", ls="--", lw=1.5,
                label="Sequential baseline")

    ax.set_xlabel("Demand multiplier")
    ax.set_ylabel("% of LP optimum achieved")
    ax.set_title("Efficiency: How Close to Theoretical Max?")
    ax.legend(fontsize=7, ncol=2)
    ax.set_ylim(85, 101)
    ax.grid(alpha=0.3)

    # ---- Chart 6: Real VR fleet context ----
    ax = axes[1, 2]
    if trains is not None:
        ax.hist(trains["load_factor"] * 100, bins=30, alpha=0.75,
                color="steelblue", edgecolor="white")
        ax.axvline(100, color="red", ls="--", lw=1.5, label="100% capacity")
        ax.axvline(trains["load_factor"].mean() * 100, color="orange",
                   ls="--", lw=1.5, label=f"Mean: {trains['load_factor'].mean():.0%}")
        n90 = (trains["load_factor"] > 0.90).sum()
        ax.text(0.95, 0.95,
                f"{n90} trains above 90% load\n({n90/len(trains):.1%} of fleet)",
                transform=ax.transAxes, ha="right", va="top", fontsize=9,
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))
        ax.set_xlabel("Load factor (%)")
        ax.set_ylabel("Number of trains")
        ax.set_title(f"Real VR Fleet: {len(trains)} Services")
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
    else:
        ax.axis("off")

    plt.tight_layout()
    out_file = f"{out_prefix}_results.png"
    plt.savefig(out_file, dpi=160, bbox_inches="tight")
    print(f"\nSaved plot: {out_file}")


# ============================================================
# MAIN
# ============================================================
def main(xlsx_path: str, abc_csv_path: str | None = None):
    t0 = time.time()

    print("=" * 65)
    print("VR POOLED RESERVATION SIMULATION — SCENARIO D")
    print("=" * 65)
    print(f"Y = % of leg capacity available for immediate seat reservation")
    print(f"Pool passengers are seated optimally at departure")
    print(f"NUM_SIMS = {NUM_SIMS}, SEED = {SEED}")
    print("=" * 65)
    print()

    results = run_experiment(
        xlsx_path=xlsx_path,
        demand_grid=np.arange(0.8, 2.05, 0.1),
        y_values=(0, 10, 20, 30, 40, 50),
        num_sims=NUM_SIMS,
        seed=SEED,
    )

    elapsed = time.time() - t0
    print(f"\nSimulation completed in {elapsed:.0f}s")

    # ---- Summary table ----
    print("\n" + "=" * 65)
    print("RESULTS SUMMARY")
    print("=" * 65)
    summary_cols = [
        "demand_multiplier", "y_pct",
        "total_served_km_mean",
        "early_pax_km_mean", "pool_fitted_km_mean",
        "pool_rejected_km_mean", "fitting_failure_count_mean",
    ]
    print(results[summary_cols].round(1).to_string(index=False))

    # ---- Key findings ----
    print("\n" + "=" * 65)
    print("KEY FINDINGS")
    print("=" * 65)

    for dm_target in [1.0, 1.5, 2.0]:
        dm_actual = results["demand_multiplier"].unique()
        dm = min(dm_actual, key=lambda x: abs(x - dm_target))
        sub = results[results["demand_multiplier"] == dm].sort_values("y_pct")
        y0_km = sub[sub["y_pct"] == 0]["total_served_km_mean"].values[0]
        print(f"\n  Demand = {dm:.1f}x:")
        print(f"    Y=0 (all pooled) throughput: {y0_km:.0f} pax-km")
        for _, r in sub.iterrows():
            loss = y0_km - r["total_served_km_mean"]
            loss_pct = 100 * loss / y0_km if y0_km > 0 else 0
            print(f"    Y={r['y_pct']:2.0f}%: served={r['total_served_km_mean']:.0f}  "
                  f"loss vs Y=0: {loss:.0f} ({loss_pct:.1f}%)  "
                  f"fit_fail={r['fitting_failure_count_mean']:.1f}")

    # ---- Save ----
    csv_file = "pooled_reservation_results.csv"
    results.to_csv(csv_file, index=False)
    print(f"\nSaved: {csv_file}")

    make_plots(results, abc_path=abc_csv_path, xlsx_path=xlsx_path)

    print("\n" + "=" * 65)
    print("DONE")
    print("=" * 65)

    return results


if __name__ == "__main__":
    # Find Excel data file
    data_candidates = [
        "/mnt/data/20260327 CVA hackathon VR data.xlsx",
        "20260327 CVA hackathon VR data.xlsx",
        "/mnt/project/20260327_CVA_hackathon_VR_data.xlsx",
        "/mnt/user-data/uploads/20260327_CVA_hackathon_VR_data.xlsx",
    ]
    xlsx_path = next((p for p in data_candidates if os.path.exists(p)), None)
    if xlsx_path is None:
        raise FileNotFoundError(
            "Could not find the Excel data file. "
            "Place it in the same folder or update data_candidates."
        )

    # Find A/B/C reference results
    abc_candidates = [
        "fragmentation_decomposed.csv",
        "/mnt/user-data/uploads/fragmentation_decomposed.csv",
    ]
    abc_path = next((p for p in abc_candidates if os.path.exists(p)), None)
    if abc_path is None:
        print("WARNING: fragmentation_decomposed.csv not found. "
              "A/B/C reference lines will not appear in charts. "
              "Run the decomposed simulation first to generate it.")

    main(xlsx_path, abc_csv_path=abc_path)
