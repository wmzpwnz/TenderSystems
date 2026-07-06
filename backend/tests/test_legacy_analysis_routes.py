from fastapi.testclient import TestClient

from app.main import app


def test_legacy_tender_analysis_endpoints_are_removed():
    client = TestClient(app)

    quick_response = client.post("/api/v1/tenders/1/analyze")
    deep_response = client.post("/api/v1/tenders/1/deep-analyze")

    assert quick_response.status_code in {404, 405}
    assert deep_response.status_code in {404, 405}
