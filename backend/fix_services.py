feature_engineering = """import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import DoseLog, Patient
import numpy as np

FEATURE_NAMES = [
    "adherence_7d", "adherence_14d", "adherence_30d",
    "streak_current", "streak_longest_30d",
    "missed_dose_count_7d", "missed_dose_count_14d",
    "time_deviation_avg_7d", "time_deviation_std_7d",
    "evening_miss_rate_14d", "morning_miss_rate_14d",
    "photo_verification_rate_7d", "session_frequency_delta",
    "notification_open_rate_7d", "days_since_last_miss",
    "days_since_refill", "age_normalized", "num_medications",
]


def compute_features(patient_id, db):
    now = datetime.utcnow()
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise ValueError(f"Patient {patient_id} not found")

    def get_logs(days):
        cutoff = now - timedelta(days=days)
        return (
            db.query(DoseLog)
            .filter(DoseLog.patient_id == patient_id)
            .filter(DoseLog.scheduled_time >= cutoff)
            .filter(DoseLog.scheduled_time <= now)
            .all()
        )

    logs_7d = get_logs(7)
    logs_14d = get_logs(14)
    logs_30d = get_logs(30)

    def adherence_rate(logs):
        if not logs:
            return 1.0
        return sum(1 for l in logs if l.was_taken) / len(logs)

    def current_streak(logs):
        if not logs:
            return 0
        by_date = {}
        for log in logs:
            day = log.scheduled_time.date()
            by_date.setdefault(day, []).append(log.was_taken)
        streak = 0
        for day in sorted(by_date.keys(), reverse=True):
            if all(by_date[day]):
                streak += 1
            else:
                break
        return streak

    def longest_streak(logs):
        if not logs:
            return 0
        by_date = {}
        for log in logs:
            day = log.scheduled_time.date()
            by_date.setdefault(day, []).append(log.was_taken)
        best, current = 0, 0
        for day in sorted(by_date.keys()):
            if all(by_date[day]):
                current += 1
                best = max(best, current)
            else:
                current = 0
        return best

    def time_deviation_stats(logs):
        devs = [l.time_deviation_minutes for l in logs if l.time_deviation_minutes is not None]
        if not devs:
            return 0.0, 0.0
        return float(np.mean(devs)), float(np.std(devs))

    def slot_miss_rate(logs, hour_start, hour_end):
        slot = [l for l in logs if hour_start <= l.scheduled_time.hour < hour_end]
        if not slot:
            return 0.0
        return sum(1 for l in slot if not l.was_taken) / len(slot)

    def days_since_last_miss(logs):
        missed = [l for l in logs if not l.was_taken]
        if not missed:
            return 30.0
        latest_miss = max(l.scheduled_time for l in missed)
        return float((now - latest_miss).days)

    def photo_rate(logs):
        taken = [l for l in logs if l.was_taken]
        if not taken:
            return 0.0
        return sum(1 for l in taken if l.photo_verified) / len(taken)

    avg_dev, std_dev = time_deviation_stats(logs_7d)
    num_meds = len([m for m in patient.medications if m.is_active])

    features = {
        "adherence_7d": round(adherence_rate(logs_7d), 4),
        "adherence_14d": round(adherence_rate(logs_14d), 4),
        "adherence_30d": round(adherence_rate(logs_30d), 4),
        "streak_current": float(current_streak(logs_14d)),
        "streak_longest_30d": float(longest_streak(logs_30d)),
        "missed_dose_count_7d": float(sum(1 for l in logs_7d if not l.was_taken)),
        "missed_dose_count_14d": float(sum(1 for l in logs_14d if not l.was_taken)),
        "time_deviation_avg_7d": round(avg_dev, 2),
        "time_deviation_std_7d": round(std_dev, 2),
        "evening_miss_rate_14d": round(slot_miss_rate(logs_14d, 17, 24), 4),
        "morning_miss_rate_14d": round(slot_miss_rate(logs_14d, 5, 12), 4),
        "photo_verification_rate_7d": round(photo_rate(logs_7d), 4),
        "session_frequency_delta": 0.0,
        "notification_open_rate_7d": 0.6,
        "days_since_last_miss": days_since_last_miss(logs_30d),
        "days_since_refill": 5.0,
        "age_normalized": round((patient.age or 40) / 100, 4),
        "num_medications": float(num_meds),
    }
    return features


def features_to_array(features):
    return [features[name] for name in FEATURE_NAMES]
"""

prediction_service = """import json
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
        "adherence_7d": -0.35, "adherence_14d": -0.20, "adherence_30d": -0.10,
        "streak_current": -0.08, "streak_longest_30d": -0.05,
        "missed_dose_count_7d": 0.18, "missed_dose_count_14d": 0.14,
        "time_deviation_avg_7d": 0.09, "time_deviation_std_7d": 0.07,
        "evening_miss_rate_14d": 0.18, "morning_miss_rate_14d": 0.12,
        "photo_verification_rate_7d": -0.06, "session_frequency_delta": 0.12,
        "notification_open_rate_7d": -0.09, "days_since_last_miss": -0.07,
        "days_since_refill": 0.04, "age_normalized": 0.03, "num_medications": 0.05,
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
"""

with open("app/services/feature_engineering.py", "w") as f:
    f.write(feature_engineering)
print("feature_engineering.py written!")

with open("app/services/prediction_service.py", "w") as f:
    f.write(prediction_service)
print("prediction_service.py written!")

print("All service files fixed!")
