import sys
from fastapi.testclient import TestClient

# Ensure trial/backend and trial/ are in sys.path
sys.path.insert(0, r"c:\Users\anwar\Downloads\agripulse-v2-structure (3)\trial")
sys.path.insert(0, r"c:\Users\anwar\Downloads\agripulse-v2-structure (3)\trial\backend")

from main import app

def run_tests():
    print("Starting CORS policy validation tests...")
    client = TestClient(app)

    # Test Case 1: Preflight from allowed origin
    print("Testing Preflight from allowed origin: http://localhost:3000...")
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    }
    res = client.options("/api/meta/status", headers=headers)
    print("Preflight response status:", res.status_code)
    print("Preflight response headers:", dict(res.headers))
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-credentials" not in res.headers or res.headers.get("access-control-allow-credentials") == "false"
    print("Pass: Preflight accepted with correct headers.")

    # Test Case 2: Preflight from disallowed origin
    print("Testing Preflight from disallowed origin: http://evil.com...")
    headers = {
        "Origin": "http://evil.com",
        "Access-Control-Request-Method": "GET",
    }
    res = client.options("/api/meta/status", headers=headers)
    print("Preflight evil response status:", res.status_code)
    print("Preflight evil response headers:", dict(res.headers))
    assert "access-control-allow-origin" not in res.headers
    print("Pass: Rejected CORS headers from unauthorized origin.")

    print("\nAll CORS validation tests passed successfully!")

if __name__ == "__main__":
    run_tests()
