
from pathlib import Path
import joblib

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "ml" / "email_classifier.pkl"

model = joblib.load(MODEL_PATH)


def predict_email(text):
    prediction = model.predict([text])[0]

    probabilities = model.predict_proba([text])[0]
    confidence = float(max(probabilities))

    return {
        "predicted_class": prediction,
        "confidence_score": round(confidence, 3)
    }


if __name__ == "__main__":
    result = predict_email(
        "Your bank account statement is ready"
    )
    print(result)
