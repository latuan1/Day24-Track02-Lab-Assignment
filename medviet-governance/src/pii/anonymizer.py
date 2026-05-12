import secrets

import pandas as pd
from faker import Faker
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from .detector import build_vietnamese_analyzer, detect_pii

fake = Faker("vi_VN")


def _fake_cccd() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(12))


def _fake_phone() -> str:
    prefix = secrets.choice(["03", "05", "07", "08", "09"])
    suffix = "".join(secrets.choice("0123456789") for _ in range(8))
    return f"{prefix}{suffix}"


def _unique_fake_values(
    generator,
    count: int,
    excluded_values=None,
    forbidden_substrings=None,
) -> list[str]:
    """Generate values that do not collide with raw PII or each other."""
    if excluded_values is None:
        excluded_values = []
    if forbidden_substrings is None:
        forbidden_substrings = []

    excluded = {str(value) for value in excluded_values if not pd.isna(value)}
    forbidden = {
        str(value)
        for value in forbidden_substrings
        if not pd.isna(value) and str(value).strip()
    }
    generated = set()
    values = []

    for _ in range(count):
        for _attempt in range(1000):
            value = str(generator())
            has_forbidden_part = any(part in value for part in forbidden)
            if value not in excluded and value not in generated and not has_forbidden_part:
                generated.add(value)
                values.append(value)
                break
        else:
            raise RuntimeError("Unable to generate a unique anonymized value")

    return values


class MedVietAnonymizer:

    def __init__(self):
        self.analyzer = build_vietnamese_analyzer()
        self.anonymizer = AnonymizerEngine()

    def anonymize_text(self, text: str, strategy: str = "replace") -> str:
        """
        Anonymize PII text with the selected strategy.

        Strategies:
        - replace: substitute fake values with Faker
        - mask: mask detected entities with "*"
        - hash: replace detected entities with SHA-256 hashes
        """
        if pd.isna(text):
            return text

        text = str(text)
        results = detect_pii(text, self.analyzer)
        if not results:
            return text

        if strategy == "replace":
            operators = {
                "PERSON": OperatorConfig("replace", {"new_value": fake.name()}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": fake.email()}),
                "VN_CCCD": OperatorConfig("replace", {"new_value": _fake_cccd()}),
                "VN_PHONE": OperatorConfig("replace", {"new_value": _fake_phone()}),
            }
        elif strategy == "mask":
            operators = {
                "DEFAULT": OperatorConfig(
                    "mask",
                    {
                        "masking_char": "*",
                        "chars_to_mask": 100,
                        "from_end": True,
                    },
                )
            }
        elif strategy == "hash":
            operators = {
                "DEFAULT": OperatorConfig("hash", {"hash_type": "sha256"})
            }
        else:
            raise ValueError(f"Unsupported anonymization strategy: {strategy}")

        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators,
        )
        return anonymized.text

    def anonymize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Anonymize PII columns while preserving non-PII training features.
        """
        df_anon = df.copy()
        row_count = len(df_anon)
        name_columns = [col for col in ["ho_ten", "bac_si_phu_trach"] if col in df_anon]
        raw_names = []
        for col in name_columns:
            raw_names.extend(df_anon[col].dropna().astype(str).tolist())

        if "ho_ten" in df_anon.columns:
            df_anon["ho_ten"] = _unique_fake_values(
                fake.name,
                row_count,
                raw_names,
                raw_names,
            )

        if "email" in df_anon.columns:
            df_anon["email"] = _unique_fake_values(
                fake.email,
                row_count,
                df_anon["email"],
            )

        if "bac_si_phu_trach" in df_anon.columns:
            df_anon["bac_si_phu_trach"] = _unique_fake_values(
                fake.name,
                row_count,
                raw_names,
                raw_names,
            )

        if "dia_chi" in df_anon.columns:
            forbidden_address_parts = raw_names
            for col in ["cccd", "so_dien_thoai", "email"]:
                if col in df_anon:
                    forbidden_address_parts.extend(df_anon[col].dropna().astype(str).tolist())

            df_anon["dia_chi"] = _unique_fake_values(
                fake.address,
                row_count,
                df_anon["dia_chi"],
                forbidden_address_parts,
            )

        if "cccd" in df_anon.columns:
            df_anon["cccd"] = _unique_fake_values(
                _fake_cccd,
                row_count,
                df_anon["cccd"],
            )

        if "so_dien_thoai" in df_anon.columns:
            df_anon["so_dien_thoai"] = _unique_fake_values(
                _fake_phone,
                row_count,
                df_anon["so_dien_thoai"],
            )

        return df_anon

    @staticmethod
    def _normalize_cell_for_detection(column: str, value) -> str:
        """Restore leading zeroes lost when CSV identifiers are read as numbers."""
        if pd.isna(value):
            return ""

        text = str(value).strip()
        if text.endswith(".0") and text[:-2].isdigit():
            text = text[:-2]

        if column == "cccd" and text.isdigit() and len(text) <= 12:
            return text.zfill(12)

        if (
            column == "so_dien_thoai"
            and text.isdigit()
            and len(text) == 9
            and text[0] in "35789"
        ):
            return f"0{text}"

        return text

    def calculate_detection_rate(
        self,
        original_df: pd.DataFrame,
        pii_columns: list,
    ) -> float:
        """
        Calculate the share of PII cells with at least one detected entity.
        """
        total = 0
        detected = 0

        for col in pii_columns:
            for value in original_df[col]:
                total += 1
                value = self._normalize_cell_for_detection(col, value)
                results = detect_pii(value, self.analyzer)
                if len(results) > 0:
                    detected += 1

        return detected / total if total > 0 else 0.0

if __name__ == "__main__":
    import pandas as pd

    df = pd.read_csv("data/raw/patients_raw.csv", dtype={"cccd": str, "so_dien_thoai": str})
    df_anon = MedVietAnonymizer().anonymize_dataframe(df)
    df_anon.to_csv("data/processed/patients_anonymized.csv", index=False)
    print(f"Wrote {len(df_anon)} anonymized rows")
