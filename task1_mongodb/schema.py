# schema.py

patients_schema = {
    "bsonType": "object",
    "required": ["patient_id", "name", "age", "arrival_date", "service", "satisfaction"],
    "properties": {
        "patient_id": {"bsonType": "string"},
        "name": {"bsonType": "string"},
        "age": {"bsonType": "int"},
        "arrival_date": {"bsonType": "date"},
        "departure_date": {"bsonType": ["date", "null"]},
        "service": {"bsonType": "string"},
        "satisfaction": {"bsonType": "int"}
    }
}

staffs_schema = {
    "bsonType": "object",
    "required": ["staff_id", "staff_name", "role", "service"],
    "properties": {
        "staff_id": {"bsonType": "string"},
        "staff_name": {"bsonType": "string"},
        "role": {"bsonType": "string"},
        "service": {"bsonType": "string"}
    }
}

staff_schedule_schema = {
    "bsonType": "object",
    "required": ["week", "staff_id", "staff_name", "role", "service", "present"],
    "properties": {
        "week": {"bsonType": "int"},
        "staff_id": {"bsonType": "string"},
        "staff_name": {"bsonType": "string"},
        "role": {"bsonType": "string"},
        "service": {"bsonType": "string"},
        "present": {"bsonType": "bool"}
    }
}

services_weekly_schema = {
    "bsonType": "object",
    "required": [
        "week", "month", "service",
        "available_beds", "patients_request", "patients_admitted",
        "patients_refused", "patient_satisfaction", "staff_morale"
    ],
    "properties": {
        "week": {"bsonType": "int"},
        "month": {"bsonType": "int"},
        "service": {"bsonType": "string"},
        "available_beds": {"bsonType": "int"},
        "patients_request": {"bsonType": "int"},
        "patients_admitted": {"bsonType": "int"},
        "patients_refused": {"bsonType": "int"},
        "patient_satisfaction": {"bsonType": "int"},
        "staff_morale": {"bsonType": "int"},
        "event": {"bsonType": "string"}
    }
}
