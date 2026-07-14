import sys
import io
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Ensure trial/backend and trial/ are in sys.path
sys.path.insert(0, r"c:\Users\anwar\Downloads\agripulse-v2-structure (3)\trial")
sys.path.insert(0, r"c:\Users\anwar\Downloads\agripulse-v2-structure (3)\trial\backend")

from auth import create_access_token
from main import app

def run_tests():
    print("Starting upload validation tests...")
    client = TestClient(app)

    manager_token = create_access_token(user_id=1, role="manager")
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    # Test Case 1: Valid image file under 5MB -> 200 Success
    print("Testing Case 1: Valid small PNG image...")
    file_content = b"fake-png-content-bytes-here"
    files = {"file": ("test.png", file_content, "image/png")}
    res = client.post("/api/meetings/upload-photo?user_id=2", files=files, headers=manager_headers)
    assert res.status_code == 200
    assert res.json()["ok"] is True
    print("Pass: Valid image successfully accepted.")

    # Test Case 2: Invalid file extension (e.g. .txt) -> 400
    print("Testing Case 2: Invalid text file (.txt)...")
    files = {"file": ("test.txt", b"plain text content", "text/plain")}
    res = client.post("/api/meetings/upload-photo?user_id=2", files=files, headers=manager_headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "Only image files allowed"
    print("Pass: Rejected .txt extension with HTTP 400.")

    # Test Case 3: Oversized image file (>5MB) -> 413
    print("Testing Case 3: Oversized PNG image (6MB)...")
    large_content = b"x" * (6 * 1024 * 1024) # 6MB
    files = {"file": ("large.png", large_content, "image/png")}
    res = client.post("/api/meetings/upload-photo?user_id=2", files=files, headers=manager_headers)
    assert res.status_code == 413
    assert "File too large" in res.json()["detail"]
    print("Pass: Rejected 6MB file with HTTP 413.")

    print("\nAll upload validation tests passed successfully!")

if __name__ == "__main__":
    run_tests()
