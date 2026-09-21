"""Generate ~5,000 synthetic people with Faker. No real personal data.

Direct identifiers: name, email, phone
Quasi-identifiers: age, zip_code, gender, job_title
Sensitive attributes: medical_condition, salary
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

from paths import RAW_CSV, ensure_dirs

SEED = 42
N_RECORDS = 5000

ZIP_PREFIXES = ["100", "606", "941", "331", "752", "981"]
ZIPS_PER_PREFIX = 10

JOBS: dict[str, tuple[int, int]] = {
    "Software Engineer": (105000, 20000),
    "Data Analyst": (72000, 12000),
    "Nurse": (78000, 10000),
    "Teacher": (55000, 8000),
    "Accountant": (68000, 11000),
    "Electrician": (62000, 9000),
    "Marketing Manager": (85000, 15000),
    "Cashier": (30000, 5000),
    "Physician": (210000, 40000),
    "Lawyer": (130000, 35000),
    "Chef": (45000, 8000),
    "Graphic Designer": (58000, 10000),
}
JOB_TITLES = list(JOBS.keys())
JOB_WEIGHTS = np.array([10, 8, 9, 10, 7, 6, 6, 9, 3, 4, 6, 5], dtype=float)
JOB_WEIGHTS /= JOB_WEIGHTS.sum()

CONDITIONS = [
    "No Condition",
    "Hypertension",
    "Diabetes",
    "Asthma",
    "Depression",
    "Heart Disease",
    "Cancer",
    "Arthritis",
]


def _zip_universe(rng: np.random.Generator) -> tuple[list[str], np.ndarray]:
    prefix_weights = rng.dirichlet(np.ones(len(ZIP_PREFIXES)) * 2.0)
    zip_codes: list[str] = []
    zip_weights: list[float] = []
    for prefix, p_w in zip(ZIP_PREFIXES, prefix_weights):
        suffixes = rng.choice(100, ZIPS_PER_PREFIX, replace=False)
        inner = rng.dirichlet(np.ones(ZIPS_PER_PREFIX) * 0.6)
        zip_codes += [f"{prefix}{s:02d}" for s in suffixes]
        zip_weights += list(p_w * inner)
    weights = np.array(zip_weights)
    return zip_codes, weights / weights.sum()


def pick_condition(age: int, rng: np.random.Generator) -> str:
    """Older people are more likely to have chronic conditions."""
    if age >= 50:
        base = np.array([0.20, 0.20, 0.15, 0.06, 0.08, 0.14, 0.09, 0.08])
    elif age < 30:
        base = np.array([0.60, 0.03, 0.03, 0.14, 0.14, 0.01, 0.01, 0.04])
    else:
        base = np.array([0.45, 0.10, 0.08, 0.10, 0.10, 0.05, 0.04, 0.08])
    base = base / base.sum()
    return str(rng.choice(CONDITIONS, p=base))


def generate(n: int = N_RECORDS, seed: int = SEED) -> pd.DataFrame:
    fake = Faker("en_US")
    Faker.seed(seed)
    rng = np.random.default_rng(seed)
    zip_codes, zip_weights = _zip_universe(rng)

    records = []
    seen_emails: set[str] = set()
    for i in range(n):
        gender = rng.choice(["Male", "Female", "Non-binary"], p=[0.49, 0.49, 0.02])
        if gender == "Male":
            first, last = fake.first_name_male(), fake.last_name()
        elif gender == "Female":
            first, last = fake.first_name_female(), fake.last_name()
        else:
            first, last = fake.first_name_nonbinary(), fake.last_name()

        name = f"{first} {last}"
        while True:
            email = f"{first}.{last}{rng.integers(1, 99)}@{fake.free_email_domain()}".lower()
            if email not in seen_emails:
                seen_emails.add(email)
                break

        age = int(np.clip(rng.normal(42, 14), 18, 90))
        zip_code = str(rng.choice(zip_codes, p=zip_weights))
        job = str(rng.choice(JOB_TITLES, p=JOB_WEIGHTS))
        mean, std = JOBS[job]
        experience_bump = 1 + (min(age, 60) - 30) * 0.006
        salary = int(max(20000, rng.normal(mean * experience_bump, std)))
        records.append(
            {
                "record_id": i + 1,
                "name": name,
                "email": email,
                "phone": fake.numerify("(%##) ###-####"),
                "age": age,
                "zip_code": zip_code,
                "gender": gender,
                "job_title": job,
                "medical_condition": pick_condition(age, rng),
                "salary": salary,
            }
        )
    return pd.DataFrame(records)


def save(df: pd.DataFrame, path: Path | None = None) -> Path:
    ensure_dirs()
    out = path or RAW_CSV
    df.to_csv(out, index=False)
    return out


def main() -> None:
    df = generate()
    out = save(df)
    print(f"Saved {len(df)} records to {out}")


if __name__ == "__main__":
    main()
