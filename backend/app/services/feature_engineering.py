import json
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
