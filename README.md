<h1 align="center"> MedTrack — AI-Powered Medicine Adherence Tracker</h1>

<p align="center">
<b>Codecure @ SPIRIT 2026 · IIT (BHU) Varanasi</b><br>
Predicting medication dropout before it happens
</p>

<hr>

<h2> Problem</h2>
<p>
Medication non-adherence affects nearly 50% of chronic patients in India. 
Existing apps only send reminders and fail to detect early behavioral patterns.
</p>

<h2> Solution</h2>
<p>
MedTrack is an AI-powered system that predicts adherence risk and triggers 
personalized interventions before patients drop off.
</p>

<ul>
<li> Photo-based dose verification (MobileNetV2)</li>
<li> Dropout prediction (XGBoost)</li>
<li> Explainable AI (SHAP)</li>
<li> Smart intervention engine</li>
</ul>

<hr>

<h2>🧠 How It Works</h2>

<pre>
Patient → API → Feature Engineering → ML Model → SHAP → Intervention
</pre>

<hr>

<h2> Tech Stack</h2>

<table>
<tr><th>Layer</th><th>Technology</th></tr>
<tr><td>Backend</td><td>FastAPI</td></tr>
<tr><td>Database</td><td>SQLite → PostgreSQL</td></tr>
<tr><td>ML</td><td>XGBoost + scikit-learn</td></tr>
<tr><td>CV</td><td>OpenCV + MobileNetV2</td></tr>
<tr><td>Frontend</td><td>HTML/CSS/JS</td></tr>
<tr><td>Mobile</td><td>React Native</td></tr>
</table>

<hr>

<h2> Model Performance</h2>
<ul>
<li>ROC-AUC: ~0.87</li>
<li>Precision: ~0.79</li>
<li>Recall: ~0.74</li>
</ul>

<hr>

<h2> Setup</h2>

<pre>
git clone https://github.com/YOURNAME/medtrack.git
cd medtrack
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
</pre>

<hr>

<h2> Impact</h2>
<ul>
<li>Targets India's chronic disease burden</li>
<li>Works in low-connectivity environments</li>
<li>Reduces caregiver workload</li>
</ul>

<hr>

<h2> Built For</h2>
<p><b>Codecure @ SPIRIT 2026</b><br>IIT (BHU) Varanasi</p>

<hr>

<p align="center">⭐ Star this repo if you like it</p>
