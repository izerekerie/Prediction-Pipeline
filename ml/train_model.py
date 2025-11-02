from pathlib import Path
import pandas as pd
import joblib

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor

CSV_PATH = Path(__file__).resolve().parents[1] / "services_weekly.csv"

# Load data
df = pd.read_csv(CSV_PATH)

TARGET = "patients_admitted"
FEATURES = [
    "week",
    "month",
    "service",
    "available_beds",
    "patients_request",
    "patients_refused",
    "patient_satisfaction",
    "staff_morale",
    "event",
]

# Basic guard
missing = [c for c in [TARGET] + FEATURES if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns in CSV: {missing}")

# Drop rows without target
df = df.dropna(subset=[TARGET])

X = df[FEATURES].copy()
y = df[TARGET].astype(float)

# Split numeric vs categorical
num_cols = ["week","month","available_beds","patients_request","patients_refused","patient_satisfaction","staff_morale"]
cat_cols = ["service","event"]

pre = ColumnTransformer(
    transformers=[
        ("num", SimpleImputer(strategy="median"), num_cols),
        ("cat", Pipeline([
            ("imp", SimpleImputer(strategy="most_frequent")),
            ("ohe", OneHotEncoder(handle_unknown="ignore"))
        ]), cat_cols),
    ],
    remainder="drop",
)

pipe = Pipeline(steps=[
    ("pre", pre),
    ("model", RandomForestRegressor(n_estimators=300, random_state=42)),
])

pipe.fit(X, y)

bundle = {
    "pipeline": pipe,
    "features": FEATURES,
    "target": TARGET,
    "model_name": "rf_patients_admitted",
    "model_version": "v1",
}
joblib.dump(bundle, Path(__file__).with_name("model.joblib"))
print("Trained and saved to ml/model.joblib")
