from pathlib import Path
import pandas as pd

csv_path = Path(__file__).resolve().parents[1] / "services_weekly.csv"
df = pd.read_csv(csv_path)

print("\n=== Column Names (exact) ===")
print(list(df.columns))

print("\n=== First 5 rows ===")
print(df.head())

print("\n=== Dtypes ===")
print(df.dtypes)
