content = """from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InterventionType(str, enum.Enum):
    PUSH_NOTIFICATION = "push_notification"
    CAREGIVER_ALERT = "caregiver_alert"
    PHARMACIST_CALLBACK = "pharmacist_callback"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=True)
    age = Column(Integer)
    language = Column(String, default="en")
    fcm_token = Column(String, nullable=True)
    caregiver_phone = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    medications = relationship("Medication", back_populates="patient")
    dose_logs = relationship("DoseLog", back_populates="patient")
    risk_scores = relationship("RiskScore", back_populates="patient")
    interventions = relationship("Intervention", back_populates="patient")


class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    name = Column(String, nullable=False)
    dosage = Column(String)
    frequency = Column(Integer)
    schedule_times = Column(Text)
    instructions = Column(String)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="medications")
    dose_logs = relationship("DoseLog", back_populates="medication")


class DoseLog(Base):
    __tablename__ = "dose_logs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=False)
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    taken_at = Column(DateTime(timezone=True), nullable=True)
    was_taken = Column(Boolean, default=False)
    photo_verified = Column(Boolean, default=False)
    photo_url = Column(String, nullable=True)
    photo_confidence = Column(Float, nullable=True)
    time_deviation_minutes = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="dose_logs")
    medication = relationship("Medication", back_populates="dose_logs")


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    score = Column(Float, nullable=False)
    risk_level = Column(Enum(RiskLevel), nullable=False)
    shap_values = Column(Text, nullable=True)
    features_snapshot = Column(Text, nullable=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="risk_scores")


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    intervention_type = Column(Enum(InterventionType), nullable=False)
    trigger_score = Column(Float)
    message = Column(Text)
    delivered = Column(Boolean, default=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="interventions")
"""

with open("app/models/models.py", "w") as f:
    f.write(content)

print("models.py written successfully!")
