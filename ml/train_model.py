from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "training_data.csv"
MODEL_PATH = BASE_DIR / "email_classifier.joblib"


def main():
    data = pd.read_csv(DATA_PATH)
    if not {"text", "label"}.issubset(data.columns):
        raise ValueError("training_data.csv must contain text and label columns")
    data = data.dropna(subset=["text", "label"])
    texts = data["text"].astype(str)
    labels = data["label"].astype(str).str.upper()
    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.25, random_state=42, stratify=labels
    )
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode")),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    model.fit(x_train, y_train)
    print("Holdout evaluation:")
    print(classification_report(y_test, model.predict(x_test), zero_division=0))
    model.fit(texts, labels)
    joblib.dump(model, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
