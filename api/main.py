from datetime import date
from enum import Enum
from secrets import token_hex
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from .db import (
	call_sp_insert_patient,
	execute,
	get_connection,
	query_all,
	query_one,
)


app = FastAPI(title="Prediction Pipeline CRUD API", version="1.0.0")


def db_conn():
	conn = get_connection()
	try:
		yield conn
	finally:
		conn.close()


def generate_staff_id() -> str:
	"""Generate a unique staff_id following the pattern STF-xxxxxx"""
	return f"STF-{token_hex(6)}"


def generate_patient_id() -> str:
	"""Generate a unique patient_id"""
	return f"PAT-{token_hex(8)}"


# ======== Enums ========
class StaffRole(str, Enum):
	DOCTOR = "doctor"
	NURSE = "nurse"
	NURSING_ASSISTANT = "nursing_assistant"
	ADMIN = "ADMIN"  # Added based on user request
	# Add more roles as needed


class ServiceType(str, Enum):
	EMERGENCY = "emergency"
	SURGERY = "surgery"
	GENERAL_MEDICINE = "general_medicine"
	ICU = "ICU"
	FRONT_DESK = "FRONT DESK"  # Added based on user request
	# Add more services as needed


# ======== Schemas ========
class PatientIn(BaseModel):
	# patient_id is auto-generated, not in request payload
	name: str = Field(min_length=1, max_length=255)
	age: Optional[int] = Field(default=None, ge=0)
	arrival_date: Optional[date] = None
	departure_date: Optional[date] = None
	service: Optional[str] = Field(default=None, max_length=64)
	satisfaction: Optional[int] = Field(default=None, ge=0, le=100)

	@field_validator("departure_date")
	@classmethod
	def validate_dates(cls, v, info):
		arrival = info.data.get("arrival_date")
		if v is not None and arrival is not None and v < arrival:
			raise ValueError("departure_date cannot be before arrival_date")
		return v


class PatientOut(BaseModel):
	patient_id: str
	name: str
	age: Optional[int]
	arrival_date: Optional[date]
	departure_date: Optional[date]
	service: Optional[str]
	satisfaction: Optional[int]


class PatientPatch(BaseModel):
	# All fields optional for partial updates
	name: Optional[str] = Field(default=None, min_length=1, max_length=255)
	age: Optional[int] = Field(default=None, ge=0)
	arrival_date: Optional[date] = None
	departure_date: Optional[date] = None
	service: Optional[str] = Field(default=None, max_length=64)
	satisfaction: Optional[int] = Field(default=None, ge=0, le=100)

	@field_validator("departure_date")
	@classmethod
	def validate_dates(cls, v, info):
		arrival = info.data.get("arrival_date")
		if v is not None and arrival is not None and v < arrival:
			raise ValueError("departure_date cannot be before arrival_date")
		return v


class StaffIn(BaseModel):
	# staff_id is auto-generated, not in request payload
	staff_name: str = Field(min_length=1, max_length=255)
	role: Optional[StaffRole] = Field(default=None, description="Staff role")
	service: Optional[ServiceType] = Field(default=None, description="Service department")


class StaffOut(BaseModel):
	staff_id: str
	staff_name: str
	role: Optional[str]  # Returned as string from DB
	service: Optional[str]  # Returned as string from DB


class StaffPatch(BaseModel):
	# All fields optional for partial updates
	staff_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
	role: Optional[StaffRole] = Field(default=None, description="Staff role")
	service: Optional[ServiceType] = Field(default=None, description="Service department")


class StaffScheduleIn(BaseModel):
	day_or_shift: str = Field(min_length=1, max_length=64)
	staff_id: Optional[str] = Field(default=None, max_length=64)
	staff_name: Optional[str] = Field(default=None, max_length=255)
	role: Optional[str] = Field(default=None, max_length=64)
	service: Optional[str] = Field(default=None, max_length=64)
	on_shift: Optional[bool] = False


class StaffScheduleOut(StaffScheduleIn):
	id: int


class StaffSchedulePatch(BaseModel):
	# All fields optional for partial updates
	day_or_shift: Optional[str] = Field(default=None, min_length=1, max_length=64)
	staff_id: Optional[str] = Field(default=None, max_length=64)
	staff_name: Optional[str] = Field(default=None, max_length=255)
	role: Optional[str] = Field(default=None, max_length=64)
	service: Optional[str] = Field(default=None, max_length=64)
	on_shift: Optional[bool] = None


class ServiceWeeklyIn(BaseModel):
	week: int = Field(ge=1, le=53)
	month: int = Field(ge=1, le=12)
	service: str = Field(min_length=1, max_length=64)
	available_beds: Optional[int] = Field(default=None, ge=0)
	patients_request: Optional[int] = Field(default=None, ge=0)
	patients_admitted: Optional[int] = Field(default=None, ge=0)
	patients_refused: Optional[int] = Field(default=None, ge=0)
	patient_satisfaction: Optional[int] = Field(default=None, ge=0, le=100)
	staff_morale: Optional[int] = Field(default=None, ge=0, le=100)
	event: Optional[str] = Field(default=None, max_length=255)


class ServiceWeeklyOut(ServiceWeeklyIn):
	id: int


class ServiceWeeklyPatch(BaseModel):
	# All fields optional for partial updates
	week: Optional[int] = Field(default=None, ge=1, le=53)
	month: Optional[int] = Field(default=None, ge=1, le=12)
	service: Optional[str] = Field(default=None, min_length=1, max_length=64)
	available_beds: Optional[int] = Field(default=None, ge=0)
	patients_request: Optional[int] = Field(default=None, ge=0)
	patients_admitted: Optional[int] = Field(default=None, ge=0)
	patients_refused: Optional[int] = Field(default=None, ge=0)
	patient_satisfaction: Optional[int] = Field(default=None, ge=0, le=100)
	staff_morale: Optional[int] = Field(default=None, ge=0, le=100)
	event: Optional[str] = Field(default=None, max_length=255)


# ======== Patients CRUD ========
@app.post("/patients", response_model=dict, status_code=status.HTTP_201_CREATED, tags=["Patients"])
def create_patient(payload: PatientIn, conn=Depends(db_conn)):
	# Auto-generate patient_id
	patient_id = generate_patient_id()
	
	# Create a copy of the payload with the generated ID
	patient_data = payload.model_dump()
	patient_data["patient_id"] = patient_id
	
	result = call_sp_insert_patient(conn, patient_data, changed_by="api")
	if result.get("status") == "validation_failed":
		raise HTTPException(status_code=400, detail=result.get("error_message"))
	return {"status": "created", "patient_id": patient_id}


@app.get("/patients", response_model=list[PatientOut], tags=["Patients"])
def list_patients(conn=Depends(db_conn)):
	rows = query_all(conn, "SELECT * FROM patients ORDER BY patient_id", ())
	return rows


@app.get("/patients/{patient_id}", response_model=PatientOut, tags=["Patients"])
def get_patient(patient_id: str, conn=Depends(db_conn)):
	row = query_one(conn, "SELECT * FROM patients WHERE patient_id=%s", (patient_id,))
	if not row:
		raise HTTPException(status_code=404, detail="Patient not found")
	return row


@app.put("/patients/{patient_id}", response_model=dict, tags=["Patients"])
def update_patient(patient_id: str, payload: PatientIn, conn=Depends(db_conn)):
	# patient_id is only in the path, not in the body

	row = query_one(conn, "SELECT * FROM patients WHERE patient_id=%s", (patient_id,))
	if not row:
		raise HTTPException(status_code=404, detail="Patient not found")

	count = execute(
		conn,
		"""
		UPDATE patients SET name=%s, age=%s, arrival_date=%s, departure_date=%s,
		       service=%s, satisfaction=%s
		WHERE patient_id=%s
		""",
		(
			payload.name,
			payload.age,
			payload.arrival_date,
			payload.departure_date,
			payload.service,
			payload.satisfaction,
			patient_id,
		),
	)
	return {"updated": count}


@app.patch("/patients/{patient_id}", response_model=dict, tags=["Patients"])
def patch_patient(patient_id: str, payload: PatientPatch, conn=Depends(db_conn)):
	# Check if patient exists
	row = query_one(conn, "SELECT * FROM patients WHERE patient_id=%s", (patient_id,))
	if not row:
		raise HTTPException(status_code=404, detail="Patient not found")
	
	# Build dynamic UPDATE query with only provided fields
	updates = []
	params = []
	
	payload_dict = payload.model_dump(exclude_unset=True)  # Only get fields that were explicitly set
	
	if "name" in payload_dict and payload_dict["name"] is not None:
		updates.append("name=%s")
		params.append(payload_dict["name"])
	if "age" in payload_dict:
		updates.append("age=%s")
		params.append(payload_dict["age"])
	if "arrival_date" in payload_dict:
		updates.append("arrival_date=%s")
		params.append(payload_dict["arrival_date"])
	if "departure_date" in payload_dict:
		updates.append("departure_date=%s")
		params.append(payload_dict["departure_date"])
	if "service" in payload_dict:
		updates.append("service=%s")
		params.append(payload_dict["service"])
	if "satisfaction" in payload_dict:
		updates.append("satisfaction=%s")
		params.append(payload_dict["satisfaction"])
	
	if not updates:
		raise HTTPException(status_code=400, detail="No fields to update")
	
	params.append(patient_id)
	sql = f"UPDATE patients SET {', '.join(updates)} WHERE patient_id=%s"
	count = execute(conn, sql, tuple(params))
	return {"updated": count}


@app.delete("/patients/{patient_id}", response_model=dict, status_code=status.HTTP_200_OK, tags=["Patients"])
def delete_patient(patient_id: str, conn=Depends(db_conn)):
	row = query_one(conn, "SELECT * FROM patients WHERE patient_id=%s", (patient_id,))
	if not row:
		raise HTTPException(status_code=404, detail="Patient not found")
	count = execute(conn, "DELETE FROM patients WHERE patient_id=%s", (patient_id,))
	return {"deleted": count}


# ======== Staff CRUD ========
@app.post("/staff", response_model=StaffOut, status_code=status.HTTP_201_CREATED, tags=["Staff"])
def create_staff(payload: StaffIn, conn=Depends(db_conn)):
	# Auto-generate staff_id
	staff_id = generate_staff_id()
	
	# Convert enum to string value (or None)
	role_value = payload.role.value if payload.role else None
	service_value = payload.service.value if payload.service else None
	
	execute(
		conn,
		"INSERT INTO staff (staff_id, staff_name, role, service) VALUES (%s,%s,%s,%s)",
		(staff_id, payload.staff_name, role_value, service_value),
	)
	
	# Fetch the inserted record
	row = query_one(conn, "SELECT * FROM staff WHERE staff_id=%s", (staff_id,))
	if not row:
		raise HTTPException(status_code=500, detail="Failed to retrieve created staff record")
	
	# Ensure we return proper values (handle None -> empty string conversion)
	if row.get("role") is None:
		row["role"] = role_value or ""
	if row.get("service") is None:
		row["service"] = service_value or ""
	
	return row  # type: ignore


@app.get("/staff", response_model=list[StaffOut], tags=["Staff"])
def list_staff(conn=Depends(db_conn)):
	return query_all(conn, "SELECT * FROM staff ORDER BY staff_id", ())


@app.get("/staff/{staff_id}", response_model=StaffOut, tags=["Staff"])
def get_staff(staff_id: str, conn=Depends(db_conn)):
	row = query_one(conn, "SELECT * FROM staff WHERE staff_id=%s", (staff_id,))
	if not row:
		raise HTTPException(status_code=404, detail="Staff not found")
	return row  # type: ignore


@app.put("/staff/{staff_id}", response_model=dict, tags=["Staff"])
def update_staff(staff_id: str, payload: StaffIn, conn=Depends(db_conn)):
	# staff_id is only in the path, not in the body
	# Convert enum to string value (or None)
	role_value = payload.role.value if payload.role else None
	service_value = payload.service.value if payload.service else None
	
	count = execute(
		conn,
		"UPDATE staff SET staff_name=%s, role=%s, service=%s WHERE staff_id=%s",
		(payload.staff_name, role_value, service_value, staff_id),
	)
	return {"updated": count}


@app.patch("/staff/{staff_id}", response_model=dict, tags=["Staff"])
def patch_staff(staff_id: str, payload: StaffPatch, conn=Depends(db_conn)):
	# Check if staff exists
	row = query_one(conn, "SELECT * FROM staff WHERE staff_id=%s", (staff_id,))
	if not row:
		raise HTTPException(status_code=404, detail="Staff not found")
	
	# Build dynamic UPDATE query with only provided fields
	updates = []
	params = []
	
	payload_dict = payload.model_dump(exclude_unset=True)  # Only get fields that were explicitly set
	
	if "staff_name" in payload_dict and payload_dict["staff_name"] is not None:
		updates.append("staff_name=%s")
		params.append(payload_dict["staff_name"])
	if "role" in payload_dict and payload_dict["role"] is not None:
		updates.append("role=%s")
		params.append(payload_dict["role"].value)  # Convert enum to value
	if "service" in payload_dict and payload_dict["service"] is not None:
		updates.append("service=%s")
		params.append(payload_dict["service"].value)  # Convert enum to value
	
	if not updates:
		raise HTTPException(status_code=400, detail="No fields to update")
	
	params.append(staff_id)
	sql = f"UPDATE staff SET {', '.join(updates)} WHERE staff_id=%s"
	count = execute(conn, sql, tuple(params))
	return {"updated": count}


@app.delete("/staff/{staff_id}", response_model=dict, tags=["Staff"])
def delete_staff(staff_id: str, conn=Depends(db_conn)):
	count = execute(conn, "DELETE FROM staff WHERE staff_id=%s", (staff_id,))
	return {"deleted": count}


# ======== Staff Schedule CRUD ========
@app.post("/staff-schedule", response_model=StaffScheduleOut, status_code=status.HTTP_201_CREATED, tags=["Staff Schedule"])
def create_staff_schedule(payload: StaffScheduleIn, conn=Depends(db_conn)):
	execute(
		conn,
		"""
		INSERT INTO staff_schedule (day_or_shift, staff_id, staff_name, role, service, on_shift)
		VALUES (%s,%s,%s,%s,%s,%s)
		""",
		(
			payload.day_or_shift,
			payload.staff_id,
			payload.staff_name,
			payload.role,
			payload.service,
			1 if payload.on_shift else 0,
		),
	)
	row = query_one(conn, "SELECT * FROM staff_schedule ORDER BY id DESC LIMIT 1", ())
	return row  # type: ignore


@app.get("/staff-schedule", response_model=list[StaffScheduleOut], tags=["Staff Schedule"])
def list_staff_schedule(conn=Depends(db_conn)):
	return query_all(conn, "SELECT * FROM staff_schedule ORDER BY id DESC", ())


@app.get("/staff-schedule/{id}", response_model=StaffScheduleOut, tags=["Staff Schedule"])
def get_staff_schedule(id: int, conn=Depends(db_conn)):
	row = query_one(conn, "SELECT * FROM staff_schedule WHERE id=%s", (id,))
	if not row:
		raise HTTPException(status_code=404, detail="Schedule not found")
	return row  # type: ignore


@app.put("/staff-schedule/{id}", response_model=dict, tags=["Staff Schedule"])
def update_staff_schedule(id: int, payload: StaffScheduleIn, conn=Depends(db_conn)):
	count = execute(
		conn,
		"""
		UPDATE staff_schedule
		SET day_or_shift=%s, staff_id=%s, staff_name=%s, role=%s, service=%s, on_shift=%s
		WHERE id=%s
		""",
		(
			payload.day_or_shift,
			payload.staff_id,
			payload.staff_name,
			payload.role,
			payload.service,
			1 if payload.on_shift else 0,
			id,
		),
	)
	return {"updated": count}


@app.patch("/staff-schedule/{id}", response_model=dict, tags=["Staff Schedule"])
def patch_staff_schedule(id: int, payload: StaffSchedulePatch, conn=Depends(db_conn)):
	# Check if schedule exists
	row = query_one(conn, "SELECT * FROM staff_schedule WHERE id=%s", (id,))
	if not row:
		raise HTTPException(status_code=404, detail="Schedule not found")
	
	# Build dynamic UPDATE query with only provided fields
	updates = []
	params = []
	
	payload_dict = payload.model_dump(exclude_unset=True)  # Only get fields that were explicitly set
	
	if "day_or_shift" in payload_dict and payload_dict["day_or_shift"] is not None:
		updates.append("day_or_shift=%s")
		params.append(payload_dict["day_or_shift"])
	if "staff_id" in payload_dict:
		updates.append("staff_id=%s")
		params.append(payload_dict["staff_id"])
	if "staff_name" in payload_dict:
		updates.append("staff_name=%s")
		params.append(payload_dict["staff_name"])
	if "role" in payload_dict:
		updates.append("role=%s")
		params.append(payload_dict["role"])
	if "service" in payload_dict:
		updates.append("service=%s")
		params.append(payload_dict["service"])
	if "on_shift" in payload_dict and payload_dict["on_shift"] is not None:
		updates.append("on_shift=%s")
		params.append(1 if payload_dict["on_shift"] else 0)
	
	if not updates:
		raise HTTPException(status_code=400, detail="No fields to update")
	
	params.append(id)
	sql = f"UPDATE staff_schedule SET {', '.join(updates)} WHERE id=%s"
	count = execute(conn, sql, tuple(params))
	return {"updated": count}


@app.delete("/staff-schedule/{id}", response_model=dict, tags=["Staff Schedule"])
def delete_staff_schedule(id: int, conn=Depends(db_conn)):
	count = execute(conn, "DELETE FROM staff_schedule WHERE id=%s", (id,))
	return {"deleted": count}


# ======== Services Weekly CRUD ========
@app.post("/services-weekly", response_model=ServiceWeeklyOut, status_code=status.HTTP_201_CREATED, tags=["Services Weekly"])
def create_service_weekly(payload: ServiceWeeklyIn, conn=Depends(db_conn)):
	execute(
		conn,
		"""
		INSERT INTO services_weekly
		(`week`,`month`,service,available_beds,patients_request,patients_admitted,patients_refused,
		 patient_satisfaction,staff_morale,`event`)
		VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
		""",
		(
			payload.week,
			payload.month,
			payload.service,
			payload.available_beds,
			payload.patients_request,
			payload.patients_admitted,
			payload.patients_refused,
			payload.patient_satisfaction,
			payload.staff_morale,
			payload.event,
		),
	)
	row = query_one(
		conn,
		"SELECT * FROM services_weekly WHERE `week`=%s AND `month`=%s AND service=%s",
		(payload.week, payload.month, payload.service),
	)
	return row  # type: ignore


@app.get("/services-weekly", response_model=list[ServiceWeeklyOut], tags=["Services Weekly"])
def list_services_weekly(conn=Depends(db_conn)):
	return query_all(conn, "SELECT * FROM services_weekly ORDER BY id DESC", ())


@app.get("/services-weekly/{id}", response_model=ServiceWeeklyOut, tags=["Services Weekly"])
def get_service_weekly(id: int, conn=Depends(db_conn)):
	row = query_one(conn, "SELECT * FROM services_weekly WHERE id=%s", (id,))
	if not row:
		raise HTTPException(status_code=404, detail="Record not found")
	return row  # type: ignore


@app.put("/services-weekly/{id}", response_model=dict, tags=["Services Weekly"])
def update_service_weekly(id: int, payload: ServiceWeeklyIn, conn=Depends(db_conn)):
	count = execute(
		conn,
		"""
		UPDATE services_weekly
		SET `week`=%s, `month`=%s, service=%s, available_beds=%s, patients_request=%s,
		    patients_admitted=%s, patients_refused=%s, patient_satisfaction=%s, staff_morale=%s, `event`=%s
		WHERE id=%s
		""",
		(
			payload.week,
			payload.month,
			payload.service,
			payload.available_beds,
			payload.patients_request,
			payload.patients_admitted,
			payload.patients_refused,
			payload.patient_satisfaction,
			payload.staff_morale,
			payload.event,
			id,
		),
	)
	return {"updated": count}


@app.patch("/services-weekly/{id}", response_model=dict, tags=["Services Weekly"])
def patch_service_weekly(id: int, payload: ServiceWeeklyPatch, conn=Depends(db_conn)):
	# Check if record exists
	row = query_one(conn, "SELECT * FROM services_weekly WHERE id=%s", (id,))
	if not row:
		raise HTTPException(status_code=404, detail="Record not found")
	
	# Build dynamic UPDATE query with only provided fields
	updates = []
	params = []
	
	payload_dict = payload.model_dump(exclude_unset=True)  # Only get fields that were explicitly set
	
	if "week" in payload_dict and payload_dict["week"] is not None:
		updates.append("`week`=%s")
		params.append(payload_dict["week"])
	if "month" in payload_dict and payload_dict["month"] is not None:
		updates.append("`month`=%s")
		params.append(payload_dict["month"])
	if "service" in payload_dict and payload_dict["service"] is not None:
		updates.append("service=%s")
		params.append(payload_dict["service"])
	if "available_beds" in payload_dict:
		updates.append("available_beds=%s")
		params.append(payload_dict["available_beds"])
	if "patients_request" in payload_dict:
		updates.append("patients_request=%s")
		params.append(payload_dict["patients_request"])
	if "patients_admitted" in payload_dict:
		updates.append("patients_admitted=%s")
		params.append(payload_dict["patients_admitted"])
	if "patients_refused" in payload_dict:
		updates.append("patients_refused=%s")
		params.append(payload_dict["patients_refused"])
	if "patient_satisfaction" in payload_dict:
		updates.append("patient_satisfaction=%s")
		params.append(payload_dict["patient_satisfaction"])
	if "staff_morale" in payload_dict:
		updates.append("staff_morale=%s")
		params.append(payload_dict["staff_morale"])
	if "event" in payload_dict:
		updates.append("`event`=%s")
		params.append(payload_dict["event"])
	
	if not updates:
		raise HTTPException(status_code=400, detail="No fields to update")
	
	params.append(id)
	sql = f"UPDATE services_weekly SET {', '.join(updates)} WHERE id=%s"
	count = execute(conn, sql, tuple(params))
	return {"updated": count}


@app.delete("/services-weekly/{id}", response_model=dict, tags=["Services Weekly"])
def delete_service_weekly(id: int, conn=Depends(db_conn)):
	count = execute(conn, "DELETE FROM services_weekly WHERE id=%s", (id,))
	return {"deleted": count}


@app.get("/health", response_model=dict, tags=["Health"])
def health(conn=Depends(db_conn)):
	_ = query_one(conn, "SELECT 1 AS ok", ())
	return {"status": "ok"}

