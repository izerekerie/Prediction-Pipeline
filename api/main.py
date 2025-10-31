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

