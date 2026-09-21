"""Linkage attack: a public voter list vs released health-style records.

Classic scenario: two datasets that look harmless on their own. Join them on
quasi-identifiers (age, ZIP, gender) and unique matches reveal identities.

This is the Sweeney / Netflix-style lesson: stripping names is not enough when
quasi-identifiers remain.
"""
from __future__ import annotations

import json

import pandas as pd

from anonymize import QI_ANON, generalize
from paths import ANON_CSV, PSEUDO_CSV, RAW_CSV, REPORTS_DIR, ROOT, VOTER_CSV, ensure_dirs
from risk_metrics import class_sizes

QI_RAW = ["age", "zip_code", "gender"]
VOTER_COLS = ["name", "age", "zip_code", "gender"]
COVERAGE = 0.40
SEED = 7


def make_voter_list(raw: pd.DataFrame, coverage: float = COVERAGE, seed: int = SEED) -> pd.DataFrame:
    """A fake public roster: names plus the same quasi-identifiers."""
    sample = raw.sample(frac=coverage, random_state=seed)
    return sample[VOTER_COLS].reset_index(drop=True)


def unique_links(released: pd.DataFrame, voter: pd.DataFrame, on: list[str]) -> pd.DataFrame:
    """Keep joins where the QI combination is unique on both sides."""
    rel = released.copy()
    vot = voter.copy()
    rel["_rel_k"] = class_sizes(rel, on)
    vot["_vot_k"] = class_sizes(vot, on)
    merged = vot.merge(rel, on=on, how="inner", suffixes=("_voter", "_released"))
    unique = merged[(merged["_rel_k"] == 1) & (merged["_vot_k"] == 1)]
    return unique.drop(columns=["_rel_k", "_vot_k"])


def attack_pseudonymized(pseudo: pd.DataFrame, voter: pd.DataFrame) -> dict:
    links = unique_links(pseudo, voter, QI_RAW)
    n_voter = len(voter)
    return {
        "dataset": "pseudonymized",
        "join_keys": QI_RAW,
        "voter_records": n_voter,
        "unique_links": int(len(links)),
        "reidentified_rate": round(100.0 * len(links) / n_voter, 2) if n_voter else 0.0,
    }


def attack_anonymized(anon: pd.DataFrame, voter: pd.DataFrame) -> dict:
    voter_g = generalize(voter)
    on = [c for c in QI_ANON if c in anon.columns]
    links = unique_links(anon, voter_g, on)
    n_voter = len(voter)
    return {
        "dataset": "anonymized",
        "join_keys": on,
        "voter_records": n_voter,
        "unique_links": int(len(links)),
        "reidentified_rate": round(100.0 * len(links) / n_voter, 2) if n_voter else 0.0,
    }


def run_linkage(
    raw: pd.DataFrame,
    pseudo: pd.DataFrame,
    anon: pd.DataFrame,
    coverage: float = COVERAGE,
) -> dict:
    voter = make_voter_list(raw, coverage=coverage)
    ensure_dirs()
    voter.to_csv(VOTER_CSV, index=False)
    pseudo_result = attack_pseudonymized(pseudo, voter)
    anon_result = attack_anonymized(anon, voter)
    return {
        "coverage": coverage,
        "voter_path": str(VOTER_CSV.relative_to(ROOT)).replace("\\", "/"),
        "pseudonymized": pseudo_result,
        "anonymized": anon_result,
        "reduction_factor": (
            round(pseudo_result["unique_links"] / max(anon_result["unique_links"], 1), 1)
            if pseudo_result["unique_links"]
            else None
        ),
    }


def main() -> None:
    raw = pd.read_csv(RAW_CSV, dtype={"zip_code": str}, keep_default_na=False)
    pseudo = pd.read_csv(PSEUDO_CSV, dtype={"zip_code": str}, keep_default_na=False)
    anon = pd.read_csv(ANON_CSV, dtype={"zip3": str}, keep_default_na=False)
    results = run_linkage(raw, pseudo, anon)

    p, a = results["pseudonymized"], results["anonymized"]
    print(f"Voter list: {p['voter_records']} records ({results['coverage']:.0%} of population)")
    print(
        f"[pseudonymized] unique links: {p['unique_links']} "
        f"({p['reidentified_rate']}% of the voter list)"
    )
    print(
        f"[anonymized]    unique links: {a['unique_links']} "
        f"({a['reidentified_rate']}% of the voter list)"
    )

    out = REPORTS_DIR / "linkage_results.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
