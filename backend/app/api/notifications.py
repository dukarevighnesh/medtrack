from fastapi import APIRouter, Depends, HTTPException
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
