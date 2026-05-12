import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.encryption.vault import SimpleVault


def test_envelope_encryption_round_trip(tmp_path):
    vault = SimpleVault(master_key_path=str(tmp_path / ".vault_key"))
    original = "Nguyen Van A - CCCD: 012345678901"

    encrypted = vault.encrypt_data(original)
    assert encrypted["algorithm"] == "AES-256-GCM"
    assert encrypted["ciphertext"] != original

    decrypted = vault.decrypt_data(encrypted)
    assert decrypted == original


def test_encrypt_column_replaces_plaintext_values(tmp_path):
    vault = SimpleVault(master_key_path=str(tmp_path / ".vault_key"))
    df = pd.DataFrame({"cccd": ["012345678901", "987654321000"]})

    encrypted_df = vault.encrypt_column(df, "cccd")

    for original_value in df["cccd"]:
        assert original_value not in encrypted_df["cccd"].to_string()
