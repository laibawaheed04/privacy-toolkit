"""How much analytical value is lost after anonymization."""
from __future__ import annotations

import numpy as np
import pandas as pd

from anonymize import age_band, anonymize


def with_age_band(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "age_band" not in out.columns:
        out["age_band"] = out["age"].map(lambda a: age_band(int(a)))
    return out


def salary_by_age_band(df: pd.DataFrame) -> pd.Series:
    return with_age_band(df).groupby("age_band")["salary"].mean().sort_index()


def condition_share(df: pd.DataFrame) -> pd.Series:
    return df["medical_condition"].value_counts(normalize=True).sort_index()


def mean_absolute_pct_error(truth: pd.Series, approx: pd.Series) -> float:
    aligned = pd.concat([truth, approx], axis=1, keys=["t", "a"]).dropna()
    if aligned.empty:
        return float("nan")
    denom = aligned["t"].replace(0, np.nan)
    return float((100.0 * (aligned["a"] - aligned["t"]).abs() / denom).mean())


def total_variation(p: pd.Series, q: pd.Series) -> float:
    idx = p.index.union(q.index)
    p = p.reindex(idx, fill_value=0)
    q = q.reindex(idx, fill_value=0)
    return float(0.5 * (p - q).abs().sum())


def compare_utility(raw: pd.DataFrame, anon: pd.DataFrame) -> dict:
    raw_sal = salary_by_age_band(raw)
    anon_sal = salary_by_age_band(anon)
    raw_cond = condition_share(raw)
    anon_cond = condition_share(anon)
    return {
        "salary_mape_pct": round(mean_absolute_pct_error(raw_sal, anon_sal), 3),
        "condition_total_variation": round(total_variation(raw_cond, anon_cond), 4),
        "n_raw": len(raw),
        "n_anon": len(anon),
        "salary_by_age_band_raw": {k: round(v, 2) for k, v in raw_sal.items()},
        "salary_by_age_band_anon": {k: round(v, 2) for k, v in anon_sal.items()},
        "condition_share_raw": {k: round(v, 4) for k, v in raw_cond.items()},
        "condition_share_anon": {k: round(v, 4) for k, v in anon_cond.items()},
    }


def utility_vs_k(
    raw: pd.DataFrame,
    ks: tuple[int, ...] = (2, 3, 5, 10, 15),
    l: int = 2,
) -> pd.DataFrame:
    rows = []
    for k in ks:
        anon, stats = anonymize(raw, k=k, l=l)
        util = compare_utility(raw, anon)
        rows.append(
            {
                "k": k,
                "l": l,
                "n_out": stats["n_out"],
                "suppression_rate": stats["suppression_rate"],
                "achieved_k": stats["achieved_k"],
                "achieved_l": stats["achieved_l"],
                "salary_mape_pct": util["salary_mape_pct"],
                "condition_total_variation": util["condition_total_variation"],
            }
        )
    return pd.DataFrame(rows)
