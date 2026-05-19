import pyodbc
import pandas as pd
import os

# =========================
# DATABASE CONNECTION
# =========================

server = 'YOUR_SERVER_NAME'
database = 'YOUR_DATABASE_NAME'
username = 'YOUR_USERNAME'
password = 'YOUR_PASSWORD'

# =========================
# CONNECT TO SQL SERVER
# =========================

print("Connecting to SQL Server...")

try:
    conn = pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'UID={username};'
        f'PWD={password};'
        f'TrustServerCertificate=yes;'
        f'ApplicationIntent=ReadOnly;'
    )
    print("✓ Connected successfully!")
except Exception as e:
    print(f"✗ Connection failed: {e}")
    print("\nCheck your credentials and server name!")
    exit()

# =========================
# CREATE FOLDER FOR CSV FILES
# =========================

folder_name = "database_backup_csv"

if not os.path.exists(folder_name):
    os.makedirs(folder_name)
    print(f"✓ Created folder: {folder_name}")

# =========================
# GET ALL TABLE NAMES
# =========================

tables_query = """
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
"""

try:
    tables = pd.read_sql(tables_query, conn)
    print(f"\n✓ Found {len(tables)} tables:")
    print(tables)
except Exception as e:
    print(f"✗ Failed to get tables: {e}")
    conn.close()
    exit()

# =========================
# EXPORT EACH TABLE TO CSV
# =========================

success_count = 0
failed_count = 0

for table in tables['TABLE_NAME']:
    
    # Validate table name (prevent SQL injection)
    if not str(table).isidentifier():
        print(f"\n⚠️  Skipping invalid table name: {table}")
        failed_count += 1
        continue
    
    try:
        print(f"\nExporting table: {table}")

        # Use parameterized query (safer)
        query = f"SELECT * FROM [{table}]"  # Table names can't be parameterized, but validation helps

        df = pd.read_sql(query, conn)

        csv_path = os.path.join(folder_name, f"{table}.csv")

        df.to_csv(csv_path, index=False)

        print(f"✓ Saved: {csv_path} ({len(df)} rows)")
        success_count += 1

    except Exception as e:
        print(f"✗ Could not export {table}")
        print(f"  Error: {e}")
        failed_count += 1

# =========================
# CLOSE CONNECTION
# =========================

conn.close()

print("\n" + "="*50)
print("EXPORT COMPLETE!")
print("="*50)
print(f"  ✓ Successfully exported: {success_count} tables")
print(f"  ✗ Failed: {failed_count} tables")
print(f"  📁 Files saved in: {folder_name}/")
print("  Original database was NOT modified.")
print("="*50)