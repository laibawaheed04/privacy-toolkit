# Findings

Generated 2026-09-21 23:23 UTC. Synthetic n = 5000.

## Analyze: starting risk

On (age, ZIP, gender):

- **26.66%** of records are unique (k = 1).
- **77.98%** sit in a class smaller than k = 5.
- Worst-case prosecutor risk is **1.0** (1 / min class size).

Hashing names away does not change this. Quasi-identifiers are the real join keys.

## Analyze: unsalted hashing fails

A dictionary of `first.lastNN@provider` emails, using a roster that covers
60% of names:

- Unsalted SHA-256 cracked **61.88%** of emails.
- HMAC-SHA256 with a secret key cracked **0.0%**.

HMAC stops the rainbow-table attack. It does **not** stop linkage: after
pseudonymization, **26.66%** of people are
still unique on age + ZIP + gender.

## Construct: anonymization (k = 5, l = 2)

Generalize age to bands and ZIP to 3 digits, then suppress small or
non-diverse classes.

- Records kept: **4935 / 5000** (suppressed 1.3%).
- Achieved **k = 5**, **l = 3**.

## Execute: linkage attack

Join a fake public voter list (names + quasi-identifiers) to each release:

- Pseudonymized: **524** unique links
  (26.2% of the voter list).
- Anonymized: **0** unique links
  (0.0% of the voter list).

Two "anonymous" files can still identify someone when quasi-identifiers line up.
k-anonymity is what breaks uniqueness on those keys.

## Execute: utility

Same analyses on raw vs k = 5 anonymized data:

- Mean salary by age band, MAPE: **0.319%**
- Medical-condition shares, total variation: **0.001**

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
