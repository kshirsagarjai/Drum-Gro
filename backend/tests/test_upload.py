from fastapi.testclient import TestClient
from app.main import app
from io import BytesIO

client = TestClient(app)

def test_valid_upload():
    fake_audio = BytesIO(b"fake audio data")
    response = client.post(
        "/api/upload",
        files={"file": ("test.wav", fake_audio, "audio/wav")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data
    assert data["status"] == "pending"

def test_invalid_extension():
    fake_file = BytesIO(b"hello")
    response = client.post(
        "/api/upload",
        files={"file": ("test.txt", fake_file, "text/plain")}
    )
    assert response.status_code == 400
