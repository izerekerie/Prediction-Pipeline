import requests
import pandas as pd
import joblib
import pymysql

# ---------- CONFIG ----------
API_BASE = "http://127.0.0.1:8000"     
MODEL_PATH = "model.joblib"            

# Database credentials
HOST = "sql3.freesqldatabase.com"
DB_NAME = "sql3805058"
DB_USER = "sql3805058"
DB_PASS = "wBhIUnhTBQ"
PORT = 3306

# ---------- FETCH LATEST DATA ----------
def fetch_latest():
    """Fetch the latest record from the /services-weekly endpoint."""
    url = f"{API_BASE}/services-weekly"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    # pick the last record (largest id)
    latest = max(data, key=lambda d: d.get("id", 0))
    print(" Latest record fetched from API.")
    return latest

# ---------- PREDICT ----------
def predict_latest(latest):
    """Use model.joblib to make a prediction on the latest record."""
    bundle = joblib.load(MODEL_PATH)
    pipe = bundle["pipeline"]
    features = bundle["features"]

    # Build a one-row DataFrame matching model features
    X = pd.DataFrame([{f: latest.get(f, None) for f in features}])
    y_pred = pipe.predict(X)[0]

    print(f"Prediction for record {latest.get('id')}: {y_pred}")
    return y_pred

# ---------- LOG RESULT ----------
def log_prediction(source_id, value):
    """Insert prediction into MySQL 'predictions' table."""
    conn = pymysql.connect(
        host=HOST, port=PORT, user=DB_USER,
        password=DB_PASS, database=DB_NAME
    )
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS predictions(
                id INT AUTO_INCREMENT PRIMARY KEY,
                source_table VARCHAR(50),
                source_id INT,
                prediction_value FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            INSERT INTO predictions (source_table, source_id, prediction_value)
            VALUES (%s, %s, %s)
        """, ("services_weekly", source_id, float(value)))
    conn.commit()
    conn.close()
    print(" Logged prediction in SQL table 'predictions'.")

# ---------- MAIN ----------
def main():
    latest = fetch_latest()
    pred = predict_latest(latest)
    log_prediction(latest.get("id"), pred)

if __name__ == "__main__":
    main()
