"""k-anonymity + l-diversity via generalization and suppression.

Generalization
  age      -> 10-year bands (18-29, 30-39, ...)
  zip_code -> first 3 digits (region)

Suppression
  drop any equivalence class smaller than k, then any class with fewer
  than l distinct values of the sensitive attribute.
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd

from paths import ANON_CSV, RAW_CSV, ensure_dirs
from risk_metrics import achieved_l, min_k, summarize_risk

DIRECT_IDENTIFIERS = ["name", "email", "phone", "record_id"]
QI_ANON = ["age_band", "zip3", "gender"]
SENSITIVE = "medical_condition"
DEFAULT_K = 5
DEFAULT_L = 2


def age_band(age: int) -> str:
    if age < 30:
        return "18-29"
    if age < 40:
        return "30-39"
    if age < 50:
        return "40-49"
    if age < 60:
        return "50-59"
    if age < 70:
        return "60-69"
    return "70+"


def generalize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["age_band"] = out["age"].map(lambda a: age_band(int(a)))
    out["zip3"] = out["zip_code"].astype(str).str.zfill(5).str[:3]
    return out


def _keep_classes(
    df: pd.DataFrame,
    qi: Iterable[str],
    mask_index: pd.Index,
) -> pd.DataFrame:
    qi = list(qi)
    keyed = df.set_index(qi)
    return keyed[keyed.index.isin(mask_index)].reset_index()


def suppress_below_k(df: pd.DataFrame, k: int, qi: Iterable[str] = QI_ANON) -> pd.DataFrame:
    qi = list(qi)
    sizes = df.groupby(qi, dropna=False).size()
    keep = sizes[sizes >= k].index
    return _keep_classes(df, qi, keep)


def suppress_below_l(
    df: pd.DataFrame,
    l: int,
    qi: Iterable[str] = QI_ANON,
    sensitive: str = SENSITIVE,
) -> pd.DataFrame:
    qi = list(qi)
    diversity = df.groupby(qi, dropna=False)[sensitive].nunique()
    keep = diversity[diversity >= l].index
    return _keep_classes(df, qi, keep)


def anonymize(
    df: pd.DataFrame,
    k: int = DEFAULT_K,
    l: int = DEFAULT_L,
    drop_identifiers: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """Return (anonymized_frame, stats). Irreversible: originals are not stored."""
    n_in = len(df)
    work = generalize(df)
    if drop_identifiers:
        drop = [c for c in DIRECT_IDENTIFIERS + ["age", "zip_code"] if c in work.columns]
        work = work.drop(columns=drop)

    after_gen = work.copy()
    work = suppress_below_k(work, k)
    n_after_k = len(work)
    work = suppress_below_l(work, l)
    n_out = len(work)

    stats = {
        "k": k,
        "l": l,
        "n_in": n_in,
        "n_after_generalization": n_in,
        "n_after_k": n_after_k,
        "n_out": n_out,
        "suppressed": n_in - n_out,
        "suppression_rate": round(100.0 * (n_in - n_out) / n_in, 2) if n_in else 0.0,
        "achieved_k": min_k(work, QI_ANON) if n_out else 0,
        "achieved_l": achieved_l(work, QI_ANON, SENSITIVE) if n_out else 0,
        "risk_after": summarize_risk(work, QI_ANON, SENSITIVE, k) if n_out else {},
        "risk_after_generalization_only": summarize_risk(
            after_gen, QI_ANON, SENSITIVE, k
        ),
    }
    return work.reset_index(drop=True), stats


def main() -> None:
    raw = pd.read_csv(RAW_CSV, dtype={"zip_code": str}, keep_default_na=False)
    anon, stats = anonymize(raw, k=DEFAULT_K, l=DEFAULT_L)
    ensure_dirs()
    anon.to_csv(ANON_CSV, index=False)
    print(f"Anonymized {stats['n_in']} -> {stats['n_out']} records "
          f"(suppressed {stats['suppression_rate']}%)")
    print(f"  achieved k={stats['achieved_k']}, l={stats['achieved_l']}")
    print(f"  output: {ANON_CSV}")
    print(anon.head(3).to_string())


if __name__ == "__main__":
    main()
