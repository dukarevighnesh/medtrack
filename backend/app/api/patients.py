from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
from app.database import get_db
from app.models.models import Patient, Medication

router = APIRouter()


class PatientCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    age: Optional[int] = None
    language: str = "en"
    caregiver_phone: Optional[str] = None


class MedicationCreate(BaseModel):
    patient_id: int
    name: str
    dosage: str
    frequency: int
    schedule_times: list
    instructions: Optional[str] = ""


@router.post("/")
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    existing = db.query(Patient).filter(Patient.phone == payload.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    patient = Patient(
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        age=payload.age,
        language=payload.language,
        caregiver_phone=payload.caregiver_phone,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return {"id": patient.id, "name": patient.name, "message": "Patient registered successfully"}


@router.get("/all")
def list_patients(db: Session = Depends(get_db)):
    patients = db.query(Patient).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "phone": p.phone,
            "age": p.age,
        }
        for p in patients
    ]


@router.post("/medication")
def add_medication(payload: MedicationCreate, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    med = Medication(
        patient_id=payload.patient_id,
        name=payload.name,
        dosage=payload.dosage,
        frequency=payload.frequency,
        schedule_times=json.dumps(payload.schedule_times),
        instructions=payload.instructions,
    )
    db.add(med)
    db.commit()
    db.refresh(med)
    return {"id": med.id, "name": med.name, "message": "Medication added successfully"}


@router.get("/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "id": patient.id,
        "name": patient.name,
        "phone": patient.phone,
        "age": patient.age,
        "language": patient.language,
        "caregiver_phone": patient.caregiver_phone,
        "medications": [
            {
                "id": m.id,
                "name": m.name,
                "dosage": m.dosage,
                "frequency": m.frequency,
                "schedule_times": json.loads(m.schedule_times) if m.schedule_times else [],
                "instructions": m.instructions,
                "is_active": m.is_active,
            }
            for m in patient.medications if m.is_active
        ],
    }


@router.delete("/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(patient)
    db.commit()
    return {"message": "Patient deleted"}
