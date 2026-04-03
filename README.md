MedTrack — AI-Powered Medicine Adherence Tracker

Codecure @ SPIRIT 2026 · IIT (BHU) Varanasi · Health-Tech Innovation Challenge


Why We Built This
India has one of the highest rates of medication non-adherence in the world. Studies show that nearly 50% of patients with chronic conditions like diabetes, hypertension, and cardiovascular disease stop taking their medication within the first year — not because they choose to, but because no one noticed they were slipping.
Existing apps send reminders. That is it.
MedTrack goes further. It watches for early warning signs — subtle drops in app engagement, irregular dose timing, missed evening doses — and predicts dropout before it happens. Then it automatically routes the patient to the right intervention: a motivational nudge, a caregiver alert, or a pharmacist callback. The right help, at the right time, before it is too late.
We chose this problem because it sits at the intersection of two things that matter deeply: technology that actually reaches people, and healthcare that does not wait for patients to fall through the cracks.

What Makes MedTrack Different
FeatureOther AppsMedTrackDose remindersYesYesDose loggingSometimesYesPhoto verificationRareYes — MobileNet CV modelDropout predictionNoYes — XGBoost ML modelExplainable AI (SHAP)NoYes — plain-language reasonsTiered interventionsNoYes — Push, Caregiver, PharmacistMultilingual supportRareYes — Hindi, English, regionalOffline-firstRareYesOpen sourceRareYes
Most adherence apps treat all patients the same. MedTrack learns from each patient's individual pattern and acts differently based on their specific risk profile. A patient who always misses evening doses gets different support than one whose app engagement has dropped — because those are different problems requiring different solutions.

Features

Photo-based dose verification — patient photographs their pill, a MobileNetV2 model confirms it is the right medication with a confidence score
14-day adherence heatmap — visual calendar of taken and missed doses per medication per day
ML dropout risk score — XGBoost classifier trained on 18 behavioural features outputs a 0 to 100 risk score daily
SHAP explainability — the top factors driving each patient score are shown in plain language, not just a number
Tiered intervention engine — Low risk gets a motivational push notification, Medium triggers a caregiver SMS, High queues a pharmacist callback
Full web dashboard — register patients, add medications, log doses, and run predictions from a browser
Multilingual — Hindi and English support, extensible to regional languages
REST API — fully documented FastAPI backend with Swagger UI at /docs


Tech Stack
LayerTechnologyWhyBackend APIFastAPI (Python)Async, fast, auto-generates API docsDatabaseSQLite to PostgreSQLSimple for prototype, production-ready swapML modelXGBoost + scikit-learnBest performance on tabular health dataExplainabilitySHAP TreeExplainerPer-prediction feature attributionClass balancingSMOTEHandles real-world 25% dropout ratePhoto verificationOpenCV + MobileNetV2Lightweight, runs on-deviceFrontendVanilla HTML/CSS/JSZero dependencies, works on any deviceMobileReact Native + ExpoCross-platform iOS and AndroidPush notificationsFirebase Cloud MessagingIndustry standard for health apps

ML Model — How It Works
The dropout prediction model is trained as a binary classifier. A patient is labelled as a dropout if they miss more than 40% of doses over 14 days.
18 features computed per patient per day:
FeatureDescriptionadherence_7dProportion of doses taken in last 7 daysadherence_14dProportion of doses taken in last 14 daysadherence_30dProportion of doses taken in last 30 daysstreak_currentConsecutive compliant daysmissed_dose_count_7dRaw miss count this weekevening_miss_rate_14dFraction of evening doses missedmorning_miss_rate_14dFraction of morning doses missedtime_deviation_avg_7dAverage minutes off scheduled timesession_frequency_deltaChange in app opens over last 3 daysnotification_open_rate_7dFraction of reminders openedphoto_verification_rate_7dHow often patient uses photo verificationdays_since_last_missDays since most recent missed dosedays_since_refillProxy for medication availability
Training pipeline:

Generate 2,000 synthetic patients with realistic adherence distributions
Apply SMOTE to balance the 25% dropout minority class
Train XGBoost with 300 estimators, learning rate 0.05
Evaluate with 5-fold stratified cross-validation
Build SHAP TreeExplainer for per-prediction explanations

Expected performance:

ROC-AUC: ~0.87
Precision (High risk): ~0.79
Recall (High risk): ~0.74


System Architecture
Patient logs dose (manual or photo)
           |
           v
   FastAPI /doses/log
   saves to PostgreSQL
   runs MobileNet pill classifier if photo provided
           |
           v
   Nightly batch job
   Feature Engineering Service
   computes 18 features per patient
           |
           v
   XGBoost Classifier
   outputs dropout probability 0.0 to 1.0
   SHAP TreeExplainer computes feature contributions
           |
           v
   Risk Tier Decision
   score < 0.35  -->  LOW    -->  Push nudge
   0.35 to 0.65  -->  MEDIUM -->  Caregiver SMS
   score > 0.65  -->  HIGH   -->  Pharmacist callback
           |
           v
   Intervention dispatched
   Patient sees plain-language explanation in app

Project Structure
medtrack/
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py                      FastAPI entry point
│       ├── database.py                  SQLAlchemy engine and session
│       ├── models/
│       │   └── models.py                Patient, Medication, DoseLog, RiskScore, Intervention
│       ├── api/
│       │   ├── patients.py              Patient registration and lookup
│       │   ├── doses.py                 Dose logging and photo verification
│       │   ├── predictions.py           ML inference endpoints
│       │   └── notifications.py         Intervention log
│       ├── services/
│       │   ├── feature_engineering.py   18-feature computation from dose history
│       │   └── prediction_service.py    XGBoost inference, SHAP, intervention dispatch
│       └── ml/
│           ├── model.pkl                Trained XGBoost model
│           └── shap_explainer.pkl       SHAP TreeExplainer
├── ml_training/
│   └── train.py                         Full training pipeline with evaluation report
├── mobile_screens/
│   ├── HomeScreen.tsx                   Today's doses with photo capture
│   └── RiskScreen.tsx                   Patient-facing risk score and SHAP factors
├── webapp/
│   └── index.html                       Full web dashboard, no framework needed
└── README.md

Installation and Setup
1. Clone the repository
bashgit clone https://github.com/YOURNAME/medtrack.git
cd medtrack
2. Set up the backend
bashcd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac or Linux
source venv/bin/activate

pip install -r requirements.txt
3. Train the ML model
bashcd ..
python ml_training/train.py
You will see the training log with ROC-AUC score and the model saved to backend/app/ml/
4. Start the API server
bashcd backend
uvicorn app.main:app --reload --port 8000
API docs available at http://localhost:8000/docs
5. Open the web dashboard
Open webapp/index.html in any browser. Click Test connection to verify the API is reachable.

API Endpoints
MethodEndpointDescriptionGET/healthHealth checkPOST/api/patients/Register new patientGET/api/patients/allList all patientsGET/api/patients/{id}Get patient with medicationsPOST/api/patients/medicationAdd medication to patientPOST/api/doses/logLog a dose with optional photoGET/api/doses/patient/{id}Get dose historyGET/api/doses/adherence/{id}Get 7, 14, 30 day adherence ratesPOST/api/predictions/run/{id}Run ML prediction for patientGET/api/predictions/history/{id}Risk score trend over timePOST/api/predictions/run-allBatch predict all patientsGET/api/notifications/patient/{id}Get intervention log

Scalability
MedTrack is designed to scale from a 10-patient pilot to a 100,000-patient deployment without architectural changes.
Horizontal scaling — FastAPI workers are stateless and scale behind a load balancer. Each request is independent.
Async batch processing — Nightly risk predictions run as background jobs, not on the request path. Adding 10,000 patients does not slow down the API.
Database — SQLite for development swaps to PostgreSQL with a single environment variable change. Read replicas handle analytics queries.
ML model — XGBoost inference takes under 5ms per patient. Batch prediction for 10,000 patients completes in under a minute.
Mobile — React Native app works offline and syncs when reconnected, making it viable for rural areas with poor connectivity.
Multilingual — Language is stored per patient. Adding a new language requires only translation files, not code changes.

Societal Impact

Targets India's chronic disease burden — 77 million diabetics, 220 million hypertension patients
Designed for rural accessibility — offline-first, voice-ready, vernacular language support
Reduces pharmacist and caregiver workload through intelligent triage
SHAP explainability gives patients agency over their own health data
Privacy-first — photos are verified server-side and deleted immediately


Ethical Considerations

Risk scores are never shown as you might stop your medication — framed as a positive health check score to avoid anxiety
SHAP explanations give patients plain-language reasons so they can act, not just a number
Caregiver and pharmacist alerts require patient consent at onboarding
No patient data is shared with third parties


Built For
Codecure @ SPIRIT 2026
IIT (BHU) Varanasi — Annual Techno-Pharma Conference
Past partners: Sun Pharma · Marichi Ventures · A2Z4.0
