"""Shared filesystem locations. Every script in src/ imports this."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
SECRETS_DIR = ROOT / "secrets"
NOTEBOOKS_DIR = ROOT / "notebooks"

RAW_CSV = DATA_DIR / "raw_data.csv"
PSEUDO_CSV = DATA_DIR / "pseudonymized.csv"
ANON_CSV = DATA_DIR / "anonymized.csv"
VOTER_CSV = DATA_DIR / "voter_list.csv"
VAULT_CSV = SECRETS_DIR / "vault.csv"
KEY_FILE = SECRETS_DIR / "pseudo.key"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)
    SECRETS_DIR.mkdir(exist_ok=True)
