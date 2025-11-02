import requests

payload = {
  "week": 10,
  "month": 3,
  "service": "emergency",
  "available_beds": 30,
  "patients_request": 70,
  "patients_admitted": 45,
  "patients_refused": 25,
  "patient_satisfaction": 85,
  "staff_morale": 75,
  "event": "flu"
}

response = requests.post("http://127.0.0.1:8000/services-weekly", json=payload)
print(response.status_code, response.json())
