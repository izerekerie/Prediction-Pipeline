# Prediction-Pipeline

## Overview
This project predicts weekly hospital patient admissions using data like
available beds, patient requests, satisfaction, staff morale, and events.
It combines a MySQL database, a FastAPI API, and a machine learning model 
that fetches the latest data, makes a prediction, and saves the result back
to the database for better hospital planning.


## Task 1 — MongoDB

This folder contains a small MongoDB helper used for the assignment: schema
definitions, a helper to connect to MongoDB, a script to create collections
with JSON Schema validators, and a small test insert script.

Files

- `connect_db.py` — returns a pymongo `Database` object using `MONGO_URI` and
  `DB_NAME` from a `.env` file (uses `python-dotenv`). The file currently sets
  `tlsAllowInvalidCertificates=True` to help debugging TLS issues; remove that
  option for production.
- `schema.py` — JSON-schema dictionaries for the four collections:
  `patients`, `staffs`, `staff_schedule`, and `services_weekly`.
- `create_collections.py` — creates collections (if missing) and applies the
  JSON Schema validators (uses `db.command('collMod', ...)`). Run this to
  enforce the schema at the server side.
- `test_insert.py` — small script that inserts a few documents and prints
  counts; useful to verify validators are applied.

Prerequisites

- Python 3.8+ (recommended 3.11/3.12 for best binary wheel support)
- Install Python packages (in your venv):

```powershell
python -m pip install -r requirements.txt
```

.env (example)
Create a `.env` file in `task1_mongodb/` (or the repo root) with these keys:

```ini
MONGO_URI=mongodb+srv://<user>:<password>@<your-cluster>.mongodb.net
DB_NAME=prediction_pipeline
```

How it works

- `connect_db.get_database()` loads `MONGO_URI` and `DB_NAME` and creates a
  `MongoClient`. It performs a `ping` to verify the connection and returns the
  `Database` object. If `MONGO_URI` is missing or the connection fails the
  function raises a helpful error.
- `create_collections.py` imports `get_database()` and the schemas from
  `schema.py`. For each schema it:
  1. Attempts to create the collection (ignored if exists).
  2. Runs `collMod` to apply the validator.

Run the setup (create collections + validators)

1. Ensure your `.env` is present and valid.
2. From the `task1_mongodb` folder run:

```powershell
python create_collections.py
```

This will print success/failure messages for each collection. If `collMod`
fails with a replica-set / TLS error, see the Troubleshooting section below.

Quick test

- After creating collections, run the small test script:

```powershell
python test_insert.py
```

The script attempts valid and invalid inserts and reports whether the
validator rejected an invalid document.

Troubleshooting

- ReplicaSetNoPrimary / TLS handshake errors: these mean the driver cannot
  successfully speak to a PRIMARY member of the Atlas cluster (often due to
  networking or TLS issues). Quick checks:
  - Confirm Atlas IP Access List includes your client IP (Atlas UI → Network Access).
  - Use the SRV connection string (mongodb+srv://...) and install SRV helpers:
    `pip install "pymongo[srv]" dnspython certifi`.
  - Temporarily enable `tlsAllowInvalidCertificates=True` in
    `connect_db.py` only for debugging. Remove it for production.
  - Try the connection test (python + ping) or use MongoDB Compass to get a
    more descriptive TLS error.
- If pydantic or other pip installs fail on Windows (Rust build errors): use
  a supported Python version (3.11/3.12) or install the Rust toolchain.

When to skip validators (temporary)

- If you cannot apply `collMod` because of topology issues but still want the
  collections created, you can:
  1. Edit `create_collections.py` and comment out or remove the `db.command("collMod", ...)`
     call so only `db.create_collection(name)` is run. This will create empty
     collections without validation.
  2. Alternatively, create collections manually using a small Python snippet:

```python
from connect_db import get_database
db = get_database()
for name in ("patients","staffs","staff_schedule","services_weekly"):
    try:
        db.create_collection(name)
    except Exception:
        pass

```

Security note

- `tlsAllowInvalidCertificates=True` is only for debugging. Do NOT use it in
  production. Always use SRV URIs, keep your Atlas IP list minimal, and prefer
  environment variables for credentials (do not commit `.env` to version control).

If you want, I can:

- add a `--no-validate` flag to `create_collections.py` so you can create
  collections without applying validators from the command line; or
- add a connection test script (ping + topology dump) under `task1_mongodb/`.

## FastAPI CRUD Service (Task 2)

This project includes a FastAPI application exposing CRUD endpoints for both relational (MySQL) and NoSQL (MongoDB) databases created in Task 1. It uses `PyMySQL` and `PyMongo` with environment variables from `.env` to connect to hosted databases.

### Setup

1. **Create a virtual environment** (recommended, especially on macOS):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure your `.env` file contains:**

   **MySQL Connection:**

   - `HOST`
   - `PORT_NUMBER`
   - `DATABASE_NAME`
   - `DATABASE_USER`
   - `DATABASE_PASSWORD`

   **MongoDB Connection (optional, defaults to localhost):**

   - `MONGO_URI` (default: `mongodb://localhost:27017/`)
   - `MONGO_DATABASE_NAME` (default: `prediction_pipeline`)

4. **Set up databases:**

   **MySQL Setup:**

   ```bash
   python task1_mysql.py
   ```

   **MongoDB Setup:**

   ```bash
   python task1_mongodb.py
   ```

   (Ensure MongoDB is running and accessible)

5. **Run the API:**
   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

Open API docs at: `http://localhost:8000/docs`

### Endpoints

- **Patients**

  - POST `/patients` (uses `sp_insert_patient` for validation + audit)
  - GET `/patients`
  - GET `/patients/{patient_id}`
  - PUT `/patients/{patient_id}`
  - DELETE `/patients/{patient_id}`

- **Staff**

  - POST `/staff`
  - GET `/staff`
  - GET `/staff/{staff_id}`
  - PUT `/staff/{staff_id}`
  - DELETE `/staff/{staff_id}`

- **Staff Schedule**

  - POST `/staff-schedule`
  - GET `/staff-schedule`
  - GET `/staff-schedule/{id}`
  - PUT `/staff-schedule/{id}`
  - DELETE `/staff-schedule/{id}`

- **Services Weekly**

  - POST `/services-weekly`
  - GET `/services-weekly`
  - GET `/services-weekly/{id}`
  - PUT `/services-weekly/{id}`
  - PATCH `/services-weekly/{id}` (partial update)
  - DELETE `/services-weekly/{id}`

- **MongoDB Endpoints** (parallel CRUD operations):
  - **Patients**
    - POST `/mongo/patients`
    - GET `/mongo/patients`
    - GET `/mongo/patients/{patient_id}`
    - PUT `/mongo/patients/{patient_id}`
    - PATCH `/mongo/patients/{patient_id}`
    - DELETE `/mongo/patients/{patient_id}`
  - **Staff**
    - POST `/mongo/staff`
    - GET `/mongo/staff`
    - GET `/mongo/staff/{staff_id}`
    - PUT `/mongo/staff/{staff_id}`
    - PATCH `/mongo/staff/{staff_id}`
    - DELETE `/mongo/staff/{staff_id}`

### Notes

- **Input Validation**: Enforced with Pydantic models (e.g., age >= 0, satisfaction 0–100, valid week/month ranges, date consistency, enum validation).
- **Auto-generated IDs**: Patient and Staff IDs are auto-generated (not required in request payload).
- **Dual Database Support**: API supports both MySQL (relational) and MongoDB (NoSQL) databases.
- **PATCH Endpoints**: Partial updates available for all resources (only update fields sent in payload).
- **Swagger Documentation**: Auto-generated API docs with tags and validation schemas at `/docs`.
- **Remember**: Activate your virtual environment (`source venv/bin/activate`) before running the API.

### ERD Diagram

See `ERD_DIAGRAM.md` for the complete Entity Relationship Diagram documentation, including:

- Entity descriptions
- Relationship mappings
- Stored procedures documentation
- Triggers documentation
- MongoDB schema structure
- dbdiagram.io syntax for visual generation
