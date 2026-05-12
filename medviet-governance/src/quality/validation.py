from pathlib import Path
from typing import Any

import pandas as pd

try:
    import great_expectations as gx
    from great_expectations.core.expectation_suite import ExpectationSuite
except ImportError:
    gx = None
    ExpectationSuite = Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "patients_raw.csv"
IMPORTANT_COLUMNS = [
    "patient_id",
    "cccd",
    "email",
    "benh",
    "ket_qua_xet_nghiem",
]
VALID_CONDITIONS = ["Tiểu đường", "Huyết áp cao", "Tim mạch", "Khỏe mạnh"]
EMAIL_REGEX = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"


def _read_patient_csv(filepath: str) -> pd.DataFrame:
    return pd.read_csv(
        filepath,
        dtype={
            "patient_id": str,
            "cccd": str,
            "so_dien_thoai": str,
            "email": str,
        },
    )


def _fail(results: dict, check_name: str) -> None:
    results["success"] = False
    results["failed_checks"].append(check_name)


def build_patient_expectation_suite() -> ExpectationSuite:
    """
    Tạo expectation suite cho anonymized patient data.
    """
    if gx is None:
        raise ImportError(
            "great_expectations is required to build the patient expectation suite."
        )

    context = gx.get_context()
    suite_name = "patient_data_suite"

    if hasattr(context, "add_or_update_expectation_suite"):
        suite = context.add_or_update_expectation_suite(
            expectation_suite_name=suite_name
        )
    else:
        suite = context.add_expectation_suite(suite_name)

    # Lấy validator
    df = _read_patient_csv(RAW_DATA_PATH)
    if hasattr(context.sources, "pandas_default"):
        pandas_datasource = context.sources.pandas_default
    else:
        pandas_datasource = context.sources.add_or_update_pandas("pandas_default")

    validator = pandas_datasource.read_dataframe(df)

    # 1. patient_id không được null
    validator.expect_column_values_to_not_be_null("patient_id")

    # 2. cccd phải có đúng 12 ký tự
    validator.expect_column_value_lengths_to_equal(
        column="cccd",
        value=12,
    )

    # 3. ket_qua_xet_nghiem phải trong khoảng [0, 50]
    validator.expect_column_values_to_be_between(
        column="ket_qua_xet_nghiem",
        min_value=0,
        max_value=50,
    )

    # 4. benh phải thuộc danh sách hợp lệ
    validator.expect_column_values_to_be_in_set(
        column="benh",
        value_set=VALID_CONDITIONS,
    )

    # 5. email phải match regex pattern
    validator.expect_column_values_to_match_regex(
        column="email",
        regex=EMAIL_REGEX,
    )

    # 6. Không được có duplicate patient_id
    validator.expect_column_values_to_be_unique(column="patient_id")

    if hasattr(validator, "expectation_suite"):
        expectation_suite = validator.expectation_suite
        if hasattr(expectation_suite, "expectation_suite_name"):
            expectation_suite.expectation_suite_name = suite_name
        elif hasattr(expectation_suite, "name"):
            expectation_suite.name = suite_name

    validator.save_expectation_suite(discard_failed_expectations=False)
    if hasattr(validator, "get_expectation_suite"):
        return validator.get_expectation_suite()

    return suite


def validate_anonymized_data(filepath: str) -> dict:
    """
    Validate anonymized data.
    Trả về dict: {"success": bool, "failed_checks": list, "stats": dict}
    """
    df = _read_patient_csv(filepath)
    original_df = _read_patient_csv(RAW_DATA_PATH)
    results = {
        "success": True,
        "failed_checks": [],
        "stats": {
            "total_rows": len(df),
            "original_rows": len(original_df),
            "columns": list(df.columns),
        },
    }

    # Check 1: Không còn CCCD gốc dạng số thuần túy
    # (sau anonymization, cccd phải là fake hoặc masked)
    if "cccd" not in df.columns:
        _fail(results, "missing_cccd_column")
        results["stats"]["leaked_original_cccd_count"] = None
    else:
        original_cccd = set(original_df["cccd"].dropna().astype(str))
        anonymized_cccd = set(df["cccd"].dropna().astype(str))
        leaked_cccd = sorted(original_cccd.intersection(anonymized_cccd))
        results["stats"]["leaked_original_cccd_count"] = len(leaked_cccd)
        results["stats"]["leaked_original_cccd_samples"] = leaked_cccd[:5]

        if leaked_cccd:
            _fail(results, "original_cccd_still_present")

    # Check 2: Không có null values trong các cột quan trọng
    missing_columns = [col for col in IMPORTANT_COLUMNS if col not in df.columns]
    if missing_columns:
        _fail(results, "missing_important_columns")

    present_columns = [col for col in IMPORTANT_COLUMNS if col in df.columns]
    null_counts = {
        col: int(count)
        for col, count in df[present_columns].isna().sum().items()
        if count > 0
    }
    results["stats"]["null_counts"] = null_counts

    if null_counts:
        _fail(results, "null_values_in_important_columns")

    # Check 3: Số rows phải bằng original
    if len(df) != len(original_df):
        _fail(results, "row_count_mismatch")

    return results

if __name__ == "__main__":
    validation_results = validate_anonymized_data(
        filepath=PROJECT_ROOT / "data" / "processed" / "patients_anonymized.csv"
    )
    print(validation_results)
