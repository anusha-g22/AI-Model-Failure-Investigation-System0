import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from sklearn.feature_extraction.text import HashingVectorizer

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PATH = BASE_DIR.parent / "chroma_db"
CHROMA_DIR = Path(os.getenv("CHROMA_PATH", str(DEFAULT_PATH)))
if not CHROMA_DIR.is_absolute():
    CHROMA_DIR = (BASE_DIR / CHROMA_DIR).resolve()

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = client.get_or_create_collection(
    name="failure_investigation",
    metadata={"hnsw:space": "cosine"},
)
_vectorizer = HashingVectorizer(
    n_features=384, alternate_sign=False, norm="l2",
    ngram_range=(1, 2), lowercase=True,
)


def _embed(texts):
    return _vectorizer.transform(texts).toarray().astype("float32").tolist()


def upsert_case(case_id: str, document: str, metadata: dict):
    safe = {
        key: value if isinstance(value, (str, int, float, bool)) else str(value)
        for key, value in metadata.items() if value is not None
    }
    text = document[:12000]
    collection.upsert(ids=[str(case_id)], documents=[text],
                      embeddings=_embed([text]), metadatas=[safe])


def search_cases(query: str, limit: int = 5):
    count = collection.count()
    if count == 0 or not query.strip():
        return []
    result = collection.query(
        query_embeddings=_embed([query]),
        n_results=min(max(1, limit), count),
        include=["documents", "metadatas", "distances"],
    )
    rows = []
    for i, case_id in enumerate(result.get("ids", [[]])[0]):
        rows.append({
            "id": case_id,
            "document": result["documents"][0][i],
            "metadata": result["metadatas"][0][i],
            "distance": result["distances"][0][i],
        })
    return rows


def collection_count():
    return collection.count()


def index_existing_records(connection):
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT p.prediction_id, p.email_id, p.model_id, p.predicted_class,
                   e.subject, e.email_text, ar.actual_class, f.failure_id,
                   f.description, ft.failure_type_name
            FROM predictions p
            JOIN emails e ON e.email_id = p.email_id
            LEFT JOIN actual_results ar ON ar.prediction_id = p.prediction_id
            LEFT JOIN failures f ON f.prediction_id = p.prediction_id
            LEFT JOIN failure_types ft ON ft.failure_type_id = f.failure_type_id
            ORDER BY p.prediction_id
        """)
        rows = cursor.fetchall()
        for row in rows:
            document = (
                f"Subject: {row.get('subject') or ''}\n"
                f"Email: {row.get('email_text') or ''}\n"
                f"Predicted: {row.get('predicted_class') or ''}\n"
                f"Actual: {row.get('actual_class') or 'Not verified'}\n"
                f"Failure: {row.get('description') or ''}"
            )
            upsert_case(
                f"prediction-{row['prediction_id']}", document, {
                    "prediction_id": row["prediction_id"],
                    "email_id": row["email_id"],
                    "model_id": row["model_id"],
                    "predicted_class": row["predicted_class"],
                    "actual_class": row.get("actual_class"),
                    "failure_id": row.get("failure_id"),
                    "failure_type": row.get("failure_type_name"),
                    "record_type": "historical_prediction",
                }
            )
        return len(rows)
    finally:
        cursor.close()


if __name__ == "__main__":
    from database import get_connection
    db = get_connection()
    try:
        indexed = index_existing_records(db)
        print(f"Indexed {indexed} prediction records.")
        print(f"Total vectors: {collection_count()}")
    finally:
        db.close()
