# Prediction-Pipeline

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
