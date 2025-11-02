# test_insert.py
from connect_db import get_database
from datetime import datetime

def test_insert_data():
    db = get_database()
    
    # Test 1: Insert valid staff document
    print("\n Test 1: Inserting valid staff...")
    try:
        staff_doc = {
            "staff_id": "S001",
            "staff_name": "Dr. John Smith",
            "role": "Doctor",
            "service": "Emergency"
        }
        result = db.staffs.insert_one(staff_doc)
        print(f" Success! Inserted staff with ID: {result.inserted_id}")
    except Exception as e:
        print(f" Failed: {e}")
    
    # Test 2: Try to insert INVALID staff (missing required field)
    print("\n Test 2: Inserting invalid staff (missing 'role')...")
    try:
        invalid_staff = {
            "staff_id": "S002",
            "staff_name": "Jane Doe",
            "service": "Surgery"
            # Missing "role" - should fail validation!
        }
        result = db.staffs.insert_one(invalid_staff)
        print(f" Unexpectedly succeeded: {result.inserted_id}")
        print("   (This means validation isn't enabled)")
    except Exception as e:
        print(f" Validation working! Rejected invalid data:")
        print(f"   {e}")
    
    # Test 3: Insert valid patient
    print("\nTest 3: Inserting valid patient...")
    try:
        patient_doc = {
            "patient_id": "P001",
            "name": "Alice Johnson",
            "age": 45,
            "arrival_date": datetime.now(),
            "service": "Cardiology",
            "satisfaction": 4
        }
        result = db.patients.insert_one(patient_doc)
        print(f"Success! Inserted patient with ID: {result.inserted_id}")
    except Exception as e:
        print(f" Failed: {e}")
    
    # Test 4: Count documents
    print("\n Document counts:")
    print(f"   Staffs: {db.staffs.count_documents({})}")
    print(f"   Patients: {db.patients.count_documents({})}")
    print(f"   Staff Schedule: {db.staff_schedule.count_documents({})}")
    print(f"   Services Weekly: {db.services_weekly.count_documents({})}")

if __name__ == "__main__":
    test_insert_data()