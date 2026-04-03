from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
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
