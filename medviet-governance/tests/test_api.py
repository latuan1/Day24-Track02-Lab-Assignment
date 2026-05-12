import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.api.main import app


client = TestClient(app)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_raw_patients_requires_admin():
    assert client.get("/api/patients/raw").status_code == 401
    assert client.get("/api/patients/raw", headers=_auth("token-bob")).status_code == 403

    response = client.get("/api/patients/raw", headers=_auth("token-alice"))
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["records"]) == 10
    assert {"patient_id", "ho_ten", "cccd", "email"}.issubset(payload["records"][0])


def test_training_data_access_is_limited_to_admin_and_ml_engineer():
    response = client.get("/api/patients/anonymized", headers=_auth("token-bob"))
    assert response.status_code == 200
    assert len(response.json()["records"]) > 0

    assert (
        client.get("/api/patients/anonymized", headers=_auth("token-alice")).status_code
        == 200
    )
    assert (
        client.get("/api/patients/anonymized", headers=_auth("token-carol")).status_code
        == 403
    )
    assert (
        client.get("/api/patients/anonymized", headers=_auth("token-dave")).status_code
        == 403
    )


def test_aggregated_metrics_are_non_pii_and_role_limited():
    for token in ["token-alice", "token-bob", "token-carol"]:
        response = client.get("/api/metrics/aggregated", headers=_auth(token))
        assert response.status_code == 200
        payload = response.json()
        assert payload["total_patients"] > 0
        assert "patients_by_disease" in payload

    assert client.get("/api/metrics/aggregated", headers=_auth("token-dave")).status_code == 403


def test_delete_patient_requires_admin():
    assert (
        client.delete("/api/patients/abc123", headers=_auth("token-bob")).status_code
        == 403
    )

    response = client.delete("/api/patients/abc123", headers=_auth("token-alice"))
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
