"""Why an unsalted hash is not protection, and why a keyed HMAC is.

Threat model: the attacker has (1) the published dataset and (2) a public
name roster covering part of the population (think voter list or company
directory) and (3) knows the common email format `first.last<NN>@provider`.
The attacker does not have the secret key.

Run from the repo root:  python src/dictionary_attack.py
"""
from __future__ import annotations

import json
import time

import pandas as pd

from paths import PSEUDO_CSV, RAW_CSV, REPORTS_DIR, ensure_dirs
from pseudonymize import TOKEN_LEN, load_key, make_token, sha256_hex
from risk_metrics import uniqueness_rate

DOMAINS = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"]
ROSTER_COVERAGE = 0.60
SEED = 42


def candidate_emails(names):
    """Yield every email the attacker would guess for each known name."""
    for name in names:
        parts = str(name).lower().split(" ", 1)
        if len(parts) != 2:
            continue
        first, rest = parts
        for suffix in range(1, 99):
            local = f"{first}.{rest}{suffix}"
            for domain in DOMAINS:
                yield f"{local}@{domain}"


def dictionary_attack(targets: set[str], names, hash_fn) -> tuple[dict, int]:
    """Hash every candidate; return {target_hash: guessed_email} for matches."""
    cracked, tried = {}, 0
    for email in candidate_emails(names):
        tried += 1
        h = hash_fn(email)
        if h in targets:
            cracked[h] = email
    return cracked, tried


def run_attacks(raw: pd.DataFrame, key: bytes, roster_names) -> dict:
    n = len(raw)
    covered = raw[raw["name"].isin(set(roster_names))]

    weak = set(raw["email"].map(sha256_hex))
    t0 = time.perf_counter()
    cracked_weak, tried = dictionary_attack(weak, roster_names, sha256_hex)
    secs_weak = time.perf_counter() - t0

    strong = set(raw["email"].map(lambda e: make_token(e, key)))
    t0 = time.perf_counter()
    cracked_strong, tried2 = dictionary_attack(
        strong, roster_names, lambda e: sha256_hex(e)[:TOKEN_LEN]
    )
    secs_strong = time.perf_counter() - t0

    still_unique = uniqueness_rate(raw, ["age", "zip_code", "gender"])
    return {
        "roster_coverage": ROSTER_COVERAGE,
        "roster_names": int(len(roster_names)),
        "records_with_known_name": int(len(covered)),
        "domains_guessed": DOMAINS,
        "guesses_tried": tried,
        "unsalted_sha256": {
            "cracked": len(cracked_weak),
            "of": n,
            "pct": round(100.0 * len(cracked_weak) / n, 2),
            "seconds": round(secs_weak, 2),
        },
        "keyed_hmac": {
            "cracked": len(cracked_strong),
            "of": n,
            "pct": round(100.0 * len(cracked_strong) / n, 2),
            "seconds": round(secs_strong, 2),
            "guesses_tried": tried2,
        },
        "pct_unique_after_pseudonymization": round(100.0 * still_unique, 2),
    }


def main() -> None:
    raw = pd.read_csv(RAW_CSV, dtype={"zip_code": str}, keep_default_na=False)
    key = load_key()
    roster = raw["name"].sample(frac=ROSTER_COVERAGE, random_state=SEED)
    results = run_attacks(raw, key, roster)

    n = results["unsalted_sha256"]["of"]
    print(
        f"Attacker roster: {results['roster_names']} names "
        f"({results['records_with_known_name']} of {n} records have a matching name)"
    )
    w = results["unsalted_sha256"]
    print(
        f"\n[1] Unsalted SHA-256 : cracked {w['cracked']}/{n} "
        f"({w['pct']:.1f}%) after {results['guesses_tried']:,} guesses in {w['seconds']:.1f}s"
    )
    s = results["keyed_hmac"]
    print(
        f"[2] Keyed HMAC tokens: cracked {s['cracked']}/{n} "
        f"({s['pct']:.1f}%) after {s['guesses_tried']:,} guesses in {s['seconds']:.1f}s"
    )
    print(
        f"\n[3] Pseudonymized data: {results['pct_unique_after_pseudonymization']:.1f}% "
        "of people are still unique on age + ZIP + gender (linkage risk untouched)"
    )

    ensure_dirs()
    out = REPORTS_DIR / "pseudonymization_results.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nSaved {out}")
    if not PSEUDO_CSV.exists():
        print("Note: run python src/pseudonymize.py to write data/pseudonymized.csv")


if __name__ == "__main__":
    main()
