from datetime import date, datetime
from enum import Enum
from secrets import token_hex
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

try:
    # Primary (normal) import when project root is on PYTHONPATH / running from repo root
    from task1_mongodb.connect_db import get_database
    from task1_mongodb import schema as task_schema
except Exception:
    # Fallback: if the module isn't found because the working directory or PYTHONPATH
    # differs (common when running uvicorn from another folder), add the repo root
    # to sys.path and retry the import.
    import sys
    import os

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from task1_mongodb.connect_db import get_database
    from task1_mongodb import schema as task_schema
from datetime import datetime as _datetime
import jsonschema
from jsonschema import FormatChecker

app = FastAPI(title="Prediction Pipeline CRUD API (Mongo)", version="1.0.0")


def db_conn():
    db = get_database()
    try:
        yield db
    finally:
        # get_database creates a client internally; not closing here to avoid side-effects
        pass


def generate_staff_id() -> str:
    return f"STF-{token_hex(6)}"


def generate_patient_id() -> str:
    return f"PAT-{token_hex(8)}"


# ======== Enums ========
class StaffRole(str, Enum):
    DOCTOR = "doctor"
    NURSE = "nurse"
    NURSING_ASSISTANT = "nursing_assistant"
    ADMIN = "ADMIN"


class ServiceType(str, Enum):
    EMERGENCY = "emergency"
    SURGERY = "surgery"
    GENERAL_MEDICINE = "general_medicine"
    ICU = "ICU"
    FRONT_DESK = "FRONT DESK"


# ======== Schemas (same as SQL API) ========
class PatientIn(BaseModel):
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
    age: Optional[int] = None
    arrival_date: Optional[date] = None
    departure_date: Optional[date] = None
    service: Optional[str] = None
    satisfaction: Optional[int] = None


class PatientPatch(BaseModel):
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
    staff_name: str = Field(min_length=1, max_length=255)
    role: Optional[StaffRole] = Field(default=None, description="Staff role")
    service: Optional[ServiceType] = Field(default=None, description="Service department")


class StaffOut(BaseModel):
    staff_id: str
    staff_name: str
    role: Optional[str]
    service: Optional[str]


class StaffPatch(BaseModel):
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
    id: str


class StaffSchedulePatch(BaseModel):
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
    id: str


class ServiceWeeklyPatch(BaseModel):
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


# ======== Utility helpers ========
def _date_to_iso(d: Optional[date]) -> Optional[str]:
    return d.isoformat() if d is not None else None


def _format_patient(doc: dict) -> dict:
    return {
        "patient_id": doc.get("patient_id"),
        "name": doc.get("name"),
        "age": doc.get("age"),
        "arrival_date": doc.get("arrival_date"),
        "departure_date": doc.get("departure_date"),
        "service": doc.get("service"),
        "satisfaction": doc.get("satisfaction"),
    }


def _format_staff(doc: dict) -> dict:
    return {
        "staff_id": doc.get("staff_id"),
        "staff_name": doc.get("staff_name"),
        "role": doc.get("role") or "",
        "service": doc.get("service") or "",
    }


def _ensure_date(val):
    """Normalize a value to a datetime.date or None.

    Accepts datetime, date, or ISO date string.
    """
    if val is None:
        return None
    # datetime from pymongo will be a datetime.datetime
    try:
        from datetime import datetime as _dt
    except Exception:
        _dt = None
    if _dt and isinstance(val, _dt):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return date.fromisoformat(val)
        except Exception:
            return None
    return None


def _normalize_patient_for_model(doc: dict) -> dict:
    d = dict(doc)
    # Make sure optional keys exist (pydantic will accept None defaults)
    d.setdefault("age", None)
    d.setdefault("arrival_date", None)
    d.setdefault("departure_date", None)
    d.setdefault("service", None)
    d.setdefault("satisfaction", None)
    # Normalize date-like fields to date objects (no time)
    d["arrival_date"] = _ensure_date(d.get("arrival_date"))
    d["departure_date"] = _ensure_date(d.get("departure_date"))
    return d


_JSON_SCHEMA_CACHE: dict = {}


def _bson_to_jsonschema(bson_schema: dict) -> dict:
    props = {}
    for key, prop in bson_schema.get("properties", {}).items():
        bsonType = prop.get("bsonType")
        types = bsonType if isinstance(bsonType, list) else [bsonType]
        json_types = []
        prop_schema: dict = {}
        for t in types:
            if t == "string":
                json_types.append("string")
            elif t == "int":
                json_types.append("integer")
            elif t == "bool":
                json_types.append("boolean")
            elif t == "date":
                json_types.append("string")
                prop_schema["format"] = "date"
            elif t == "null":
                json_types.append("null")
            else:
                json_types.append("string")
        prop_schema["type"] = json_types[0] if len(json_types) == 1 else json_types
        props[key] = prop_schema

    json_schema = {"type": "object", "properties": props}
    if "required" in bson_schema:
        json_schema["required"] = bson_schema["required"]
    return json_schema


def _validate_against_task_schema(collection: str, doc: dict):
    mapping = {
        "patients": "patients_schema",
        "staff": "staffs_schema",
        "staff_schedule": "staff_schedule_schema",
        "services_weekly": "services_weekly_schema",
    }
    schema_name = mapping.get(collection)
    if not schema_name:
        return True
    bson_sch = getattr(task_schema, schema_name, None)
    if not bson_sch:
        return True

    if schema_name not in _JSON_SCHEMA_CACHE:
        _JSON_SCHEMA_CACHE[schema_name] = _bson_to_jsonschema(bson_sch)
    json_sch = _JSON_SCHEMA_CACHE[schema_name]

    try:
        jsonschema.validate(instance=doc, schema=json_sch, format_checker=FormatChecker())
    except jsonschema.ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Schema validation error: {e.message}")
    return True


# ======== Patients CRUD ========
@app.post("/patients", response_model=dict, status_code=status.HTTP_201_CREATED, tags=["Patients"])
def create_patient(payload: PatientIn, db=Depends(db_conn)):
    patient_id = generate_patient_id()
    doc = payload.model_dump()
    # store dates as ISO strings for portability
    doc["arrival_date"] = _date_to_iso(doc.get("arrival_date"))
    doc["departure_date"] = _date_to_iso(doc.get("departure_date"))
    doc["patient_id"] = patient_id
    # validate against task schema
    _validate_against_task_schema("patients", doc)
    res = db["patients"].insert_one(doc)
    if not res.acknowledged:
        raise HTTPException(status_code=500, detail="Failed to create patient")
    return {"status": "created", "patient_id": patient_id}


@app.get("/patients", response_model=list[PatientOut], tags=["Patients"])
def list_patients(db=Depends(db_conn)):
    cursor = db["patients"].find({}, {"_id": 0}).sort("patient_id", 1)
    rows = [PatientOut(**_normalize_patient_for_model(r)) for r in cursor]
    return rows


@app.get("/patients/{patient_id}", response_model=PatientOut, tags=["Patients"])
def get_patient(patient_id: str, db=Depends(db_conn)):
    doc = db["patients"].find_one({"patient_id": patient_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientOut(**_normalize_patient_for_model(doc))


@app.put("/patients/{patient_id}", response_model=dict, tags=["Patients"])
def update_patient(patient_id: str, payload: PatientIn, db=Depends(db_conn)):
    payload_doc = payload.model_dump()
    payload_doc["arrival_date"] = _date_to_iso(payload_doc.get("arrival_date"))
    payload_doc["departure_date"] = _date_to_iso(payload_doc.get("departure_date"))
    # ensure schema compliance by merging with existing patient_id
    payload_doc["patient_id"] = patient_id
    _validate_against_task_schema("patients", payload_doc)
    result = db["patients"].update_one({"patient_id": patient_id}, {"$set": payload_doc})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"updated": result.modified_count}


@app.patch("/patients/{patient_id}", response_model=dict, tags=["Patients"])
def patch_patient(patient_id: str, payload: PatientPatch, db=Depends(db_conn)):
    doc = db["patients"].find_one({"patient_id": patient_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Patient not found")
    payload_dict = payload.model_dump(exclude_unset=True)
    if "arrival_date" in payload_dict:
        payload_dict["arrival_date"] = _date_to_iso(payload_dict.get("arrival_date"))
    if "departure_date" in payload_dict:
        payload_dict["departure_date"] = _date_to_iso(payload_dict.get("departure_date"))
    if not payload_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    # merge and validate against schema
    merged = dict(doc)
    merged.update(payload_dict)
    _validate_against_task_schema("patients", merged)
    result = db["patients"].update_one({"patient_id": patient_id}, {"$set": payload_dict})
    return {"updated": result.modified_count}


@app.delete("/patients/{patient_id}", response_model=dict, status_code=status.HTTP_200_OK, tags=["Patients"])
def delete_patient(patient_id: str, db=Depends(db_conn)):
    result = db["patients"].delete_one({"patient_id": patient_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"deleted": result.deleted_count}


# ======== Staff CRUD ========
@app.post("/staff", response_model=StaffOut, status_code=status.HTTP_201_CREATED, tags=["Staff"])
def create_staff(payload: StaffIn, db=Depends(db_conn)):
    staff_id = generate_staff_id()
    role_value = payload.role.value if payload.role else None
    service_value = payload.service.value if payload.service else None
    doc = {
        "staff_id": staff_id,
        "staff_name": payload.staff_name,
        "role": role_value,
        "service": service_value,
    }
    # validate against task schema
    _validate_against_task_schema("staff", doc)
    db["staff"].insert_one(doc)
    saved = db["staff"].find_one({"staff_id": staff_id}, {"_id": 0})
    if not saved:
        raise HTTPException(status_code=500, detail="Failed to retrieve created staff record")
    return StaffOut(**saved)


@app.get("/staff", response_model=list[StaffOut], tags=["Staff"])
def list_staff(db=Depends(db_conn)):
    cursor = db["staff"].find({}, {"_id": 0}).sort("staff_id", 1)
    return [StaffOut(**r) for r in cursor]


@app.get("/staff/{staff_id}", response_model=StaffOut, tags=["Staff"])
def get_staff(staff_id: str, db=Depends(db_conn)):
    doc = db["staff"].find_one({"staff_id": staff_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Staff not found")
    return StaffOut(**doc)


@app.put("/staff/{staff_id}", response_model=dict, tags=["Staff"])
def update_staff(staff_id: str, payload: StaffIn, db=Depends(db_conn)):
    role_value = payload.role.value if payload.role else None
    service_value = payload.service.value if payload.service else None
    payload_doc = {
        "staff_id": staff_id,
        "staff_name": payload.staff_name,
        "role": role_value,
        "service": service_value,
    }
    _validate_against_task_schema("staff", payload_doc)
    result = db["staff"].update_one({"staff_id": staff_id}, {"$set": payload_doc})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"updated": result.modified_count}


@app.patch("/staff/{staff_id}", response_model=dict, tags=["Staff"])
def patch_staff(staff_id: str, payload: StaffPatch, db=Depends(db_conn)):
    doc = db["staff"].find_one({"staff_id": staff_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Staff not found")
    payload_dict = payload.model_dump(exclude_unset=True)
    if "role" in payload_dict and payload_dict["role"] is not None:
        payload_dict["role"] = payload_dict["role"].value
    if "service" in payload_dict and payload_dict["service"] is not None:
        payload_dict["service"] = payload_dict["service"].value
    if not payload_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    # merge for validation
    merged = dict(doc)
    merged.update(payload_dict)
    _validate_against_task_schema("staff", merged)
    result = db["staff"].update_one({"staff_id": staff_id}, {"$set": payload_dict})
    return {"updated": result.modified_count}


@app.delete("/staff/{staff_id}", response_model=dict, tags=["Staff"])
def delete_staff(staff_id: str, db=Depends(db_conn)):
    result = db["staff"].delete_one({"staff_id": staff_id})
    return {"deleted": result.deleted_count}


# ======== Staff Schedule CRUD ========
@app.post("/staff-schedule", response_model=StaffScheduleOut, status_code=status.HTTP_201_CREATED, tags=["Staff Schedule"])
def create_staff_schedule(payload: StaffScheduleIn, db=Depends(db_conn)):
    doc = payload.model_dump()
    doc["on_shift"] = bool(doc.get("on_shift"))
    res = db["staff_schedule"].insert_one(doc)
    saved = db["staff_schedule"].find_one({"_id": res.inserted_id})
    saved["id"] = str(saved.get("_id"))
    saved.pop("_id", None)
    return StaffScheduleOut(**saved)


@app.get("/staff-schedule", response_model=list[StaffScheduleOut], tags=["Staff Schedule"])
def list_staff_schedule(db=Depends(db_conn)):
    cursor = db["staff_schedule"].find().sort("_id", -1)
    out = []
    for r in cursor:
        r["id"] = str(r.get("_id"))
        r.pop("_id", None)
        out.append(StaffScheduleOut(**r))
    return out


@app.get("/staff-schedule/{id}", response_model=StaffScheduleOut, tags=["Staff Schedule"])
def get_staff_schedule(id: str, db=Depends(db_conn)):
    from bson.objectid import ObjectId
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = db["staff_schedule"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Schedule not found")
    doc["id"] = str(doc.get("_id"))
    doc.pop("_id", None)
    return StaffScheduleOut(**doc)


@app.put("/staff-schedule/{id}", response_model=dict, tags=["Staff Schedule"])
def update_staff_schedule(id: str, payload: StaffScheduleIn, db=Depends(db_conn)):
    from bson.objectid import ObjectId
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = payload.model_dump()
    doc["on_shift"] = 1 if doc.get("on_shift") else 0
    result = db["staff_schedule"].update_one({"_id": oid}, {"$set": doc})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"updated": result.modified_count}


@app.patch("/staff-schedule/{id}", response_model=dict, tags=["Staff Schedule"])
def patch_staff_schedule(id: str, payload: StaffSchedulePatch, db=Depends(db_conn)):
    from bson.objectid import ObjectId
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = db["staff_schedule"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Schedule not found")
    payload_dict = payload.model_dump(exclude_unset=True)
    if "on_shift" in payload_dict and payload_dict["on_shift"] is not None:
        payload_dict["on_shift"] = 1 if payload_dict["on_shift"] else 0
    if not payload_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db["staff_schedule"].update_one({"_id": oid}, {"$set": payload_dict})
    return {"updated": result.modified_count}


@app.delete("/staff-schedule/{id}", response_model=dict, tags=["Staff Schedule"])
def delete_staff_schedule(id: str, db=Depends(db_conn)):
    from bson.objectid import ObjectId
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    result = db["staff_schedule"].delete_one({"_id": oid})
    return {"deleted": result.deleted_count}


# ======== Services Weekly CRUD ========
@app.post("/services-weekly", response_model=ServiceWeeklyOut, status_code=status.HTTP_201_CREATED, tags=["Services Weekly"])
def create_service_weekly(payload: ServiceWeeklyIn, db=Depends(db_conn)):
    doc = payload.model_dump()
    # validate against task schema
    _validate_against_task_schema("services_weekly", doc)
    res = db["services_weekly"].insert_one(doc)
    saved = db["services_weekly"].find_one({"_id": res.inserted_id})
    saved["id"] = str(saved.get("_id"))
    saved.pop("_id", None)
    return ServiceWeeklyOut(**saved)


@app.get("/services-weekly", response_model=list[ServiceWeeklyOut], tags=["Services Weekly"])
def list_services_weekly(db=Depends(db_conn)):
    cursor = db["services_weekly"].find().sort("_id", -1)
    out = []
    for r in cursor:
        r["id"] = str(r.get("_id"))
        r.pop("_id", None)
        out.append(ServiceWeeklyOut(**r))
    return out


@app.get("/services-weekly/{id}", response_model=ServiceWeeklyOut, tags=["Services Weekly"])
def get_service_weekly(id: str, db=Depends(db_conn)):
    from bson.objectid import ObjectId
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = db["services_weekly"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Record not found")
    doc["id"] = str(doc.get("_id"))
    doc.pop("_id", None)
    return ServiceWeeklyOut(**doc)


@app.put("/services-weekly/{id}", response_model=dict, tags=["Services Weekly"])
def update_service_weekly(id: str, payload: ServiceWeeklyIn, db=Depends(db_conn)):
    from bson.objectid import ObjectId
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = payload.model_dump()
    # validate merged document against schema
    merged = dict(doc)
    merged.update(doc)
    _validate_against_task_schema("services_weekly", doc)
    result = db["services_weekly"].update_one({"_id": oid}, {"$set": doc})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"updated": result.modified_count}


@app.patch("/services-weekly/{id}", response_model=dict, tags=["Services Weekly"])
def patch_service_weekly(id: str, payload: ServiceWeeklyPatch, db=Depends(db_conn)):
    from bson.objectid import ObjectId
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = db["services_weekly"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Record not found")
    payload_dict = payload.model_dump(exclude_unset=True)
    if not payload_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    # merge and validate
    merged = dict(doc)
    merged.update(payload_dict)
    _validate_against_task_schema("services_weekly", merged)
    result = db["services_weekly"].update_one({"_id": oid}, {"$set": payload_dict})
    return {"updated": result.modified_count}


@app.delete("/services-weekly/{id}", response_model=dict, tags=["Services Weekly"])
def delete_service_weekly(id: str, db=Depends(db_conn)):
    from bson.objectid import ObjectId
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    result = db["services_weekly"].delete_one({"_id": oid})
    return {"deleted": result.deleted_count}


@app.get("/health", response_model=dict, tags=["Health"])
def health(db=Depends(db_conn)):
    # Simple ping
    try:
        db.client.admin.command("ping")
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=500, detail="db ping failed")
