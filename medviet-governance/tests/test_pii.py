import sys
from pathlib import Path

import pandas as pd
from pandas.testing import assert_series_equal
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.pii.anonymizer import MedVietAnonymizer


PII_COLUMNS = ["ho_ten", "cccd", "so_dien_thoai", "email"]
NON_PII_COLUMNS = ["patient_id", "benh", "ket_qua_xet_nghiem"]


def _dataframe_text(df: pd.DataFrame) -> str:
    return df.astype(str).to_csv(index=False)


@pytest.fixture
def anonymizer():
    return MedVietAnonymizer()


@pytest.fixture
def sample_df():
    return pd.read_csv(
        PROJECT_ROOT / "data" / "raw" / "patients_raw.csv",
        dtype={"patient_id": str, "cccd": str, "so_dien_thoai": str},
    ).head(50)


class TestPIIDetection:

    def test_cccd_detected(self, anonymizer):
        text = "Benh nhan Nguyen Van A, CCCD: 012345678901"
        results = anonymizer.analyzer.analyze(
            text=text,
            language="vi",
            entities=["VN_CCCD"],
        )
        assert any(result.entity_type == "VN_CCCD" for result in results)

    def test_phone_detected(self, anonymizer):
        text = "Lien he: 0912345678"
        results = anonymizer.analyzer.analyze(
            text=text,
            language="vi",
            entities=["VN_PHONE"],
        )
        assert any(result.entity_type == "VN_PHONE" for result in results)

    def test_email_detected(self, anonymizer):
        text = "Email: nguyenvana@gmail.com"
        results = anonymizer.analyzer.analyze(
            text=text,
            language="vi",
            entities=["EMAIL_ADDRESS"],
        )
        assert any(result.entity_type == "EMAIL_ADDRESS" for result in results)

    def test_detection_rate_above_95_percent(self, anonymizer, sample_df):
        """Pipeline must reach >95% detection rate."""
        rate = anonymizer.calculate_detection_rate(sample_df, PII_COLUMNS)
        print(f"\nDetection rate: {rate:.2%}")
        assert rate >= 0.95, f"Detection rate {rate:.2%} < 95%"


class TestAnonymization:

    def test_pii_not_in_output(self, anonymizer, sample_df):
        """Original PII values must not survive anonymization."""
        df_anon = anonymizer.anonymize_dataframe(sample_df)
        anonymized_text = _dataframe_text(df_anon)

        for column in PII_COLUMNS:
            for original_value in sample_df[column].dropna().astype(str):
                assert original_value not in anonymized_text

    def test_non_pii_columns_unchanged(self, anonymizer, sample_df):
        """Training-safe columns must be preserved exactly."""
        df_anon = anonymizer.anonymize_dataframe(sample_df)
        for column in NON_PII_COLUMNS:
            assert_series_equal(
                sample_df[column].reset_index(drop=True),
                df_anon[column].reset_index(drop=True),
                check_names=False,
            )

    def test_processed_file_contains_no_original_pii(self, sample_df):
        """Generated deliverable should not leak original raw PII."""
        processed_path = PROJECT_ROOT / "data" / "processed" / "patients_anonymized.csv"
        df_anon = pd.read_csv(
            processed_path,
            dtype={"patient_id": str, "cccd": str, "so_dien_thoai": str},
        )
        anonymized_text = _dataframe_text(df_anon)

        for column in PII_COLUMNS:
            for original_value in sample_df[column].dropna().astype(str):
                assert original_value not in anonymized_text
