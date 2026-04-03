print("Step 1: Starting...")

import pickle
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from imblearn.over_sampling import SMOTE
import xgboost as xgb
import shap

print("Step 2: All imports done!")

rng = np.random.default_rng(42)
n = 2000
X = rng.random((n, 18))
y = (X[:, 0] + X[:, 5] > 1.0).astype(int)
print("Step 3: Data generated!")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
sm = SMOTE(random_state=42)
X_train, y_train = sm.fit_resample(X_train, y_train)
print("Step 4: Data balanced!")

model = xgb.XGBClassifier(
    n_estimators=100,
    random_state=42,
    eval_metric="logloss"
)
model.fit(X_train, y_train, verbose=False)
print("Step 5: Model trained!")

auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
print(f"Step 6: ROC-AUC = {auc:.4f}")

# Use absolute path — no more path errors
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "..", "backend", "app", "ml")
os.makedirs(OUT, exist_ok=True)
print(f"Step 7: Saving to folder: {OUT}")

with open(os.path.join(OUT, "model.pkl"), "wb") as f:
    pickle.dump(model, f)
print("Step 8: model.pkl saved!")

explainer = shap.TreeExplainer(model)
with open(os.path.join(OUT, "shap_explainer.pkl"), "wb") as f:
    pickle.dump(explainer, f)
print("Step 9: shap_explainer.pkl saved!")

print("")
print("=============================")
print("   TRAINING COMPLETE!")
print("=============================")
