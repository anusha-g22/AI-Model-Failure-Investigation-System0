
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from mysql.connector import Error

from database import get_connection
from classifier import predict_email
from vector_store import (
    collection,
    sync_failures,
    search_similar_failures
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Synchronize existing MySQL failures when the API starts.
    sync_failures()
    yield


app = FastAPI(
    title="AI Model Failure Investigation System",
    version="1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)


class EmailInput(BaseModel):
    sender: str = ""
    subject: str = Field(min_length=1)
    email_text: str = Field(min_length=1)


class VerificationInput(BaseModel):
    prediction_id: int
    actual_class: str
    user_id: int
    comment: str = ""


@app.get("/api/health")
def health():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()

        return {
            "status": "ok",
            "mysql": "connected",
            "vectors": collection.count()
        }
    finally:
        conn.close()


@app.get("/api/dashboard")
def dashboard():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT COUNT(*) AS total_predictions
            FROM predictions
        """)
        total = cursor.fetchone()["total_predictions"]

        cursor.execute("""
            SELECT
                COUNT(*) AS verified_predictions,
                COALESCE(SUM(is_correct = 1), 0)
                    AS correct_predictions,
                COALESCE(SUM(is_correct = 0), 0)
                    AS failed_predictions,
                ROUND(100 * AVG(is_correct), 2)
                    AS accuracy_percent
            FROM actual_results
        """)
        stats = cursor.fetchone()

        return {
            "total_predictions": total,
            **stats
        }
    finally:
        cursor.close()
        conn.close()


@app.post("/api/analyze")
def analyze_email(data: EmailInput):
    result = predict_email(
        data.subject + " " + data.email_text
    )

    # Model 2 is the existing Email Classification Model.
    model_id = 2

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO emails
                (sender, subject, email_text, metadata)
            VALUES (%s, %s, %s, JSON_OBJECT(
                'source', 'frontend'
            ))
        """, (
            data.sender,
            data.subject,
            data.email_text
        ))

        email_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO predictions
                (model_id, email_id,
                 predicted_class, confidence_score)
            VALUES (%s, %s, %s, %s)
        """, (
            model_id,
            email_id,
            result["predicted_class"],
            result["confidence_score"]
        ))

        prediction_id = cursor.lastrowid
        conn.commit()

    except Error as error:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
    finally:
        cursor.close()
        conn.close()

    similar = search_similar_failures(
        data.subject + " " + data.email_text
    )

    return {
        "email_id": email_id,
        "prediction_id": prediction_id,
        **result,
        "similar_failures": similar
    }


@app.get("/api/search")
def search_failures(
    q: str = Query(min_length=1),
    limit: int = Query(default=5, ge=1, le=20)
):
    return {
        "query": q,
        "results": search_similar_failures(q, limit)
    }


@app.get("/api/failures")
def get_failures():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT *
            FROM v_failure_investigation
            ORDER BY failure_id DESC
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


@app.post("/api/verify")
def verify_prediction(data: VerificationInput):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.callproc(
            "sp_record_actual_result",
            [
                data.prediction_id,
                data.actual_class,
                data.user_id,
                data.comment
            ]
        )

        results = []
        for stored_result in cursor.stored_results():
            results.extend(stored_result.fetchall())

        # The stored procedure commits its own transaction.
        response = results[0] if results else {
            "prediction_id": data.prediction_id,
            "status": "verified"
        }

    except Error as error:
        conn.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
    finally:
        cursor.close()
        conn.close()

    # Refresh the vector database after verification.
    sync_failures()

    return response


@app.get("/api/lineage/{prediction_id}")
def get_lineage(prediction_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT *
            FROM data_lineage
            WHERE prediction_id = %s
        """, (prediction_id,))

        result = cursor.fetchone()

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Lineage not found. Verify the prediction first."
            )

        return result
    finally:
        cursor.close()
        conn.close()
