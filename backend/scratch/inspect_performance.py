import time
import sys
import os

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import db_cursor

def time_query(label, sql, params=None):
    if params is None:
        params = []
    start = time.time()
    try:
        with db_cursor() as cur:
            cur.execute(sql, *params)
            rows = cur.fetchall()
            elapsed = time.time() - start
            print(f"{label}: fetched {len(rows)} rows in {elapsed:.4f} seconds")
            return elapsed
    except Exception as e:
        print(f"{label}: Error: {e}")
        return None

print("--- Benchmarking Queries ---")

# 1. Base query (no joins)
time_query("1. Base TBL_MST_MASTER (no joins)", "SELECT code, NameE, MobileNumber, Village_code, Talula_Code, Subvillage_code FROM dbo.TBL_MST_MASTER")

# 2. Join Village
time_query("2. With Village join", """
    SELECT m.code, v.Village_NameE
    FROM dbo.TBL_MST_MASTER m
    LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
""")

# 3. Join Taluka
time_query("3. With Taluka join", """
    SELECT m.code, t.Taluka_NameE
    FROM dbo.TBL_MST_MASTER m
    LEFT JOIN dbo.TBl_mst_taluka t ON t.Taluka_Code = m.Talula_Code
""")

# 4. Join Subvillage
time_query("4. With Subvillage join", """
    SELECT m.code, s.Subvillage_NameE
    FROM dbo.TBL_MST_MASTER m
    LEFT JOIN dbo.Tbl_mst_sub_village s ON s.Subvillage_code = m.Subvillage_code
""")

# 5. Join Meetings (grouped)
time_query("5. With Meetings join (grouped)", """
    SELECT m.code, COUNT(mtg.meeting_id)
    FROM dbo.TBL_MST_MASTER m
    LEFT JOIN dbo.TbL_TRN_Farmer_Meeting mtg ON mtg.farmer_code = m.code AND CAST(mtg.created_at AS DATE) >= '2026-07-01'
    GROUP BY m.code
""")

# 6. Combined without grouping
time_query("6. Combined (all joins, NO group by)", """
    SELECT m.code, m.NameE, m.MobileNumber, t.Taluka_NameE, v.Village_NameE, s.Subvillage_NameE
    FROM dbo.TBL_MST_MASTER m
    LEFT JOIN dbo.TBl_mst_village v ON v.Village_Code = m.Village_code
    LEFT JOIN dbo.TBl_mst_taluka t ON t.Taluka_Code = m.Talula_Code
    LEFT JOIN dbo.Tbl_mst_sub_village s ON s.Subvillage_code = m.Subvillage_code
""")

# 7. Index information
print("\n--- Listing Indexes ---")
sql_indexes = """
    SELECT 
        t.name AS TableName,
        ind.name AS IndexName,
        col.name AS ColumnName
    FROM 
        sys.indexes ind 
    INNER JOIN 
        sys.index_columns ic ON  ind.object_id = ic.object_id and ind.index_id = ic.index_id 
    INNER JOIN 
        sys.columns col ON ic.object_id = col.object_id and ic.column_id = col.column_id 
    INNER JOIN 
        sys.tables t ON ind.object_id = t.object_id 
    WHERE 
        t.name IN ('TBL_MST_MASTER', 'TBl_mst_village', 'TBl_mst_taluka', 'Tbl_mst_sub_village', 'TbL_TRN_Farmer_Meeting')
    ORDER BY 
        t.name, ind.name, ic.index_column_id
"""
with db_cursor() as cur:
    try:
        cur.execute(sql_indexes)
        for row in cur.fetchall():
            print(f"Table: {row[0]} | Index: {row[1]} | Column: {row[2]}")
    except Exception as e:
        print("Error listing indexes:", e)
