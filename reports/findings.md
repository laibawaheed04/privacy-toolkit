# Findings

Generated 2026-09-21 23:23 UTC. Synthetic n = 5,000.

## Starting risk

On age, ZIP, and gender alone:

- **26.66%** of records are unique (k = 1).
- **77.98%** sit in a class smaller than k = 5.
- Worst-case prosecutor risk is **1.0** (1 / minimum class size).

Hashing names away does not change any of this. Quasi-identifiers, not direct identifiers, are the real join keys.

## Unsalted hashing fails

A dictionary of `first.lastNN@provider` email guesses, run against a roster covering 60% of names:

- Unsalted SHA-256 cracked **61.88%** of emails.
- HMAC-SHA256 with a secret key cracked **0.0%**.

HMAC stops the dictionary attack, but it does not stop linkage. After pseudonymization, **26.66%** of people are still unique on age, ZIP, and gender — identical to the raw baseline.

## Anonymization (k = 5, l = 2)

Age generalized to 10-year bands, ZIP truncated to 3 digits, then classes suppressed below k or below l distinct medical conditions:

- Records kept: **4,935 / 5,000** (1.3% suppressed).
- Achieved **k = 5**, **l = 3**.

## Linkage attack

A fake public voter list (names plus quasi-identifiers) joined against each release:

- Pseudonymized: **524** unique links (26.2% of the voter list).
- Anonymized: **0** unique links (0.0% of the voter list).

Two datasets that each look anonymous on their own can still identify someone once their quasi-identifiers line up. k-anonymity is what actually removes that uniqueness, not the removal of names.

## Utility

Same analyses run on the raw and the k = 5 anonymized data:

- Mean salary by age band, MAPE: **0.319%**
- Medical condition shares, total variation: **0.001**

See `utility_vs_k.png` for how this cost grows as k increases.

## Recommendations

1. Do not treat hashing or tokenization as anonymization — a token is still personal data as long as it can be traced back to an identity.
2. Keep the HMAC key and the vault off the analytics path, and rotate the key if either is ever exposed.
3. Before any public or research release, enforce k-anonymity — and l-diversity on sensitive fields — using the quasi-identifiers an attacker could realistically obtain, not an assumed or convenient list.
4. Report suppression rate and utility loss alongside k. Choosing k = 5 without measuring either is a decision made on faith, not evidence.
5. This demo uses synthetic data. A real release needs a documented quasi-identifier list, an explicit threat model, and manual review of any residual unique cases.
