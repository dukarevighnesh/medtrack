from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api import patients, doses, predictions, notifications

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MedTrack API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router, prefix="/api/patients", tags=["patients"])
app.include_router(doses.router, prefix="/api/doses", tags=["doses"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["predictions"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "MedTrack API"}
