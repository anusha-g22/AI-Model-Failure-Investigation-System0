
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from database import get_connection

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "chroma_db"

client = chromadb.PersistentClient(path=str(CHROMA_DIR))

collection = client.get_or_create_collection(
    name="failure_investigation",
    embedding_function=DefaultEmbeddingFunction(),
    metadata={"hnsw:space": "cosine"}
)


def sync_failures():
    """Copy historical failures from MySQL into ChromaDB."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                f.failure_id,
                p.prediction_id,
                e.subject,
                e.email_text,
                p.predicted_class,
                ar.actual_class,
                ft.failure_type_name,
                f.description
            FROM failures f
            JOIN predictions p
                ON f.prediction_id = p.prediction_id
            JOIN emails e
                ON p.email_id = e.email_id
            JOIN actual_results ar
                ON p.prediction_id = ar.prediction_id
            JOIN failure_types ft
                ON f.failure_type_id = ft.failure_type_id
        """)

        rows = cursor.fetchall()

        for row in rows:
            document = (
                f"Subject: {row['subject'] or ''}\n"
                f"Email: {row['email_text']}\n"
                f"Predicted: {row['predicted_class']}\n"
                f"Actual: {row['actual_class']}\n"
                f"Failure type: {row['failure_type_name']}\n"
                f"Description: {row['description']}"
            )

            collection.upsert(
                ids=[f"failure_{row['failure_id']}"],
                documents=[document],
                metadatas=[{
                    "failure_id": row["failure_id"],
                    "prediction_id": row["prediction_id"],
                    "failure_type": row["failure_type_name"]
                }]
            )

        return len(rows)

    finally:
        cursor.close()
        conn.close()


def search_similar_failures(query, limit=5):
    """Search for semantically similar historical failures."""
    if not query.strip():
        return []

    count = collection.count()

    if count == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(limit, count),
        include=["documents", "metadatas", "distances"]
    )

    matches = []

    for document, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        matches.append({
            "document": document,
            "metadata": metadata,
            "similarity_score": round(
                max(0.0, min(1.0, 1.0 - distance)), 4
            )
        })

    return matches


if __name__ == "__main__":
    total = sync_failures()

    print(f"Synced {total} failure records from MySQL")
    print(f"Total vectors in ChromaDB: {collection.count()}")

    query = "Bank statement classified incorrectly"

    print(f"\nSearching for: {query}")

    for result in search_similar_failures(query):
        print("\n--------------------------")
        print("Similarity:", result["similarity_score"])
        print("Metadata:", result["metadata"])
        print("Document:", result["document"])
