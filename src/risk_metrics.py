"""Re-identification risk on quasi-identifiers.

k-anonymity: every equivalence class (same QI values) has size >= k.
l-diversity: every class has at least l distinct sensitive values.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

DEFAULT_QI = ["age", "zip_code", "gender"]
DEFAULT_SENSITIVE = "medical_condition"


def class_sizes(df: pd.DataFrame, qi: Iterable[str] = DEFAULT_QI) -> pd.Series:
    qi = list(qi)
    return df.groupby(qi, dropna=False)[qi[0]].transform("size")


def uniqueness_rate(df: pd.DataFrame, qi: Iterable[str] = DEFAULT_QI) -> float:
    return float((class_sizes(df, qi) == 1).mean())


def min_k(df: pd.DataFrame, qi: Iterable[str] = DEFAULT_QI) -> int:
    sizes = df.groupby(list(qi), dropna=False).size()
    return int(sizes.min()) if len(sizes) else 0


def achieved_l(
    df: pd.DataFrame,
    qi: Iterable[str] = DEFAULT_QI,
    sensitive: str = DEFAULT_SENSITIVE,
) -> int:
    if df.empty:
        return 0
    return int(df.groupby(list(qi), dropna=False)[sensitive].nunique().min())


def pct_below_k(df: pd.DataFrame, k: int, qi: Iterable[str] = DEFAULT_QI) -> float:
    return float((class_sizes(df, qi) < k).mean())


def prosecutor_risk(df: pd.DataFrame, qi: Iterable[str] = DEFAULT_QI) -> float:
    """Worst-case probability of singling someone out (1 / smallest class)."""
    k = min_k(df, qi)
    return 1.0 / k if k else 1.0


def summarize_risk(
    df: pd.DataFrame,
    qi: Iterable[str] = DEFAULT_QI,
    sensitive: str = DEFAULT_SENSITIVE,
    k_threshold: int = 5,
) -> dict:
    sizes = df.groupby(list(qi), dropna=False).size()
    n = len(df)
    unique = int((sizes == 1).sum())
    records_unique = int((class_sizes(df, qi) == 1).sum())
    return {
        "quasi_identifiers": list(qi),
        "n_records": n,
        "n_equivalence_classes": int(len(sizes)),
        "n_unique_classes": unique,
        "n_unique_records": records_unique,
        "pct_unique": round(100.0 * records_unique / n, 2) if n else 0.0,
        "min_k": int(sizes.min()) if len(sizes) else 0,
        "median_class_size": float(np.median(sizes)) if len(sizes) else 0.0,
        "pct_below_k5": round(100.0 * pct_below_k(df, k_threshold, qi), 2),
        "prosecutor_risk": round(prosecutor_risk(df, qi), 4),
        "achieved_l": achieved_l(df, qi, sensitive),
    }
