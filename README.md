# Privacy Toolkit

Pseudonymize synthetic personal data, anonymize it and then attack both releases to check whether the protection actually holds.

All records are synthetic, generated with Faker using a fixed seed (42). No real personal data is used anywhere in this repository.

## Results at a glance

| Release | Unique on age + ZIP + gender | Voter-list unique links | Mean salary MAPE |
|---|---|---|---|
| Raw / pseudonymized | 26.66% | 524 / 2,000 (26.2%) | — |
| Anonymized (k=5, l=2) | 0% | 0 / 2,000 (0%) | 0.32% |

Unsalted SHA-256 of emails was cracked for 61.88% of records using a partial name roster. The same attack against HMAC-SHA256 tokens cracked 0%. Quasi-identifiers (age, ZIP, gender) were never hashed in either release, so linkage worked against the pseudonymized data regardless — k-anonymity is what actually closed it.

## What this project demonstrates

1. **Pseudonymization is reversible.** HMAC-SHA256 tokens plus a separate vault can always be traced back to the original identity by whoever holds the key or the vault — it is still personal data under most privacy definitions.
2. **Unsalted hashing is not protection.** A dictionary of `first.lastNN@provider` email guesses recovers most addresses in seconds.
3. **Anonymization is irreversible.** Generalizing age to bands, ZIP to 3 digits, and suppressing any class with k < 5 or l < 2 removes the ability to make a unique join.
4. **Utility loss is measurable, not assumed.** The same salary-by-age-band and condition-share analyses run on both releases, and the accuracy lost is charted as k increases.

## Pipeline

```text
generate  ->  baseline risk  ->  dictionary attack
          ->  HMAC tokens    ->  k-anonymity + l-diversity
          ->  voter-list join -> utility vs. k -> reports/
```

| Stage | Script | Output |
|---|---|---|
| Generate synthetic people | `src/generate_data.py` | `data/raw_data.csv` |
| Measure baseline uniqueness | `src/risk_metrics.py` | `reports/baseline.json` |
| Attack unsalted hashes | `src/dictionary_attack.py` | `reports/pseudonymization_results.json` |
| Build pseudonymized release | `src/pseudonymize.py` | `data/pseudonymized.csv`, `secrets/vault.csv` |
| Build anonymized release | `src/anonymize.py` | `data/anonymized.csv` |
| Run linkage attack | `src/linkage_attack.py` | `reports/linkage_results.json` |
| Measure utility loss | `src/utility.py` | `reports/utility_vs_k.csv` |
| Run everything | `src/run_pipeline.py` | charts + `reports/findings.md` |

## Setup

```bash
git clone https://github.com/laibawaheed04/privacy-toolkit.git
cd privacy-toolkit
python -m venv .venv
```

**Windows (PowerShell)**

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**macOS / Linux**

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**Run**

```bash
python src/run_pipeline.py
python -m pytest
```

Then open `notebooks/analysis.ipynb` and `reports/findings.md`.

By default a random 32-byte HMAC key is generated on first run and stored in `secrets/pseudo.key` (git-ignored). Set the `PSEUDO_KEY` environment variable beforehand if you want to supply your own.

## Results in detail (n = 5,000)

**Baseline risk.** 26.66% of records are unique on age, ZIP, and gender alone. 77.98% sit in a group smaller than 5. Worst-case prosecutor risk is 1.0.

**Dictionary attack.** 1.47 million guessed emails, drawn from a roster covering 60% of names. Unsalted SHA-256 cracked 3,094 records (61.88%). Keyed HMAC cracked 0. Uniqueness on quasi-identifiers after tokenizing stayed at 26.66% — pseudonymization did not touch it.

**Anonymization.** Age generalized to 10-year bands, ZIP truncated to 3 digits, classes suppressed below k=5 or below 2 distinct medical conditions. 4,935 of 5,000 records kept (1.3% suppressed). Achieved k=5, l=3.

**Linkage attack.** A fake public voter list of 2,000 names plus quasi-identifiers, joined against each release. Pseudonymized: 524 unique matches (26.2%). Anonymized: 0.

**Utility vs. k**

| k | Salary MAPE (%) | Condition total variation | Suppressed |
|---|---|---|---|
| 2 | 0.22 | 0.0006 | 0.26% |
| 5 | 0.32 | 0.0010 | 1.30% |
| 10 | 0.24 | 0.0043 | 2.66% |
| 15 | 3.10 | 0.0065 | 4.04% |

Charts: `reports/baseline_waffle.png`, `baseline_group_sizes.png`, `risk_by_region.png`, `linkage_attack.png`, `utility_vs_k.png`, `suppression_vs_k.png`.

## Recommendations

1. Do not treat hashing or tokenization as anonymization. A token plus a vault is still personal data.
2. Keep the HMAC key and the vault off the analytics path, and rotate the key if either is exposed.
3. Before any public or research release, enforce k-anonymity — and l-diversity on sensitive fields — using the quasi-identifiers an attacker could realistically obtain.
4. Report suppression rate and utility loss alongside k. Choosing k without measuring either is not a real privacy decision.
5. This is a teaching exercise on synthetic data. A real release needs a documented list of quasi-identifiers, an explicit threat model, and manual review of any residual unique records.

## Repository layout

```text
privacy-toolkit/
├── src/                  pipeline modules, run from the repo root
├── data/                 synthetic CSVs only, regenerated by the pipeline
├── notebooks/
│   └── analysis.ipynb
├── tests/
│   └── test_pipeline.py
├── reports/               JSON, CSV, PNG charts, findings.md
├── secrets/               git-ignored: HMAC key and vault
├── requirements.txt
└── pyproject.toml         pytest configuration
```

## License

MIT. Built on synthetic data for demonstration only — not intended as a compliance tool for real personal data.
