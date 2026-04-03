import json
import pickle
from pathlib import Path
import numpy as np
from sqlalchemy.orm import Session
from app.models.models import RiskScore, RiskLevel, Intervention, InterventionType
from app.services.feature_engineering import compute_features, features_to_array, FEATURE_NAMES

MODEL_PATH = Path(__file__).parent.parent / "ml" / "model.pkl"
EXPLAINER_PATH = Path(__file__).parent.parent / "ml" / "shap_explainer.pkl"

THRESHOLD_LOW_MEDIUM = 0.35
THRESHOLD_MEDIUM_HIGH = 0.65


def predict_dropout_risk(patient_id, db):
    features = compute_features(patient_id, db)
    X = np.array([features_to_array(features)])

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Run train.py first.")

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    score = float(model.predict_proba(X)[0][1])

    if score < THRESHOLD_LOW_MEDIUM:
        risk_level = RiskLevel.LOW
    elif score < THRESHOLD_MEDIUM_HIGH:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.HIGH

    shap_dict = _compute_shap(X, features)

    risk_record = RiskScore(
        patient_id=patient_id,
        score=score,
        risk_level=risk_level,
        shap_values=json.dumps(shap_dict),
        features_snapshot=json.dumps(features),
    )
    db.add(risk_record)
    db.commit()
    db.refresh(risk_record)

    intervention = _trigger_intervention(patient_id, score, risk_level, shap_dict, db)

    return {
        "patient_id": patient_id,
        "score": round(score, 4),
        "risk_level": risk_level.value,
        "shap_values": shap_dict,
        "features": features,
        "intervention_triggered": intervention,
        "computed_at": risk_record.computed_at.isoformat(),
    }


def _compute_shap(X, features):
    try:
        if EXPLAINER_PATH.exists():
            import shap
            with open(EXPLAINER_PATH, "rb") as f:
                explainer = pickle.load(f)
            shap_values = explainer(X)
            vals = shap_values.values[0].tolist()
            return dict(zip(FEATURE_NAMES, [round(v, 4) for v in vals]))
    except Exception:
        pass

    weights = {
        "adherence_7d": -0.35,
        "adherence_14d": -0.20,
        "adherence_30d": -0.10,
        "streak_current": -0.08,
        "streak_longest_30d": -0.05,
        "missed_dose_count_7d": 0.18,
        "missed_dose_count_14d": 0.14,
        "time_deviation_avg_7d": 0.09,
        "time_deviation_std_7d": 0.07,
        "evening_miss_rate_14d": 0.18,
        "morning_miss_rate_14d": 0.12,
        "photo_verification_rate_7d": -0.06,
        "session_frequency_delta": 0.12,
        "notification_open_rate_7d": -0.09,
        "days_since_last_miss": -0.07,
        "days_since_refill": 0.04,
        "age_normalized": 0.03,
        "num_medications": 0.05,
    }
    return {k: round(features[k] * weights[k], 4) for k in FEATURE_NAMES}


def _trigger_intervention(patient_id, score, risk_level, shap_dict, db):
    if risk_level == RiskLevel.LOW:
        return None

    top_factor = max(shap_dict, key=lambda k: shap_dict[k])
    labels = {
        "adherence_7d": "declining 7-day adherence",
        "missed_dose_count_7d": "multiple missed doses this week",
        "evening_miss_rate_14d": "consistent evening dose misses",
        "session_frequency_delta": "reduced app engagement",
        "notification_open_rate_7d": "low notification open rate",
    }
    factor_label = labels.get(top_factor, top_factor.replace("_", " "))

    if risk_level == RiskLevel.MEDIUM:
        itype = InterventionType.CAREGIVER_ALERT
        message = f"Your family member may need a reminder. Concern: {factor_label}. Risk score: {score:.2f}."
    else:
        itype = InterventionType.PHARMACIST_CALLBACK
        message = f"High dropout risk detected (score: {score:.2f}). Primary concern: {factor_label}."

    intervention = Intervention(
        patient_id=patient_id,
        intervention_type=itype,
        trigger_score=score,
        message=message,
    )
    db.add(intervention)
    db.commit()
    return itype.value
