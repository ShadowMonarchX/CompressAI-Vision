from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


def test_compare_endpoint_returns_distinct_results():
    image = Image.new("RGB", (32, 32), (120, 80, 40))
    payload = BytesIO()
    image.save(payload, format="JPEG")
    payload.seek(0)

    response = TestClient(app).post(
        "/api/v1/compare/image",
        files={"file": ("sample.jpg", payload, "image/jpeg")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"ai", "baseline"}
    assert body["ai"]["params_used"] != body["baseline"]["params_used"]
