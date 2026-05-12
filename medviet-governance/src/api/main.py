import json
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI

from src.access.rbac import get_current_user, require_permission
from src.pii.anonymizer import MedVietAnonymizer


app = FastAPI(title="MedViet Data API", version="1.0.0")
anonymizer = MedVietAnonymizer()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_PATIENTS_PATH = PROJECT_ROOT / "data" / "raw" / "patients_raw.csv"


def _load_patients() -> pd.DataFrame:
    return pd.read_csv(
        RAW_PATIENTS_PATH,
        dtype={
            "patient_id": str,
            "cccd": str,
            "so_dien_thoai": str,
        },
    )


def _to_records(df: pd.DataFrame) -> list:
    return json.loads(df.to_json(orient="records", force_ascii=False))


@app.get("/api/patients/raw")
@require_permission(resource="patient_data", action="read")
async def get_raw_patients(current_user: dict = Depends(get_current_user)):
    """Return the first 10 raw patient records. Only admin can read raw PII."""
    df = _load_patients()
    return {"records": _to_records(df.head(10))}


@app.get("/api/patients/anonymized")
@require_permission(resource="training_data", action="read")
async def get_anonymized_patients(current_user: dict = Depends(get_current_user)):
    """Return anonymized patient records for training use."""
    df = _load_patients()
    df_anon = anonymizer.anonymize_dataframe(df)
    return {"records": _to_records(df_anon)}


@app.get("/api/metrics/aggregated")
@require_permission(resource="aggregated_metrics", action="read")
async def get_aggregated_metrics(current_user: dict = Depends(get_current_user)):
    """Return non-PII aggregated patient metrics."""
    df = _load_patients()
    counts = (
        df.groupby("benh", dropna=False)
        .size()
        .reset_index(name="patient_count")
        .sort_values("patient_count", ascending=False)
    )
    return {
        "total_patients": int(len(df)),
        "patients_by_disease": _to_records(counts),
    }


@app.delete("/api/patients/{patient_id}")
@require_permission(resource="patient_data", action="delete")
async def delete_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Simulate patient deletion. RBAC restricts this route to admin."""
    return {
        "status": "deleted",
        "patient_id": patient_id,
        "deleted_by": current_user["username"],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedViet Data API"}
