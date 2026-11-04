# AI Model Failure Investigation and Data Lineage System

A DBMS project integrating email classification, prediction verification, failure investigation, relational data lineage, and vector retrieval of historical prediction records.

## Stack
- MySQL 8.0+
- Python 3.11, FastAPI, Uvicorn
- React 19, Vite
- scikit-learn (TF-IDF + Logistic Regression)
- ChromaDB with local HashingVectorizer embeddings

## Features
- Email classification into FINANCE, WORK, PROMOTION, and SPAM.
- MySQL persistence for emails and predictions.
- Ground-truth verification through a MySQL stored procedure.
- Automatic correctness evaluation and failure creation through database triggers.
- Investigator feedback and lineage records.
- ChromaDB indexing/search of historical prediction records.
- Dashboard metrics, predictions, failures, and lineage pages.

## Repository structure
```text
backend/       FastAPI API, MySQL connection, classifier, ChromaDB integration
frontend/      React + Vite interface
ml/            training data, model training script, generated model artifact
sql/           DDL, sample data, procedures, triggers, views, example queries
```

## Requirements (Windows 11)
Install Python 3.11, Node.js 22+, Git, and MySQL Server 8.0+. Start MySQL before running the application.

## 1. Clone
```powershell
git clone https://github.com/anusha-g22/AI-Model-Failure-Investigation-System.git
cd AI-Model-Failure-Investigation-System
```

## 2. Create the database
Use MySQL Workbench or the MySQL CLI. Execute these scripts in order on a **fresh development database**:

1. `sql/failure_lineage_ddl.sql`
2. `sql/failure_lineage_dml.sql`
3. `sql/failure_lineage_advanced.sql`

**Warning:** `failure_lineage_ddl.sql` begins with `DROP DATABASE IF EXISTS failure_lineage`; it deletes an existing database with that name. Back up any database you need before running it. The DML/advanced scripts insert demonstration rows and should be run only once on the fresh schema.

The scripts create sample users, models, datasets, emails, predictions, triggers, the `sp_record_actual_result` stored procedure, views, and sample verification records. After setup, you can run `sql/queries.sql` for portable checks of the tables, verified accuracy, failures, lineage, feedback, and routines.

## 3. Configure Python backend
```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Set `DB_PASSWORD` to your local MySQL password in `backend/.env`. Keep this file private; it is ignored by Git.

Generate the classifier artifact from the included data:
```powershell
python ..\ml\train_model.py
```

Start the API from the `backend` folder:
```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Check:
- Health: http://127.0.0.1:8000/api/health
- Swagger docs: http://127.0.0.1:8000/docs

### Demo authentication note
The checked-in UI/backend configuration uses a local demo-user guard. Configure `DEMO_USER_ID` to an existing row in `users` and `DEMO_USER_ROLE=admin` in `.env`. This is a local development convenience, not password-based login/logout or production authentication. The login/logout UI and token-based auth migration from the developer's separate local working copy are not part of this repository revision. Do not expose this demo configuration to the internet. Replace it with a reviewed password/token authentication flow before deployment.

## 4. Start React frontend
Open a second PowerShell window at the repository root:
```powershell
cd frontend
npm install
npm run dev
```
Open the Vite URL, usually http://localhost:5173. Keep both terminals open.

## 5. API and demonstration workflow
- `GET /api/health`: database/vector-store health.
- `GET /api/dashboard`: dashboard aggregates.
- `GET /api/models`, `GET /api/predictions`, `GET /api/failures`, `GET /api/lineage`: application records.
- `POST /api/analyze` (alias `POST /api/predict`): store an email and prediction. Body: `sender`, `subject`, `email_text`, `model_id`.
- `POST /api/verify`: call the stored procedure with `prediction_id`, `actual_class`, `user_id`, and `comment`.
- `POST /api/search`: similarity search with `query` and optional `limit`.
- `POST /api/admin/index-vectors`: index historical prediction rows; requires demo admin role.

Recommended demo: classify an email → verify it → inspect failures and lineage → search a phrase from a historical email → index historical rows.

## ML and vector-search limitations
The included classifier is a **small demonstration model**, not a production classifier. Accuracy depends on the quality and size of the labeled training data. The training script prints a held-out classification report and then refits the final model on all available examples. Expand the data and keep an untouched test set before making performance claims.

The vector store uses deterministic local HashingVectorizer text features. This avoids ChromaDB's default ONNX model download and DNS/cache failures. It is lexical feature hashing, not a transformer-based semantic embedding model; treat returned distances as approximate text similarity.

## Troubleshooting
**MySQL connection failure**
- Verify the MySQL service is running.
- Check DB settings in `backend/.env`.
- Confirm the database scripts completed without SQL errors.

**PowerShell blocks venv activation**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

**pip runs out of space on C:**
```powershell
New-Item -ItemType Directory -Force D:\PythonTemp, D:\PipCache
$env:TEMP = "D:\PythonTemp"
$env:TMP = "D:\PythonTemp"
$env:PIP_CACHE_DIR = "D:\PipCache"
pip install -r requirements.txt
```

**ChromaDB ONNX/Protobuf/download error**
- Ensure the updated `backend/vector_store.py` is being used.
- It supplies explicit local vectors instead of invoking the default embedding function.
- Back up a pre-existing `chroma_db` directory before changing embedding schemes.

## Security
Never commit `.env`, database dumps, personal data, local ChromaDB persistence, `.venv`, `node_modules`, or generated model artifacts. Use a dedicated least-privilege MySQL account where practical.

## Verification status
The developer's local run demonstrated successful prediction storage, verification, failure listing, lineage listing, vector similarity search, and indexing of 12 prediction records. Those local database rows are not included in the repository; each user creates their own database by following the setup steps above.
