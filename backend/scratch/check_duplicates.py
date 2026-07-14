import sys
import os

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import db_cursor

checks = [
    ('TBL_MST_MASTER', 'code'),
    ('TBl_mst_village', 'Village_Code'),
    ('TBl_mst_taluka', 'Taluka_Code'),
    ('Tbl_mst_sub_village', 'Subvillage_code'),
]

with db_cursor() as cur:
    for table, col in checks:
        cur.execute(f"SELECT COUNT(*), COUNT(DISTINCT {col}) FROM dbo.{table}")
        total, distinct = cur.fetchone()
        print(f"Table: {table:<25} | Column: {col:<16} | Total Rows: {total:<6} | Distinct: {distinct:<6} | Has Duplicates: {total != distinct}")
