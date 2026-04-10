"""
VR seat-fragmentation model — with gap decomposition

Three benchmarks:
  A) LP optimum:           theoretical max pax-km (perfect hindsight, leg-capacity only)
  B) Sequential optimal:   passengers arrive in booking order, 100% take system seat
  C) Sequential behavioral: passengers arrive in booking order, 50% deviate to windows

Gap decomposition:
  Total gap        = A - C
  Booking-order loss = A - B  (cost of sequential processing, even with perfect compliance)
  Seat-choice loss   = B - C  (additional cost of behavioral deviation)

This lets you say exactly how much of the lost capacity is due to
seat-selection behavior vs the inherent limitation of first-come-first-served.
"""

from __future__ import annotations

import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import linprog

# -----------------------------
# Global settings
# -----------------------------
STATIONS = ["A", "B", "C", "D", "E", "F", "G"]
NUM_LEGS = len(STATIONS) - 1

TOTAL_SEATS = 200
WINDOW_SEATS = 100
AISLE_SEATS = 100

SEED = 42
NUM_SIMS = 200

# OD volumes from the hackathon assumptions
OD_VOLUMES = {
    (0, 1): 1000, (0, 2):  900, (0, 3): 800, (0, 4): 700, (0, 5): 600, (0, 6): 500,
    (1, 2):  900, (1, 3):  800, (1, 4): 700, (1, 5): 600, (1, 6): 500,
    (2, 3):  800, (2, 4):  700, (2, 5): 600, (2, 6): 500,
    (3, 4):  700, (3, 5):  600, (3, 6): 500,
    (4, 5):  600, (4, 6):  500,
    (5, 6):  500,
}

REFERENCE_LEG_LOADS = np.zeros(NUM_LEGS, dtype=float)
for (o, d), v in OD_VOLUMES.items():
    REFERENCE_LEG_LOADS[o:d] += v
REFERENCE_PEAK = REFERENCE_LEG_LOADS.max()


# -----------------------------
# Helpers
# -----------------------------
def interval_to_mask(o: int, d: int) -> int:
    mask = 0
    for leg in range(o, d):
        mask |= (1 << leg)
    return mask


def popcount(x: int) -> int:
    return int(bin(x).count("1"))


# -----------------------------
# Booking curves
# -----------------------------
def load_booking_pmfs(xlsx_path: str) -> dict[tuple[int, int], tuple[np.ndarray, np.ndarray]]:
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

    avg_by_length = {
        L: np.mean(np.vstack(v), axis=0)
        for L, v in by_length.items()
    }

    all_days = np.arange(0, 91)
    for o in range(NUM_LEGS):
        for d in range(o + 1, len(STATIONS)):
            if (o, d) not in pmfs:
                pmfs[(o, d)] = (all_days, avg_by_length[d - o])

    return pmfs


# -----------------------------
# Request generation
# -----------------------------
def generate_requests(
    target_peak_load: float,
    booking_pmfs: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]],
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


# -----------------------------
# Benchmark A: Exact LP optimum
# -----------------------------
def exact_frictionless_optimum(req: pd.DataFrame, seat_capacity: int = TOTAL_SEATS) -> dict:
    n = len(req)
    if n == 0:
        return {"served_km": 0.0, "served_count": 0.0, "fractional_count": 0}

    A = np.zeros((NUM_LEGS, n), dtype=float)
    for i, (o, d) in enumerate(zip(req["o"], req["d"])):
        A[o:d, i] = 1.0

    b = np.full(NUM_LEGS, seat_capacity, dtype=float)
    c = -req["nlegs"].to_numpy(dtype=float)

    res = linprog(c=c, A_ub=A, b_ub=b, bounds=[(0, 1)] * n, method="highs")

    if res.status != 0:
        raise RuntimeError(f"LP failed: {res.message}")

    x = res.x
    frac_mask = (x > 1e-8) & (x < 1 - 1e-8)
    fractional_count = int(frac_mask.sum())

    accepted = x > 1 - 1e-8
    served_km = float(req.loc[accepted, "nlegs"].sum())
    served_count = int(accepted.sum())

    return {
        "served_km": served_km,
        "served_count": served_count,
        "fractional_count": fractional_count,
    }


# -----------------------------
# Greedy seat offer (used by both B and C)
# -----------------------------
def offered_seat_greedy_best_fit(
    seat_masks: np.ndarray,
    req_mask: int,
    o: int,
    d: int,
) -> int | None:
    """
    Among seats free on [o,d), choose the seat already most occupied
    elsewhere, preserving clean seats for future long journeys.
    Ties broken by preferring aisle seats (reserve windows for deviators).
    """
    free = (seat_masks & req_mask) == 0
    free_idx = np.where(free)[0]
    if len(free_idx) == 0:
        return None

    scores = []
    for s in free_idx:
        occ = seat_masks[s]
        occupied_elsewhere = popcount(occ)
        is_aisle = int(s >= WINDOW_SEATS)
        scores.append((occupied_elsewhere, is_aisle, -int(s)))

    best_pos = max(range(len(scores)), key=lambda i: scores[i])
    best = free_idx[best_pos]
    return int(best)


def choose_behavioral_seat(
    free_idx: np.ndarray,
    rng: np.random.Generator,
) -> int:
    window = free_idx[free_idx < WINDOW_SEATS]
    if len(window) > 0:
        return int(window[rng.integers(len(window))])
    return int(free_idx[rng.integers(len(free_idx))])


# -----------------------------
# Benchmark B: Sequential optimal (100% compliance)
# -----------------------------
def simulate_sequential_optimal(req: pd.DataFrame) -> dict:
    """
    Passengers arrive in booking order.
    Each gets the system-assigned optimal seat (100% compliance).
    If no continuous seat available → rejected.
    """
    seat_masks = np.zeros(TOTAL_SEATS, dtype=np.uint8)
    served_km = 0
    rejected_km = 0
    served_n = 0
    rejected_n = 0

    for row in req.itertuples(index=False):
        req_mask = int(row.mask)
        o = int(row.o)
        d = int(row.d)
        nlegs = int(row.nlegs)

        offered = offered_seat_greedy_best_fit(seat_masks, req_mask, o, d)

        if offered is None:
            rejected_km += nlegs
            rejected_n += 1
            continue

        # 100% compliance: always take the offered seat
        seat_masks[offered] |= req_mask
        served_km += nlegs
        served_n += 1

    return {
        "served_km": served_km,
        "rejected_km": rejected_km,
        "served_n": served_n,
        "rejected_n": rejected_n,
    }


# -----------------------------
# Benchmark C: Sequential behavioral (50% compliance)
# -----------------------------
def simulate_behavioral_booking(
    req: pd.DataFrame,
    compliance_prob: float,
    rng: np.random.Generator,
) -> dict:
    """
    Passengers arrive in booking order.
    50% take system seat, 50% pick their own (prefer windows).
    If no continuous seat available → rejected.
    """
    seat_masks = np.zeros(TOTAL_SEATS, dtype=np.uint8)
    served_km = 0
    rejected_km = 0
    served_n = 0
    rejected_n = 0

    for row in req.itertuples(index=False):
        req_mask = int(row.mask)
        o = int(row.o)
        d = int(row.d)
        nlegs = int(row.nlegs)

        free = (seat_masks & req_mask) == 0
        free_idx = np.where(free)[0]

        if len(free_idx) == 0:
            rejected_km += nlegs
            rejected_n += 1
            continue

        offered = offered_seat_greedy_best_fit(seat_masks, req_mask, o, d)

        if offered is None:
            rejected_km += nlegs
            rejected_n += 1
            continue

        if rng.random() < compliance_prob:
            chosen = offered
        else:
            chosen = choose_behavioral_seat(free_idx, rng)

        seat_masks[chosen] |= req_mask
        served_km += nlegs
        served_n += 1

    return {
        "served_km": served_km,
        "rejected_km": rejected_km,
        "served_n": served_n,
        "rejected_n": rejected_n,
    }


# -----------------------------
# Statistics helper
# -----------------------------
def summarize(series: list[float]) -> tuple[float, float, float]:
    arr = np.asarray(series, dtype=float)
    mean = arr.mean()
    std = arr.std(ddof=1) if len(arr) > 1 else 0.0
    ci95 = 1.96 * std / math.sqrt(len(arr)) if len(arr) > 1 else 0.0
    return mean, std, ci95


# -----------------------------
# Experiment runner
# -----------------------------
def run_experiment(
    xlsx_path: str,
    demand_grid: np.ndarray | list[float] = np.arange(0.8, 2.05, 0.1),
    num_sims: int = NUM_SIMS,
    compliance_prob: float = 0.50,
    seed: int = SEED,
) -> pd.DataFrame:
    booking_pmfs = load_booking_pmfs(xlsx_path)
    master_rng = np.random.default_rng(seed)

    results = []

    for dm in demand_grid:
        lp_vals = []       # A: LP optimum
        seq_opt_vals = []   # B: sequential, 100% compliance
        seq_beh_vals = []   # C: sequential, 50% compliance
        frac_counts = []

        print(f"  Demand multiplier {dm:.1f}x ...", end=" ", flush=True)

        for _ in range(num_sims):
            sim_seed = int(master_rng.integers(0, 2**31 - 1))
            rng_req = np.random.default_rng(sim_seed)
            rng_beh = np.random.default_rng(sim_seed + 1)

            req = generate_requests(dm, booking_pmfs, rng_req, poisson_counts=True)

            # A: LP optimum
            lp = exact_frictionless_optimum(req)
            lp_vals.append(lp["served_km"])
            frac_counts.append(lp["fractional_count"])

            # B: sequential optimal (100% compliance)
            seq_opt = simulate_sequential_optimal(req)
            seq_opt_vals.append(seq_opt["served_km"])

            # C: sequential behavioral (50% compliance)
            seq_beh = simulate_behavioral_booking(req, compliance_prob, rng_beh)
            seq_beh_vals.append(seq_beh["served_km"])

        lp_mean, lp_std, lp_ci = summarize(lp_vals)
        so_mean, so_std, so_ci = summarize(seq_opt_vals)
        sb_mean, sb_std, sb_ci = summarize(seq_beh_vals)

        total_gap = lp_mean - sb_mean
        booking_order_loss = lp_mean - so_mean
        seat_choice_loss = so_mean - sb_mean

        total_gap_pct = 100 * total_gap / lp_mean if lp_mean > 0 else 0.0
        booking_order_pct = 100 * booking_order_loss / lp_mean if lp_mean > 0 else 0.0
        seat_choice_pct = 100 * seat_choice_loss / lp_mean if lp_mean > 0 else 0.0

        print(f"LP={lp_mean:.0f}  SeqOpt={so_mean:.0f}  SeqBeh={sb_mean:.0f}  "
              f"| booking_order_loss={booking_order_pct:.2f}%  seat_choice_loss={seat_choice_pct:.2f}%  "
              f"total={total_gap_pct:.2f}%")

        results.append({
            "demand_multiplier": dm,
            # A: LP optimum
            "lp_served_mean": lp_mean,
            "lp_served_std": lp_std,
            "lp_served_ci95": lp_ci,
            # B: sequential optimal
            "seq_opt_served_mean": so_mean,
            "seq_opt_served_std": so_std,
            "seq_opt_served_ci95": so_ci,
            # C: sequential behavioral
            "seq_beh_served_mean": sb_mean,
            "seq_beh_served_std": sb_std,
            "seq_beh_served_ci95": sb_ci,
            # Gap decomposition
            "total_gap_km": total_gap,
            "total_gap_pct": total_gap_pct,
            "booking_order_loss_km": booking_order_loss,
            "booking_order_loss_pct": booking_order_pct,
            "seat_choice_loss_km": seat_choice_loss,
            "seat_choice_loss_pct": seat_choice_pct,
            # Sanity
            "max_fractional_vars": max(frac_counts),
        })

    return pd.DataFrame(results)


# -----------------------------
# Context with real trains
# -----------------------------
def load_train_context(xlsx_path: str) -> pd.DataFrame:
    trains = pd.read_excel(xlsx_path, sheet_name="Trains").copy()
    trains["load_factor"] = trains["Max_pax"] / trains["Capacity"]
    return trains


# -----------------------------
# Plotting
# -----------------------------
def make_plots(
    results: pd.DataFrame,
    trains: pd.DataFrame | None = None,
    out_png: str = "fragmentation_decomposed.png",
):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "VR Seat Fragmentation: Decomposing Lost Passenger-km",
        fontsize=14, fontweight="bold",
    )

    dm = results["demand_multiplier"]

    # ---- Plot 1: Three throughput curves ----
    ax = axes[0, 0]
    ax.plot(dm, results["lp_served_mean"], "g-o", ms=4, lw=2,
            label="A: LP optimum (theoretical max)")
    ax.fill_between(dm,
                    results["lp_served_mean"] - results["lp_served_ci95"],
                    results["lp_served_mean"] + results["lp_served_ci95"],
                    alpha=0.12, color="green")
    ax.plot(dm, results["seq_opt_served_mean"], "b-^", ms=4, lw=2,
            label="B: Sequential, 100% compliance")
    ax.fill_between(dm,
                    results["seq_opt_served_mean"] - results["seq_opt_served_ci95"],
                    results["seq_opt_served_mean"] + results["seq_opt_served_ci95"],
                    alpha=0.12, color="blue")
    ax.plot(dm, results["seq_beh_served_mean"], "r-s", ms=4, lw=2,
            label="C: Sequential, 50% deviate")
    ax.fill_between(dm,
                    results["seq_beh_served_mean"] - results["seq_beh_served_ci95"],
                    results["seq_beh_served_mean"] + results["seq_beh_served_ci95"],
                    alpha=0.12, color="red")
    ax.set_xlabel("Demand multiplier", fontsize=11)
    ax.set_ylabel("Served passenger-km", fontsize=11)
    ax.set_title("Throughput: Three Benchmarks")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # ---- Plot 2: Stacked bar — gap decomposition in pax-km ----
    ax = axes[0, 1]
    w = 0.07
    ax.bar(dm, results["booking_order_loss_km"], width=w,
           label="Booking-order loss (A→B)", color="#3498db", alpha=0.85)
    ax.bar(dm, results["seat_choice_loss_km"], width=w,
           bottom=results["booking_order_loss_km"],
           label="Seat-choice loss (B→C)", color="#e74c3c", alpha=0.85)
    ax.set_xlabel("Demand multiplier", fontsize=11)
    ax.set_ylabel("Lost passenger-km", fontsize=11)
    ax.set_title("Gap Decomposition (absolute)")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, axis="y")

    # ---- Plot 3: % decomposition ----
    ax = axes[1, 0]
    ax.plot(dm, results["total_gap_pct"], "k-o", ms=5, lw=2, label="Total gap (A vs C)")
    ax.plot(dm, results["booking_order_loss_pct"], "b--^", ms=4, lw=1.5,
            label="Booking-order loss (A vs B)")
    ax.plot(dm, results["seat_choice_loss_pct"], "r--s", ms=4, lw=1.5,
            label="Seat-choice loss (B vs C)")
    ax.set_xlabel("Demand multiplier", fontsize=11)
    ax.set_ylabel("Loss as % of LP optimum", fontsize=11)
    ax.set_title("Gap Decomposition (relative)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # ---- Plot 4: Real train load factors ----
    ax = axes[1, 1]
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
        ax.set_xlabel("Load factor (%)", fontsize=11)
        ax.set_ylabel("Number of trains", fontsize=11)
        ax.set_title(f"Real VR Fleet: {len(trains)} Train Services")
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
    else:
        ax.axis("off")

    plt.tight_layout()
    plt.savefig(out_png, dpi=160, bbox_inches="tight")
    print(f"\nSaved plot: {out_png}")


# -----------------------------
# Main
# -----------------------------
def main(xlsx_path: str):
    print("=" * 65)
    print("VR SEAT FRAGMENTATION — DECOMPOSED ANALYSIS")
    print("=" * 65)
    print(f"A = LP optimum (theoretical max, perfect hindsight)")
    print(f"B = Sequential optimal (booking order, 100% compliance)")
    print(f"C = Sequential behavioral (booking order, 50% deviate)")
    print(f"")
    print(f"Booking-order loss = A - B")
    print(f"Seat-choice loss   = B - C")
    print(f"Total gap          = A - C")
    print(f"=" * 65)
    print()

    results = run_experiment(
        xlsx_path=xlsx_path,
        demand_grid=np.arange(0.8, 2.05, 0.1),
        num_sims=200,
        compliance_prob=0.50,
        seed=42,
    )

    trains = load_train_context(xlsx_path)

    # ---- Summary table ----
    print("\n" + "=" * 65)
    print("RESULTS SUMMARY")
    print("=" * 65)
    summary_cols = [
        "demand_multiplier",
        "lp_served_mean",
        "seq_opt_served_mean",
        "seq_beh_served_mean",
        "booking_order_loss_pct",
        "seat_choice_loss_pct",
        "total_gap_pct",
    ]
    print(results[summary_cols].round(2).to_string(index=False))

    # ---- Key findings ----
    print("\n" + "=" * 65)
    print("KEY FINDINGS")
    print("=" * 65)
    for target_dm in [1.0, 1.2, 1.5, 2.0]:
        idx = (results["demand_multiplier"] - target_dm).abs().idxmin()
        r = results.loc[idx]
        print(f"\n  Demand = {r['demand_multiplier']:.1f}x capacity:")
        print(f"    LP optimum:          {r['lp_served_mean']:,.0f} pax-km")
        print(f"    Seq. optimal (100%): {r['seq_opt_served_mean']:,.0f} pax-km")
        print(f"    Seq. behavioral(50%): {r['seq_beh_served_mean']:,.0f} pax-km")
        print(f"    ---")
        print(f"    Booking-order loss:   {r['booking_order_loss_pct']:.2f}% of optimum")
        print(f"    Seat-choice loss:     {r['seat_choice_loss_pct']:.2f}% of optimum")
        print(f"    Total gap:            {r['total_gap_pct']:.2f}% of optimum")

    if trains is not None:
        print(f"\n  VR Fleet Context:")
        print(f"    {len(trains)} trains, avg load factor {trains['load_factor'].mean():.0%}")
        n90 = (trains["load_factor"] > 0.90).sum()
        n100 = (trains["load_factor"] > 1.00).sum()
        print(f"    {n90} trains ({n90/len(trains):.1%}) above 90% load")
        print(f"    {n100} trains ({n100/len(trains):.1%}) above 100% load")

    # ---- Sanity check ----
    worst_frac = int(results["max_fractional_vars"].max())
    print(f"\n  LP integrality check: worst fractional count = {worst_frac}")
    if worst_frac == 0:
        print(f"  ✓ LP solutions are all integral (as expected for interval structure)")

    # ---- Save outputs ----
    results.to_csv("fragmentation_decomposed.csv", index=False)
    print("\nSaved: fragmentation_decomposed.csv")

    make_plots(results, trains, out_png="fragmentation_decomposed.png")

    return results, trains


if __name__ == "__main__":
    candidate_paths = [
        "/mnt/data/20260327 CVA hackathon VR data.xlsx",
        "20260327 CVA hackathon VR data.xlsx",
        "/mnt/project/20260327_CVA_hackathon_VR_data.xlsx",
        "/mnt/user-data/uploads/20260327_CVA_hackathon_VR_data.xlsx",
    ]
    xlsx_path = next((p for p in candidate_paths if os.path.exists(p)), None)
    if xlsx_path is None:
        raise FileNotFoundError(
            "Could not find the Excel file. "
            "Place '20260327 CVA hackathon VR data.xlsx' in the same folder or update candidate_paths."
        )
    main(xlsx_path)
