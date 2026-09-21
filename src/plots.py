"""Charts written to reports/."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from paths import REPORTS_DIR, ensure_dirs
from risk_metrics import DEFAULT_QI, class_sizes

sns.set_theme(style="whitegrid", context="talk")
PALETTE = ["#1f4e79", "#c0392b", "#1e8449", "#b9770e"]


def _save(fig: plt.Figure, name: str) -> None:
    ensure_dirs()
    path = REPORTS_DIR / name
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def plot_group_sizes(df: pd.DataFrame, qi=DEFAULT_QI, title_suffix: str = "raw") -> None:
    sizes = df.groupby(list(qi), dropna=False).size()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(sizes, bins=range(1, min(int(sizes.max()) + 2, 40)), color=PALETTE[0], edgecolor="white")
    ax.set_xlabel("Equivalence class size (age, ZIP, gender)")
    ax.set_ylabel("Number of classes")
    ax.set_title(f"Class-size distribution ({title_suffix})")
    ax.axvline(5, color=PALETTE[1], linestyle="--", label="k = 5")
    ax.legend()
    _save(fig, "baseline_group_sizes.png" if title_suffix == "raw" else f"group_sizes_{title_suffix}.png")


def plot_uniqueness_waffle(pct_unique: float, pct_below_k5: float) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels = ["Unique (k=1)", "k < 5", "k ≥ 5"]
    # pct_below_k5 includes uniques; split them
    unique = pct_unique
    small = max(pct_below_k5 - pct_unique, 0)
    safe = max(100.0 - pct_below_k5, 0)
    ax.barh(["Records"], [unique], color=PALETTE[1], label=labels[0])
    ax.barh(["Records"], [small], left=[unique], color="#e67e22", label=labels[1])
    ax.barh(["Records"], [safe], left=[unique + small], color=PALETTE[2], label=labels[2])
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of records")
    ax.set_title("Baseline prosecutor risk on quasi-identifiers")
    ax.legend(loc="lower right")
    _save(fig, "baseline_waffle.png")


def plot_risk_by_region(df: pd.DataFrame) -> None:
    work = df.copy()
    work["zip3"] = work["zip_code"].astype(str).str[:3]
    work["_k"] = class_sizes(work, ["age", "zip_code", "gender"])
    rates = work.groupby("zip3")["_k"].apply(lambda s: 100.0 * (s == 1).mean()).sort_values()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(rates.index.astype(str), rates.values, color=PALETTE[0])
    ax.set_ylabel("% unique on age + ZIP + gender")
    ax.set_xlabel("ZIP prefix")
    ax.set_title("Re-identification risk by region")
    _save(fig, "risk_by_region.png")


def plot_linkage(pseudo_rate: float, anon_rate: float) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.bar(["Pseudonymized", "Anonymized (k=5)"], [pseudo_rate, anon_rate], color=[PALETTE[1], PALETTE[2]])
    ax.set_ylabel("% of voter-list names uniquely linked")
    ax.set_title("Linkage attack: two datasets, one identity")
    _save(fig, "linkage_attack.png")


def plot_utility_vs_k(curve: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    axes[0].plot(curve["k"], curve["salary_mape_pct"], marker="o", color=PALETTE[0])
    axes[0].set_xlabel("k")
    axes[0].set_ylabel("MAPE of mean salary by age band (%)")
    axes[0].set_title("Utility loss: salary")
    axes[1].plot(curve["k"], curve["condition_total_variation"], marker="o", color=PALETTE[3])
    axes[1].set_xlabel("k")
    axes[1].set_ylabel("Total variation of condition shares")
    axes[1].set_title("Utility loss: medical conditions")
    _save(fig, "utility_vs_k.png")


def plot_suppression_vs_k(curve: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(curve["k"], curve["suppression_rate"], marker="o", color=PALETTE[1])
    ax.set_xlabel("k")
    ax.set_ylabel("Records suppressed (%)")
    ax.set_title("Privacy cost: suppression as k grows")
    _save(fig, "suppression_vs_k.png")
