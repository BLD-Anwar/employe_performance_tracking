import sys
import os

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import db_cursor

columns_to_check = [
    ('TBL_MST_MASTER', 'Village_code'),
    ('TBL_MST_MASTER', 'Talula_Code'),
    ('TBL_MST_MASTER', 'Subvillage_code'),
    ('TBL_MST_MASTER', 'code'),
    ('TBl_mst_village', 'Village_Code'),
    ('TBl_mst_taluka', 'Taluka_Code'),
    ('Tbl_mst_sub_village', 'Subvillage_code'),
    ('TbL_TRN_Farmer_Meeting', 'farmer_code'),
]

sql = """
    SELECT 
        TABLE_NAME, 
        COLUMN_NAME, 
        DATA_TYPE, 
        CHARACTER_MAXIMUM_LENGTH,
        COLLATION_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = ? AND COLUMN_NAME = ?
"""

with db_cursor() as cur:
    print("--- Detailed Column Datatypes ---")
    for tbl, col in columns_to_check:
        cur.execute(sql, (tbl, col))
        row = cur.fetchone()
        if row:
            print(f"Table: {row[0]:<25} | Column: {row[1]:<16} | Type: {row[2]:<8} | Length: {str(row[3]):<5} | Collation: {row[4]}")
        else:
            print(f"Table: {tbl:<25} | Column: {col:<16} | NOT FOUND")
