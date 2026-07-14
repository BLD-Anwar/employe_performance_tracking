import sys
import os

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import db_cursor

tables = ['TBL_MST_MASTER', 'TBl_mst_village', 'TBl_mst_taluka', 'Tbl_mst_sub_village', 'TbL_TRN_Farmer_Meeting']

with db_cursor() as cur:
    for t in tables:
        print(f"\nIndexes for {t}:")
        try:
            cur.execute(f"EXEC sp_helpindex 'dbo.{t}'")
            rows = cur.fetchall()
            for r in rows:
                print(f"  Index Name: {r[0]} | Description: {r[1]} | Keys: {r[2]}")
        except Exception as e:
            print(f"  Error/No index: {e}")
