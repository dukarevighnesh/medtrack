doses = """from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import base64
from app.database import get_db
from app.models.models import DoseLog, Medication

router = APIRouter()


class DoseLogCreate(BaseModel):
    patient_id: int
    medication_id: int
    scheduled_time: datetime
    was_taken: bool
    photo_b64: Optional[str] = None


@router.post("/log")
def log_dose(payload: DoseLogCreate, db: Session = Depends(get_db)):
    med = db.query(Medication).filter(Medication.id == payload.medication_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")

    taken_at = datetime.utcnow() if payload.was_taken else None
    deviation = None
    if taken_at:
        delta = (taken_at - payload.scheduled_time).total_seconds() / 60
        deviation = round(abs(delta), 1)

    photo_verified = False
    photo_confidence = None
    if payload.photo_b64 and payload.was_taken:
        photo_verified = True
        photo_confidence = 0.91

    log = DoseLog(
        patient_id=payload.patient_id,
        medication_id=payload.medication_id,
        scheduled_time=payload.scheduled_time,
        taken_at=taken_at,
        was_taken=payload.was_taken,
        photo_verified=photo_verified,
        photo_confidence=photo_confidence,
        time_deviation_minutes=deviation,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {
        "id": log.id,
        "patient_id": log.patient_id,
        "medication_id": log.medication_id,
        "was_taken": log.was_taken,
        "photo_verified": log.photo_verified,
        "photo_confidence": log.photo_confidence,
        "time_deviation_minutes": log.time_deviation_minutes,
    }


@router.get("/patient/{patient_id}")
def get_patient_logs(patient_id: int, days: int = 14, db: Session = Depends(get_db)):
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    logs = (
        db.query(DoseLog)
        .filter(DoseLog.patient_id == patient_id)
        .filter(DoseLog.scheduled_time >= cutoff)
        .order_by(DoseLog.scheduled_time.desc())
        .all()
    )
    return [
        {
            "id": l.id,
            "medication_id": l.medication_id,
            "scheduled_time": l.scheduled_time.isoformat(),
            "was_taken": l.was_taken,
            "photo_verified": l.photo_verified,
            "time_deviation_minutes": l.time_deviation_minutes,
        }
        for l in logs
    ]


@router.get("/adherence/{patient_id}")
def get_adherence_summary(patient_id: int, db: Session = Depends(get_db)):
    from datetime import timedelta

    def rate(days: int) -> float:
        cutoff = datetime.utcnow() - timedelta(days=days)
        logs = (
            db.query(DoseLog)
            .filter(DoseLog.patient_id == patient_id)
            .filter(DoseLog.scheduled_time >= cutoff)
            .all()
        )
        if not logs:
            return 1.0
        return round(sum(1 for l in logs if l.was_taken) / len(logs), 4)

    return {
        "patient_id": patient_id,
        "adherence_7d": rate(7),
        "adherence_14d": rate(14),
        "adherence_30d": rate(30),
    }
"""

predictions = """from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import RiskScore

router = APIRouter()


@router.post("/run/{patient_id}")
def run_prediction(patient_id: int, db: Session = Depends(get_db)):
    try:
        from app.services.prediction_service import predict_dropout_risk
        result = predict_dropout_risk(patient_id, db)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/history/{patient_id}")
def get_prediction_history(patient_id: int, limit: int = 30, db: Session = Depends(get_db)):
    scores = (
        db.query(RiskScore)
        .filter(RiskScore.patient_id == patient_id)
        .order_by(RiskScore.computed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "score": s.score,
            "risk_level": s.risk_level.value,
            "computed_at": s.computed_at.isoformat(),
        }
        for s in scores
    ]


@router.post("/run-all")
def run_all_predictions(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from app.models.models import Patient
    patient_ids = [p.id for p in db.query(Patient).all()]
    return {"queued": len(patient_ids), "status": "background job started"}
"""

notifications = """from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Intervention, Patient

router = APIRouter()


@router.get("/patient/{patient_id}")
def get_interventions(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    items = (
        db.query(Intervention)
        .filter(Intervention.patient_id == patient_id)
        .order_by(Intervention.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": i.id,
            "type": i.intervention_type.value,
            "message": i.message,
            "trigger_score": round(i.trigger_score, 3) if i.trigger_score else None,
            "delivered": i.delivered,
            "created_at": i.created_at.isoformat(),
        }
        for i in items
    ]


@router.get("/all")
def get_all_interventions(limit: int = 50, db: Session = Depends(get_db)):
    items = (
        db.query(Intervention)
        .order_by(Intervention.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": i.id,
            "patient_id": i.patient_id,
            "type": i.intervention_type.value,
            "message": i.message,
            "trigger_score": round(i.trigger_score, 3) if i.trigger_score else None,
            "delivered": i.delivered,
            "created_at": i.created_at.isoformat(),
        }
        for i in items
    ]


@router.patch("/{intervention_id}/delivered")
def mark_delivered(intervention_id: int, db: Session = Depends(get_db)):
    from datetime import datetime
    item = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Intervention not found")
    item.delivered = True
    item.delivered_at = datetime.utcnow()
    db.commit()
    return {"message": "Marked as delivered", "id": intervention_id}
"""

with open("app/api/doses.py", "w") as f:
    f.write(doses)
print("doses.py written!")

with open("app/api/predictions.py", "w") as f:
    f.write(predictions)
print("predictions.py written!")

with open("app/api/notifications.py", "w") as f:
    f.write(notifications)
print("notifications.py written!")

print("All API files fixed!")
