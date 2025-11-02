from __future__ import annotations

import sys, os
from pathlib import Path
import pandas as pd
import joblib
import pymysql

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.fetch_latest import fetch_latest as fetch_latest_record


# ---------------------------
# CONFIGURATION
# ---------------------------
API_BASE = "http://127.0.0.1:8000"
RESOURCE = "services-weekly"

# MySQL connection info
HOST = "sql3.freesqldatabase.com"
PORT = 3306
DB_NAME = "sql3805058"
DB_USER = "sql3805058"
DB_PASS = "wBhIUnhTBQ"

# Locate the model file next to this script
HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE / "model.joblib"


# ---------------------------
# MAIN LOGIC
# ---------------------------
def main():
    # 1️ Fetch the latest record using teammate's helper
    latest = fetch_latest_record(API_BASE, RESOURCE)
    if not latest:
        raise RuntimeError(" No latest record from API. Make sure you seeded data.")

    print(" Latest record fetched successfully.")

    # 2️ Load your trained model
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Run train_model.py first.")
    bundle = joblib.load(MODEL_PATH)

    pipe = bundle["pipeline"]
    features = bundle["features"]
    target = bundle.get("target", "prediction")

    # 3️ Prepare and predict
    X = pd.DataFrame([{f: latest.get(f, None) for f in features}])
    y_pred = float(pipe.predict(X)[0])
    print(f" Predicted {target}: {y_pred}")

    # 4️ Log prediction in SQL DB
    source_id = latest.get("id")
    if source_id is None:
        print(" No 'id' in record; skipping DB log.")
        return

    conn = pymysql.connect(
        host=HOST, port=PORT, user=DB_USER, password=DB_PASS, database=DB_NAME
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predictions (source_table, source_id, prediction_value)
                VALUES (%s, %s, %s)
                """,
                ("services_weekly", int(source_id), y_pred),
            )
        conn.commit()
        print(" Logged prediction in SQL table 'predictions'.")
    finally:
        conn.close()


# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    main()
