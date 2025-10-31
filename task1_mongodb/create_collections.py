from connect_db import get_database
from schema import (
    patients_schema,
    staffs_schema,
    staff_schedule_schema,
    services_weekly_schema,
)


def create_collections():
    db = get_database()

    collections = {
        "patients": patients_schema,
        "staffs": staffs_schema,
        "staff_schedule": staff_schedule_schema,
        "services_weekly": services_weekly_schema,
    }

    for name, schema in collections.items():
        try:
            # create_collection raises if it already exists; ignore that
            db.create_collection(name)
        except Exception:
            pass

        try:
            db.command("collMod", name, validator={"$jsonSchema": schema})
            print(f"✅ Created/updated collection '{name}' with validation.")
        except Exception as e:
            print(f"⚠️ Failed to apply validator to '{name}': {e}")


if __name__ == "__main__":
    create_collections()
