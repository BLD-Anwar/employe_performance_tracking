import sys
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Ensure trial/backend and trial/ are in sys.path
sys.path.insert(0, r"c:\Users\anwar\Downloads\agripulse-v2-structure (3)\trial")
sys.path.insert(0, r"c:\Users\anwar\Downloads\agripulse-v2-structure (3)\trial\backend")

from auth import create_access_token
from main import app

# We will monkeypatch utils.report_generator functions to raise errors
import utils.report_generator

def mock_raise_error(*args, **kwargs):
    raise RuntimeError("Sensitive Database Connection String details: user=admin, pwd=secret123!")

def run_tests():
    print("Starting report error masking validation tests...")
    
    # 1. Monkeypatch generators
    utils.report_generator.generate_task_report = mock_raise_error
    utils.report_generator.check_and_generate_eligible_reports = mock_raise_error

    client = TestClient(app)
    manager_token = create_access_token(user_id=1, role="manager")
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    # Test endpoint 1: /api/reports/generate-task-report
    print("Testing GET/POST /api/reports/generate-task-report with forced exception...")
    res = client.post("/api/reports/generate-task-report?task_id=9999", headers=manager_headers)
    
    assert res.status_code == 500
    assert "detail" in res.json()
    detail = res.json()["detail"]
    print("Received detail response:", detail)
    assert detail == "Report generation failed. Please try again."
    assert "Sensitive Database Connection String" not in detail
    print("Pass: generate-task-report masked the exception correctly.")

    # Test endpoint 2: /api/reports/generate-all
    print("Testing GET/POST /api/reports/generate-all with forced exception...")
    res = client.post("/api/reports/generate-all", headers=manager_headers)
    
    assert res.status_code == 500
    assert "detail" in res.json()
    detail = res.json()["detail"]
    print("Received detail response:", detail)
    assert detail == "Report generation failed. Please try again."
    assert "Sensitive Database Connection String" not in detail
    print("Pass: generate-all masked the exception correctly.")

    print("\nAll report error masking tests passed successfully!")

if __name__ == "__main__":
    run_tests()
