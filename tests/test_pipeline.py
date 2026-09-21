import pandas as pd
import pytest

from anonymize import DIRECT_IDENTIFIERS, age_band, anonymize, generalize
from generate_data import generate
from linkage_attack import attack_anonymized, attack_pseudonymized, make_voter_list
from pseudonymize import DIRECT_IDENTIFIERS as PSEUDO_IDS
from pseudonymize import make_token, pseudonymize, reidentify, sha256_hex
from risk_metrics import min_k, summarize_risk, uniqueness_rate
from utility import compare_utility, salary_by_age_band

KEY_A, KEY_B = b"a" * 32, b"b" * 32


@pytest.fixture
def tiny():
    return pd.DataFrame(
        {
            "record_id": [1, 2, 3],
            "name": ["Ann Lee", "Bob Ray", "Cy Doe"],
            "email": ["ann.lee1@x.com", "bob.ray2@x.com", "cy.doe3@x.com"],
            "phone": ["(201) 555-0101", "(202) 555-0102", "(203) 555-0103"],
            "age": [30, 40, 50],
            "zip_code": ["10001", "10002", "10003"],
            "gender": ["F", "M", "M"],
            "job_title": ["Teacher", "Nurse", "Chef"],
            "medical_condition": ["Asthma", "Diabetes", "Asthma"],
            "salary": [50000, 60000, 70000],
        }
    )


@pytest.fixture
def crowd():
    """Unique on exact QI, but the same age band + ZIP-3 + gender."""
    rows = []
    rid = 1
    specs = [
        (22, "10001", "Female"),
        (23, "10002", "Female"),
        (24, "10003", "Female"),
        (25, "10004", "Female"),
        (26, "10005", "Female"),
        (32, "60611", "Male"),
        (33, "60612", "Male"),
        (34, "60613", "Male"),
        (35, "60614", "Male"),
        (36, "60615", "Male"),
    ]
    conditions = ["Asthma", "Diabetes", "Asthma", "Diabetes", "Asthma"]
    for i, (age, zip_code, gender) in enumerate(specs):
        rows.append(
            {
                "record_id": rid,
                "name": f"Person {rid}",
                "email": f"p{rid}@x.com",
                "phone": "(201) 555-0100",
                "age": age,
                "zip_code": zip_code,
                "gender": gender,
                "job_title": "Teacher",
                "medical_condition": conditions[i % len(conditions)],
                "salary": 50000 + i * 100,
            }
        )
        rid += 1
    return pd.DataFrame(rows)


def test_generate_shape_and_uniqueness():
    df = generate(n=200, seed=1)
    assert len(df) == 200
    assert df["email"].is_unique
    assert df["age"].between(18, 90).all()
    assert {
        "name",
        "email",
        "phone",
        "age",
        "zip_code",
        "gender",
        "job_title",
        "medical_condition",
        "salary",
    }.issubset(df.columns)


def test_token_is_deterministic():
    assert make_token("a@x.com", KEY_A) == make_token("a@x.com", KEY_A)


def test_token_normalizes_case_and_whitespace():
    assert make_token(" A@X.com ", KEY_A) == make_token("a@x.com", KEY_A)


def test_token_depends_on_key():
    assert make_token("a@x.com", KEY_A) != make_token("a@x.com", KEY_B)


def test_token_differs_from_plain_hash():
    assert make_token("a@x.com", KEY_A) != sha256_hex("a@x.com")[:16]


def test_no_direct_identifiers_remain(tiny):
    pseudo, _ = pseudonymize(tiny, KEY_A)
    for col in PSEUDO_IDS + ["record_id"]:
        assert col not in pseudo.columns


def test_quasi_identifiers_are_preserved(tiny):
    pseudo, _ = pseudonymize(tiny, KEY_A)
    assert pseudo[["age", "zip_code", "gender"]].equals(tiny[["age", "zip_code", "gender"]])


def test_tokens_unique_per_person(tiny):
    pseudo, _ = pseudonymize(tiny, KEY_A)
    assert pseudo["person_token"].is_unique


def test_vault_reverses_pseudonyms(tiny):
    pseudo, vault = pseudonymize(tiny, KEY_A)
    back = reidentify(pseudo["person_token"].iloc[[0]], vault)
    assert back["email"].iloc[0] == "ann.lee1@x.com"


def test_age_band_edges():
    assert age_band(18) == "18-29"
    assert age_band(29) == "18-29"
    assert age_band(30) == "30-39"
    assert age_band(70) == "70+"


def test_anonymize_meets_k_and_l(crowd):
    anon, stats = anonymize(crowd, k=3, l=2)
    assert stats["achieved_k"] >= 3
    assert stats["achieved_l"] >= 2
    for col in DIRECT_IDENTIFIERS:
        assert col not in anon.columns
    assert "age" not in anon.columns
    assert "zip_code" not in anon.columns


def test_anonymize_is_irreversible(crowd):
    anon, _ = anonymize(crowd, k=3, l=2)
    assert "name" not in anon.columns
    assert "email" not in anon.columns


def test_generalize_zip3(tiny):
    g = generalize(tiny)
    assert list(g["zip3"]) == ["100", "100", "100"]


def test_uniqueness_on_distinct_rows(tiny):
    assert uniqueness_rate(tiny) == 1.0
    assert min_k(tiny) == 1


def test_summarize_risk_keys(tiny):
    summary = summarize_risk(tiny)
    assert summary["n_records"] == 3
    assert summary["pct_unique"] == 100.0


def test_linkage_finds_unique_pseudo_rows(tiny):
    pseudo, _ = pseudonymize(tiny, KEY_A)
    voter = tiny[["name", "age", "zip_code", "gender"]]
    result = attack_pseudonymized(pseudo, voter)
    assert result["unique_links"] == 3


def test_anonymized_linkage_is_weaker_than_pseudo(crowd):
    pseudo, _ = pseudonymize(crowd, KEY_A)
    anon, _ = anonymize(crowd, k=3, l=2)
    voter = make_voter_list(crowd, coverage=1.0, seed=0)
    p = attack_pseudonymized(pseudo, voter)
    a = attack_anonymized(anon, voter)
    assert p["unique_links"] == 10
    assert a["unique_links"] == 0


def test_utility_keys(crowd):
    anon, _ = anonymize(crowd, k=2, l=2)
    util = compare_utility(crowd, anon)
    assert "salary_mape_pct" in util
    assert len(salary_by_age_band(crowd)) >= 1
