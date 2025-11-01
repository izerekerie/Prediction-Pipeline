import pymysql

HOST="sql3.freesqldatabase.com"; PORT=3306
DB="sql3805058"; USER="sql3805058"; PWD="wBhIUnhTBQ"

conn = pymysql.connect(host=HOST, port=PORT, user=USER, password=PWD, database=DB)
with conn.cursor() as cur:

    cur.execute("""
        SELECT id, source_table, source_id, prediction_value, created_at
        FROM predictions
        ORDER BY created_at DESC
        LIMIT 5;
    """)
    rows = cur.fetchall()
conn.close()

print("\n=== Recent Predictions (basic view) ===")
for r in rows:
    print(r)
