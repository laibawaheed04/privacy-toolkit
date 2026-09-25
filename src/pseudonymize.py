"""Step 4a: Pseudonymization.

Replace direct identifiers (name, email, phone) with a keyed token.

Pseudonymization is not anonymization:
  * Whoever holds the key (or the vault) can reverse it.
  * Quasi-identifiers (age, ZIP, gender) are left untouched, so records can
    still be linked to other datasets. That risk is measured in the linkage demo.

Usage (from the repo root):
    python src/pseudonymize.py

The secret key is read from the PSEUDO_KEY environment variable. If it is not
set, a random key is generated once and stored in secrets/pseudo.key
(git-ignored). Never commit the key or the vault.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

import pandas as pd

from paths import KEY_FILE, PSEUDO_CSV, RAW_CSV, SECRETS_DIR, VAULT_CSV, ensure_dirs

KEY_ENV = "PSEUDO_KEY"
TOKEN_LEN = 16
DIRECT_IDENTIFIERS = ["name", "email", "phone"]


def _normalize(value: str) -> str:
    """Same person -> same token, even if casing/spacing differs."""
    return str(value).strip().lower()


def sha256_hex(value: str) -> str:
    """Plain, unsalted hash. Shown here as the weak approach; do not use."""
    return hashlib.sha256(_normalize(value).encode()).hexdigest()


def load_key(create: bool = True) -> bytes:
    """Get the secret key: env var first, then key file, else generate one."""
    env = os.environ.get(KEY_ENV)
    if env:
        return env.encode()
    if KEY_FILE.exists():
        return bytes.fromhex(KEY_FILE.read_text().strip())
    if not create:
        raise RuntimeError(f"No key found. Set {KEY_ENV} or create {KEY_FILE}.")
    SECRETS_DIR.mkdir(exist_ok=True)
    key = secrets.token_bytes(32)
    KEY_FILE.write_text(key.hex())
    try:
        os.chmod(KEY_FILE, 0o600)
    except OSError:
        pass
    return key


def make_token(value: str, key: bytes) -> str:
    """Keyed pseudonym: HMAC-SHA256(key, value), truncated."""
    digest = hmac.new(key, _normalize(value).encode(), hashlib.sha256).hexdigest()
    return digest[:TOKEN_LEN]


def pseudonymize(df: pd.DataFrame, key: bytes, id_col: str = "email"):
    """Return (pseudonymized_df, vault_df).

    pseudonymized_df : no direct identifiers, one `person_token` per person.
    vault_df         : token -> original identifiers. Store separately.
    """
    tokens = df[id_col].map(lambda v: make_token(v, key))
    if tokens.nunique() != df[id_col].nunique():
        raise ValueError("Token collision detected. Increase TOKEN_LEN.")

    vault = pd.DataFrame({"person_token": tokens, "record_id": df["record_id"]})
    for col in DIRECT_IDENTIFIERS:
        vault[col] = df[col].values

    drop = [c for c in DIRECT_IDENTIFIERS + ["record_id"] if c in df.columns]
    pseudo = df.drop(columns=drop).copy()
    pseudo.insert(0, "person_token", tokens.values)
    return pseudo, vault


def reidentify(tokens, vault: pd.DataFrame) -> pd.DataFrame:
    """Reverse pseudonyms using the vault (only possible for its holder)."""
    return vault[vault["person_token"].isin(list(tokens))].copy()


def main() -> None:
    raw = pd.read_csv(RAW_CSV, dtype={"zip_code": str}, keep_default_na=False)
    key = load_key()
    pseudo, vault = pseudonymize(raw, key)

    ensure_dirs()
    pseudo.to_csv(PSEUDO_CSV, index=False)
    vault.to_csv(VAULT_CSV, index=False)

    print(f"Pseudonymized {len(pseudo)} records")
    print(f"  output : {PSEUDO_CSV}")
    print(f"  vault  : {VAULT_CSV}  (keep private, git-ignored)")
    print(f"  unique tokens: {pseudo['person_token'].nunique()}")
    print(pseudo.head(3).to_string())


if __name__ == "__main__":
    main()
