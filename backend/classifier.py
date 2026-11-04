from pathlib import Path
import joblib

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "ml" / "email_classifier.joblib"


def predict_email(text: str):
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Classifier model not found at {MODEL_PATH}. Run: python ml/train_model.py")
    model = joblib.load(MODEL_PATH)
    label = model.predict([text])[0]
    confidence = float(model.predict_proba([text])[0].max())
    return label, confidence
