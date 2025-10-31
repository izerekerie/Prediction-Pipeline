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

