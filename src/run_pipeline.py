"""Run the full PACE pipeline and write reports/.

Usage (from the repo root, with src on PYTHONPATH or via):
    python src/run_pipeline.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import pandas as pd

from anonymize import DEFAULT_K, DEFAULT_L, QI_ANON, anonymize
from dictionary_attack import ROSTER_COVERAGE, run_attacks
from generate_data import generate, save
from linkage_attack import run_linkage
from paths import ANON_CSV, PSEUDO_CSV, RAW_CSV, REPORTS_DIR, VAULT_CSV, ensure_dirs
from plots import (
    plot_group_sizes,
    plot_linkage,
    plot_risk_by_region,
    plot_suppression_vs_k,
    plot_uniqueness_waffle,
    plot_utility_vs_k,
)
from pseudonymize import load_key, pseudonymize
from risk_metrics import DEFAULT_QI, summarize_risk
from utility import compare_utility, utility_vs_k


def _write_json(name: str, payload: dict) -> None:
    (REPORTS_DIR / name).write_text(json.dumps(payload, indent=2))


def _write_findings(payload: dict) -> None:
    b = payload["baseline"]
    d = payload["dictionary"]
    a = payload["anonymization"]
    link = payload["linkage"]
    u = payload["utility_k5"]
    text = f"""# Findings

Generated {payload["generated_at"]}. Synthetic n = {b["n_records"]}.

## Analyze: starting risk

On (age, ZIP, gender):

- **{b["pct_unique"]}%** of records are unique (k = 1).
- **{b["pct_below_k5"]}%** sit in a class smaller than k = 5.
- Worst-case prosecutor risk is **{b["prosecutor_risk"]}** (1 / min class size).

Hashing names away does not change this. Quasi-identifiers are the real join keys.

## Analyze: unsalted hashing fails

A dictionary of `first.lastNN@provider` emails, using a roster that covers
{d["roster_coverage"]:.0%} of names:

- Unsalted SHA-256 cracked **{d["unsalted_sha256"]["pct"]}%** of emails.
- HMAC-SHA256 with a secret key cracked **{d["keyed_hmac"]["pct"]}%**.

HMAC stops the rainbow-table attack. It does **not** stop linkage: after
pseudonymization, **{d["pct_unique_after_pseudonymization"]}%** of people are
still unique on age + ZIP + gender.

## Construct: anonymization (k = {a["k"]}, l = {a["l"]})

Generalize age to bands and ZIP to 3 digits, then suppress small or
non-diverse classes.

- Records kept: **{a["n_out"]} / {a["n_in"]}** (suppressed {a["suppression_rate"]}%).
- Achieved **k = {a["achieved_k"]}**, **l = {a["achieved_l"]}**.

## Execute: linkage attack

Join a fake public voter list (names + quasi-identifiers) to each release:

- Pseudonymized: **{link["pseudonymized"]["unique_links"]}** unique links
  ({link["pseudonymized"]["reidentified_rate"]}% of the voter list).
- Anonymized: **{link["anonymized"]["unique_links"]}** unique links
  ({link["anonymized"]["reidentified_rate"]}% of the voter list).

Two "anonymous" files can still identify someone when quasi-identifiers line up.
k-anonymity is what breaks uniqueness on those keys.

## Execute: utility

Same analyses on raw vs k = 5 anonymized data:

- Mean salary by age band, MAPE: **{u["salary_mape_pct"]}%**
- Medical-condition shares, total variation: **{u["condition_total_variation"]}**

See `utility_vs_k.png` for how that cost grows with k.

## Recommendations

1. Do not treat hashing or tokenization as anonymization. Tokens are still personal data.
2. Store the HMAC key and the vault off the analytics path; rotate the key if leaked.
3. Before a public or research release, enforce k-anonymity (and l-diversity on
   sensitive fields) on the actual quasi-identifiers an attacker would have.
4. Report suppression rate and utility loss next to k. Picking k = 5 without
   measuring either is theatre.
5. This demo is synthetic. Real releases need a documented QI list, a threat
   model, and a human review of residual unique cases.
"""
    (REPORTS_DIR / "findings.md").write_text(text.strip() + "\n")


def main() -> None:
    ensure_dirs()
    print("1/7 generate")
    raw = generate()
    save(raw)
    raw = pd.read_csv(RAW_CSV, dtype={"zip_code": str}, keep_default_na=False)

    print("2/7 baseline risk")
    baseline = summarize_risk(raw)
    _write_json("baseline.json", baseline)
    plot_group_sizes(raw)
    plot_uniqueness_waffle(baseline["pct_unique"], baseline["pct_below_k5"])
    plot_risk_by_region(raw)

    print("3/7 pseudonymize")
    key = load_key()
    pseudo, vault = pseudonymize(raw, key)
    pseudo.to_csv(PSEUDO_CSV, index=False)
    VAULT_CSV.parent.mkdir(exist_ok=True)
    vault.to_csv(VAULT_CSV, index=False)

    print("4/7 dictionary attack")
    roster = raw["name"].sample(frac=ROSTER_COVERAGE, random_state=42)
    dictionary = run_attacks(raw, key, roster)
    _write_json("pseudonymization_results.json", dictionary)

    print("5/7 anonymize")
    anon, anon_stats = anonymize(raw, k=DEFAULT_K, l=DEFAULT_L)
    anon.to_csv(ANON_CSV, index=False)
    _write_json("anonymization_results.json", anon_stats)

    print("6/7 linkage")
    linkage = run_linkage(raw, pseudo, anon)
    _write_json("linkage_results.json", linkage)
    plot_linkage(
        linkage["pseudonymized"]["reidentified_rate"],
        linkage["anonymized"]["reidentified_rate"],
    )

    print("7/7 utility")
    util_k5 = compare_utility(raw, anon)
    curve = utility_vs_k(raw)
    curve.to_csv(REPORTS_DIR / "utility_vs_k.csv", index=False)
    _write_json("utility_k5.json", util_k5)
    plot_utility_vs_k(curve)
    plot_suppression_vs_k(curve)

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "baseline": baseline,
        "dictionary": dictionary,
        "anonymization": anon_stats,
        "linkage": linkage,
        "utility_k5": util_k5,
        "utility_curve": curve.to_dict(orient="records"),
    }
    _write_json("summary.json", payload)
    _write_findings(payload)
    print(f"Done. Reports in {REPORTS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
