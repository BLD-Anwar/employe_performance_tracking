import sys
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Ensure trial/backend and trial/ are in sys.path
sys.path.insert(0, r"c:\Users\anwar\Downloads\agripulse-v2-structure (3)\trial")
sys.path.insert(0, r"c:\Users\anwar\Downloads\agripulse-v2-structure (3)\trial\backend")

from auth import create_access_token
from main import app

def run_tests():
    print("Starting meeting authorization tests...")
    client = TestClient(app)

    # 1. Generate tokens
    manager_token = create_access_token(user_id=1, role="manager")
    officer2_token = create_access_token(user_id=2, role="officer")
    officer3_token = create_access_token(user_id=3, role="officer")

    manager_headers = {"Authorization": f"Bearer {manager_token}"}
    officer2_headers = {"Authorization": f"Bearer {officer2_token}"}
    officer3_headers = {"Authorization": f"Bearer {officer3_token}"}

    # Test GET /my/{employee_id}
    # Case A: Officer 2 querying officer 2's meetings -> 200 (Success)
    print("Testing GET /my/2 as Officer 2 (Owner)...")
    res = client.get("/api/meetings/my/2", headers=officer2_headers)
    assert res.status_code == 200
    print("Pass: Allowed ownership access.")

    # Case B: Officer 3 querying officer 2's meetings -> 403 (Forbidden)
    print("Testing GET /my/2 as Officer 3 (Non-owner)...")
    res = client.get("/api/meetings/my/2", headers=officer3_headers)
    assert res.status_code == 403
    assert res.json()["detail"] == "Access denied"
    print("Pass: Blocked unauthorized ownership access with 403.")

    # Case C: Manager querying officer 2's meetings -> 200 (Success)
    print("Testing GET /my/2 as Manager...")
    res = client.get("/api/meetings/my/2", headers=manager_headers)
    assert res.status_code == 200
    print("Pass: Allowed manager access to officer meetings.")

    # Test GET /check/{employee_id}/{farmer_code}
    # Case A: Officer 2 checking combo -> 200
    print("Testing GET /check/2/1 as Officer 2 (Owner)...")
    res = client.get("/api/meetings/check/2/1", headers=officer2_headers)
    assert res.status_code == 200
    print("Pass: Officer allowed to check own farmer combo.")

    # Case B: Manager checking combo -> 200
    print("Testing GET /check/2/1 as Manager...")
    res = client.get("/api/meetings/check/2/1", headers=manager_headers)
    assert res.status_code == 200
    print("Pass: Manager allowed to check farmer combo.")

    # Case C: Officer 3 checking Officer 2's combo -> 403
    print("Testing GET /check/2/1 as Officer 3 (Non-owner)...")
    res = client.get("/api/meetings/check/2/1", headers=officer3_headers)
    assert res.status_code == 403
    assert res.json()["detail"] == "Access denied"
    print("Pass: Blocked unauthorized ownership check with 403.")

    # Test Manager-Only Endpoints
    # Case A: Officer 2 fetching all meetings -> 403
    print("Testing GET /api/meetings as Officer 2 (Manager-only route)...")
    res = client.get("/api/meetings", headers=officer2_headers)
    assert res.status_code == 403
    assert "Insufficient permissions" in res.json()["detail"]
    print("Pass: Officer blocked from manager-only list endpoint.")

    # Case B: Manager fetching all meetings -> 200
    print("Testing GET /api/meetings as Manager...")
    res = client.get("/api/meetings", headers=manager_headers)
    assert res.status_code == 200
    print("Pass: Manager allowed to list all meetings.")

    # Case C: Officer 2 getting single meeting detail -> 403
    print("Testing GET /api/meetings/1 as Officer 2 (Manager-only detail)...")
    res = client.get("/api/meetings/1", headers=officer2_headers)
    assert res.status_code == 403
    assert "Insufficient permissions" in res.json()["detail"]
    print("Pass: Officer blocked from single meeting detail.")

    print("\nAll meeting authorization tests passed successfully!")

if __name__ == "__main__":
    run_tests()
