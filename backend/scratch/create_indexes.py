import sys
import os
import time

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import db_cursor

ddl_commands = [
    # 1. Add unique clustered indexes for primary key columns
    ("CLUSTERING dbo.TBl_mst_village(Village_Code)", 
     "CREATE UNIQUE CLUSTERED INDEX UX_TBl_mst_village_Code ON dbo.TBl_mst_village(Village_Code)"),
    
    ("CLUSTERING dbo.TBl_mst_taluka(Taluka_Code)", 
     "CREATE UNIQUE CLUSTERED INDEX UX_TBl_mst_taluka_Code ON dbo.TBl_mst_taluka(Taluka_Code)"),
    
    ("CLUSTERING dbo.Tbl_mst_sub_village(Subvillage_code)", 
     "CREATE UNIQUE CLUSTERED INDEX UX_Tbl_mst_sub_village_Code ON dbo.Tbl_mst_sub_village(Subvillage_code)"),
    
    ("CLUSTERING dbo.TBL_MST_MASTER(code)", 
     "CREATE UNIQUE CLUSTERED INDEX UX_TBL_MST_MASTER_code ON dbo.TBL_MST_MASTER(code)"),
    
    # 2. Add non-clustered indexes on foreign key join columns
    ("INDEX dbo.TBL_MST_MASTER(Village_code)", 
     "CREATE NONCLUSTERED INDEX IX_TBL_MST_MASTER_Village ON dbo.TBL_MST_MASTER(Village_code)"),
    
    ("INDEX dbo.TBL_MST_MASTER(Talula_Code)", 
     "CREATE NONCLUSTERED INDEX IX_TBL_MST_MASTER_Talula ON dbo.TBL_MST_MASTER(Talula_Code)"),
    
    ("INDEX dbo.TBL_MST_MASTER(Subvillage_code)", 
     "CREATE NONCLUSTERED INDEX IX_TBL_MST_MASTER_Subvillage ON dbo.TBL_MST_MASTER(Subvillage_code)"),
    
    ("INDEX dbo.TbL_TRN_Farmer_Meeting(farmer_code, created_at)", 
     "CREATE NONCLUSTERED INDEX IX_TbL_TRN_Farmer_Meeting_FarmerCode ON dbo.TbL_TRN_Farmer_Meeting(farmer_code, created_at)"),
]

with db_cursor() as cur:
    print("--- Creating Indexes ---")
    for label, sql in ddl_commands:
        start = time.time()
        try:
            cur.execute(sql)
            print(f"Success: {label} created in {time.time() - start:.4f} seconds")
        except Exception as e:
            print(f"Failed/Skipped: {label} - {e}")

print("\n--- Verifying Query Performance ---")
sql_combined = """
    SELECT m.code, m.NameE, m.MobileNumber, t.Taluka_NameE, v.Village_NameE, s.Subvillage_NameE
    FROM dbo.TBL_MST_MASTER m
    LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
    LEFT JOIN dbo.TBl_mst_taluka t ON t.Taluka_Code = m.Talula_Code
    LEFT JOIN dbo.Tbl_mst_sub_village s ON s.Subvillage_code = m.Subvillage_code
"""
start = time.time()
try:
    with db_cursor() as cur:
        cur.execute(sql_combined)
        rows = cur.fetchall()
        elapsed = time.time() - start
        print(f"Combined Query (NO group by): fetched {len(rows)} rows in {elapsed:.4f} seconds (previously 25.1s!)")
except Exception as e:
    print(f"Combined Query error: {e}")

sql_tracking = """
    SELECT
        m.code             AS farmer_id,
        ISNULL(m.NameE, '') AS farmer_name,
        ISNULL(m.MobileNumber, '') AS mobile,
        ISNULL(t.Taluka_NameE, '') AS taluka,
        ISNULL(v.Village_NameE, '') AS village,
        ISNULL(s.Subvillage_NameE, '') AS sub_village,
        COUNT(mtg.meeting_id) AS visit_count,
        MAX(CONVERT(VARCHAR, mtg.created_at, 23)) AS last_visit_date
    FROM dbo.TBL_MST_MASTER m
    LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
    LEFT JOIN dbo.TBl_mst_taluka t ON t.Taluka_Code = m.Talula_Code
    LEFT JOIN dbo.Tbl_mst_sub_village s ON s.Subvillage_code = m.Subvillage_code
    LEFT JOIN dbo.TbL_TRN_Farmer_Meeting mtg
        ON mtg.farmer_code = m.code
        AND CAST(mtg.created_at AS DATE) >= '2026-07-01'
    GROUP BY
        m.code, m.NameE, m.MobileNumber,
        t.Taluka_NameE, v.Village_NameE, s.Subvillage_NameE
"""
start = time.time()
try:
    with db_cursor() as cur:
        cur.execute(sql_tracking)
        rows = cur.fetchall()
        elapsed = time.time() - start
        print(f"Full Group By Query (Tracking): fetched {len(rows)} rows in {elapsed:.4f} seconds")
except Exception as e:
    print(f"Tracking Query error: {e}")
