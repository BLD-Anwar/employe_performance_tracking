from backend.database import db_cursor
with db_cursor() as cur:
    cur.execute("SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Tbl_mst_sub_village' AND COLUMN_NAME = 'Subvillage_code'")
    row = cur.fetchone()
    print("Type:", row[0] if row else "Not found")

    # While we are at it, let's just add the column if it doesn't exist
    cur.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'TBL_MST_MASTER' AND COLUMN_NAME = 'Subvillage_code'")
    if cur.fetchone()[0] == 0:
        print("Adding Subvillage_code to TBL_MST_MASTER...")
        cur.execute("ALTER TABLE dbo.TBL_MST_MASTER ADD Subvillage_code INT NULL")
        print("Column added successfully.")
    else:
        print("Column already exists.")
