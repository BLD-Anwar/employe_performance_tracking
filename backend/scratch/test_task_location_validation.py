import os
import sys
from fastapi import HTTPException

# Ensure trial/backend is in path
sys.path.insert(0, r"c:\Users\anwar\Downloads\agripulse-v2-structure (3)\trial\backend")

from database import db_cursor
from routers.tasks import update_task, EditTaskRequest

def run_tests():
    print("Starting task location change validation tests...")

    # We will test using task_id = 1 (we will roll back any actual database updates)
    task_id = 1

    # Fetch current state of task 1 to verify we restore or rollback
    with db_cursor() as cur:
        cur.execute("SELECT task_name, work_type, priority, start_date, end_date, status, remarks FROM TASK_MASTER WHERE task_id = ?", task_id)
        original_master = cur.fetchone()
        cur.execute("SELECT taluka_code, village_code, subvillage_code FROM TASK_LOCATION WHERE task_id = ?", task_id)
        original_loc = cur.fetchone()
        cur.execute("SELECT farmer_id FROM TASK_FARMER_MAPPING WHERE task_id = ?", task_id)
        original_farmers = [r[0] for r in cur.fetchall()]

    print(f"Original task: {original_master[0]}, village: {original_loc[1]}, farmers: {original_farmers}")

    # Farmer ID 1 is in "Pirachi Kuroli"
    # Farmer ID 3 is in "Mahalung"
    # Farmer ID 4 is in "Atpadi"

    # Test Case 1: Change location to "Mahalung", but pass Farmer 1 (which is in "Pirachi Kuroli")
    # This should fail validation!
    body_fail = EditTaskRequest(
        task_name="Test Assignment Location Validation",
        work_type_name="Other",
        priority="Medium",
        start_date="2026-06-06",
        end_date="2026-06-09",
        schedule_type="WEEKLY",
        status="ASSIGNED",
        remarks="Test fail path",
        district="Sangola",
        village="Mahalung",
        sub_village="",
        farmers=[1, 3], # Farmer 1 is mismatched (in Pirachi Kuroli, not Mahalung)
        manager_id=1
    )

    print("Testing: Changing location to 'Mahalung' with mismatched Farmer 1...")
    try:
        update_task(task_id=task_id, body=body_fail)
        assert False, "Expected HTTPException(400) due to mismatched farmer village"
    except HTTPException as e:
        assert e.status_code == 400
        assert "farmers are not in the selected village" in e.detail["message"]
        assert 1 in e.detail["mismatched_farmer_ids"]
        print("Pass: Correctly rejected with HTTP 400 and mismatched farmer list:", e.detail["mismatched_farmer_ids"])

    # Test Case 2: Change location to "Mahalung" and pass ONLY Farmer 3 (which is in "Mahalung")
    # This should succeed!
    body_success = EditTaskRequest(
        task_name="Test Assignment Location Validation Success",
        work_type_name="Other",
        priority="Medium",
        start_date="2026-06-06",
        end_date="2026-06-09",
        schedule_type="WEEKLY",
        status="ASSIGNED",
        remarks="Test success path",
        district="Sangola",
        village="Mahalung",
        sub_village="",
        farmers=[3], # Farmer 3 is in Mahalung, should succeed!
        manager_id=1
    )

    print("Testing: Changing location to 'Mahalung' with matching Farmer 3...")
    try:
        # Wrap in a manual transaction rollback or restore afterwards
        res = update_task(task_id=task_id, body=body_success)
        assert res["success"] is True
        print("Pass: Successfully updated task with matching farmers.")
        
        # Verify the database was updated
        with db_cursor() as cur:
            cur.execute("SELECT village_code FROM TASK_LOCATION WHERE task_id = ?", task_id)
            db_village = cur.fetchone()[0]
            assert db_village == "Mahalung"
            cur.execute("SELECT farmer_id FROM TASK_FARMER_MAPPING WHERE task_id = ?", task_id)
            db_farmers = [r[0] for r in cur.fetchall()]
            assert db_farmers == [3]
            print("Pass: Database successfully reflects new village and farmer mapping.")
            
    except Exception as e:
        print("Fail: Test Case 2 encountered an error:", e)
        raise e
    finally:
        # Restore the original state to keep database clean
        print("Restoring original task state...")
        with db_cursor() as cur:
            cur.execute("""
                UPDATE TASK_MASTER
                SET task_name = ?, work_type = ?, priority = ?, start_date = ?, end_date = ?, status = ?, remarks = ?
                WHERE task_id = ?
            """, original_master[0], original_master[1], original_master[2], original_master[3], original_master[4], original_master[5], original_master[6], task_id)
            cur.execute("""
                UPDATE TASK_LOCATION
                SET taluka_code = ?, village_code = ?, subvillage_code = ?
                WHERE task_id = ?
            """, original_loc[0], original_loc[1], original_loc[2], task_id)
            cur.execute("DELETE FROM TASK_FARMER_MAPPING WHERE task_id = ?", task_id)
            for fid in original_farmers:
                cur.execute("INSERT INTO TASK_FARMER_MAPPING (task_id, farmer_id, status) VALUES (?, ?, 'PENDING')", task_id, fid)
        print("Restore complete.")

    print("\nAll task location validation tests passed successfully!")

if __name__ == "__main__":
    run_tests()
