import os
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from mysql.connector import Error
from pydantic import BaseModel, Field

from classifier import predict_email
from database import get_connection
from vector_store import collection_count, index_existing_records, search_cases, upsert_case

app = FastAPI(title="AI Model Failure Investigation System", version="2.0")
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins if origin.strip()],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

class AnalyzeBody(BaseModel):
    sender: str = ""
    subject: str = Field(default="", max_length=255)
    email_text: str = Field(min_length=1)
    model_id: int

class VerifyBody(BaseModel):
    prediction_id: int
    actual_class: str
    user_id: int
    comment: str = ""

class SearchBody(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)


def current_user():
    user_id = os.getenv("DEMO_USER_ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    return {"user_id": int(user_id), "role": os.getenv("DEMO_USER_ROLE", "admin")}


def admin_required(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@app.get("/api/health")
def health():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        return {"status": "ok", "database": "connected", "vector_count": collection_count()}
    finally:
        conn.close()


@app.get("/api/dashboard")
def dashboard(user=Depends(current_user)):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT COUNT(*) AS total_predictions FROM predictions")
        total = cur.fetchone()["total_predictions"]
        cur.execute("""
            SELECT COUNT(*) AS verified,
                   COALESCE(SUM(is_correct = 1), 0) AS correct,
                   COALESCE(SUM(is_correct = 0), 0) AS failures,
                   ROUND(100 * COALESCE(AVG(is_correct), 0), 2) AS accuracy
            FROM actual_results
        """)
        stats = cur.fetchone()
        return {
            "total_predictions": total,
            "verified_predictions": stats["verified"],
            "correct_predictions": stats["correct"],
            "failed_predictions": stats["failures"],
            "accuracy_percent": float(stats["accuracy"] or 0),
            "indexed_vectors": collection_count(),
        }
    finally:
        cur.close()
        conn.close()


@app.get("/api/models")
def models(user=Depends(current_user)):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT model_id, model_name, model_version FROM models ORDER BY model_id")
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.get("/api/predictions")
def predictions(user=Depends(current_user)):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT p.prediction_id, p.model_id, p.email_id, p.predicted_class,
                   p.confidence_score, p.predicted_at, ar.actual_class, ar.is_correct
            FROM predictions p
            LEFT JOIN actual_results ar ON ar.prediction_id = p.prediction_id
            ORDER BY p.prediction_id DESC
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.get("/api/failures")
def failures(user=Depends(current_user)):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT f.failure_id, f.prediction_id, e.subject, p.predicted_class,
                   ar.actual_class, ft.failure_type_name, f.description
            FROM failures f
            JOIN predictions p ON p.prediction_id = f.prediction_id
            JOIN emails e ON e.email_id = p.email_id
            JOIN actual_results ar ON ar.prediction_id = p.prediction_id
            JOIN failure_types ft ON ft.failure_type_id = f.failure_type_id
            ORDER BY f.failure_id DESC
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.get("/api/lineage")
def lineage(user=Depends(current_user)):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT lineage_id, prediction_id, email_id, dataset_id, model_id,
                   model_version, actual_id, failure_id, feedback_id
            FROM data_lineage ORDER BY lineage_id DESC
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/api/analyze")
@app.post("/api/predict")
def analyze(body: AnalyzeBody, user=Depends(current_user)):
    label, confidence = predict_email(body.email_text + "\n" + body.subject)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT model_id FROM models WHERE model_id=%s", (body.model_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=400, detail="Selected model_id does not exist")
        cur.execute("""
            INSERT INTO emails(sender, subject, email_text, metadata)
            VALUES(%s, %s, %s, JSON_OBJECT('source', 'react_frontend'))
        """, (body.sender, body.subject, body.email_text))
        email_id = cur.lastrowid
        cur.execute("""
            INSERT INTO predictions(model_id, email_id, predicted_class, confidence_score)
            VALUES(%s, %s, %s, %s)
        """, (body.model_id, email_id, label, confidence))
        prediction_id = cur.lastrowid
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Error as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Could not save prediction: {exc}")
    finally:
        cur.close()
        conn.close()

    upsert_case(
        f"prediction-{prediction_id}",
        f"Subject: {body.subject}\nEmail: {body.email_text}\nPredicted: {label}",
        {"prediction_id": prediction_id, "email_id": email_id,
         "model_id": body.model_id, "predicted_class": label,
         "record_type": "prediction"},
    )
    return {"prediction_id": prediction_id, "email_id": email_id,
            "predicted_class": label, "confidence_score": confidence}


@app.post("/api/search")
def vector_search(body: SearchBody, user=Depends(current_user)):
    return {"results": search_cases(body.query, body.limit)}


@app.get("/api/search")
def vector_search_get(q: str = Query(min_length=1), limit: int = Query(default=5, ge=1, le=20),
                      user=Depends(current_user)):
    return {"query": q, "results": search_cases(q, limit)}


@app.post("/api/verify")
def verify(body: VerifyBody, user=Depends(current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.callproc("sp_record_actual_result",
                     [body.prediction_id, body.actual_class, body.user_id, body.comment])
        results = []
        for result in cur.stored_results():
            results.extend(result.fetchall())
        conn.commit()
    except Error as exc:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        cur.close()
        conn.close()

    db = get_connection()
    try:
        indexed = index_existing_records(db)
    finally:
        db.close()
    return {"verification": results, "indexed_records": indexed}


@app.post("/api/admin/index-vectors")
def index_vectors(user=Depends(admin_required)):
    conn = get_connection()
    try:
        indexed = index_existing_records(conn)
        return {"indexed_records": indexed, "vector_count": collection_count()}
    finally:
        conn.close()
