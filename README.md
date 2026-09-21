# Privacy Toolkit

**Pseudonymize, anonymize, then attack your own data.**

Most portfolio projects stop at “I hashed the names.” This one measures whether the protection actually works, and how much analytical value you give up to get there.

All records are **synthetic** (Faker, seed 42). There is no real personal data in this repository.

| Release | Unique on age + ZIP + gender | Voter-list unique links | Mean salary MAPE |
| --- | --- | --- | --- |
| Raw / pseudonymized | 26.66% | 524 / 2,000 (26.2%) | — |
| Anonymized (k=5, l=2) | 0% | 0 / 2,000 (0%) | 0.32% |

Unsalted SHA-256 of emails: **61.88% cracked** from a name roster. HMAC-SHA256 with a secret key: **0% cracked**. Quasi-identifiers were never hashed, so linkage still worked until k-anonymity.

## What this project shows

1. **Pseudonymization** (HMAC-SHA256 tokens + a separate vault) is reversible and still personal data.
2. **Unsalted hashing is not protection** — a dictionary of `first.lastNN@provider` emails recovers most addresses.
3. **Anonymization** (age bands, 3-digit ZIP, suppress classes with k < 5 or l < 2) is irreversible and breaks unique joins.
4. **Utility is measurable.** The same salary-by-age-band and condition-share analyses run before and after; accuracy loss is charted as k grows.

## Pipeline (PACE)

```text
generate  →  baseline risk  →  dictionary attack
         →  HMAC tokens     →  k-anonymity + l-diversity
         →  voter-list join →  utility vs k  →  reports/
```

| Step | Script | Output |
| --- | --- | --- |
| Plan: synthetic people | `src/generate_data.py` | `data/raw_data.csv` |
| Analyze: uniqueness | `src/risk_metrics.py` | `reports/baseline.json` |
| Analyze: hash cracking | `src/dictionary_attack.py` | `reports/pseudonymization_results.json` |
| Construct: tokens | `src/pseudonymize.py` | `data/pseudonymized.csv`, `secrets/vault.csv` |
| Construct: k, l | `src/anonymize.py` | `data/anonymized.csv` |
| Execute: linkage | `src/linkage_attack.py` | `reports/linkage_results.json` |
| Execute: utility | `src/utility.py` | `reports/utility_vs_k.csv` |
| One command | `src/run_pipeline.py` | charts + `reports/findings.md` |

## Setup

```bash
git clone https://github.com/YOUR-USERNAME/privacy-toolkit.git
cd privacy-toolkit
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src/run_pipeline.py
python -m pytest
```

macOS / Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python src/run_pipeline.py
python -m pytest
```

Then open `notebooks/analysis.ipynb` and `reports/findings.md`.

Set `PSEUDO_KEY` if you want a chosen HMAC key; otherwise a random 32-byte key is written to `secrets/pseudo.key` (git-ignored).

## Results (this repo, n = 5,000)

**Baseline.** 26.66% of people are unique on (age, ZIP, gender). 77.98% sit in a class smaller than k = 5. Prosecutor risk is 1.0.

**Dictionary attack.** 1.47 million guesses, 60% name roster: unsalted SHA-256 cracked 3,094 emails (61.88%); keyed HMAC cracked 0. After tokenization, uniqueness on quasi-identifiers is unchanged at 26.66%.

**Anonymization.** Age bands + ZIP-3, then drop classes with k < 5 or fewer than 2 distinct medical conditions. 4,935 / 5,000 records kept (1.3% suppressed). Achieved k = 5, l = 3.

**Linkage.** Fake voter list of 2,000 names + quasi-identifiers. Pseudonymized release: 524 unique joins (26.2%). Anonymized release: 0 unique joins.

**Utility vs k** (salary MAPE by age band / condition total variation / % suppressed):

| k | MAPE % | TV | suppressed |
| --- | --- | --- | --- |
| 2 | 0.22 | 0.0006 | 0.26% |
| 5 | 0.32 | 0.0010 | 1.30% |
| 10 | 0.24 | 0.0043 | 2.66% |
| 15 | 3.10 | 0.0065 | 4.04% |

Charts: `reports/baseline_waffle.png`, `baseline_group_sizes.png`, `risk_by_region.png`, `linkage_attack.png`, `utility_vs_k.png`, `suppression_vs_k.png`.

## Recommendations

1. Do not call hashing or tokenization “anonymization.” Tokens plus a vault are still personal data.
2. Keep the HMAC key and vault off the analytics path.
3. Before a public or research release, enforce k-anonymity (and l-diversity on sensitive fields) on the quasi-identifiers an attacker would actually have.
4. Publish suppression rate and utility loss next to k.
5. This is a teaching demo on synthetic data. A real release needs a documented QI list, a threat model, and review of residual unique cases.

## Repository layout

```text
privacy-toolkit/
├── src/                 # pipeline modules (run from repo root)
├── data/                # synthetic CSV only
├── notebooks/analysis.ipynb
├── tests/test_pipeline.py
├── reports/             # JSON, CSV, PNG, findings.md
├── secrets/             # git-ignored key + vault
├── requirements.txt
└── pyproject.toml       # pytest pythonpath
```

## License

MIT. Synthetic data only; do not use this as a compliance tool for real personal data.
