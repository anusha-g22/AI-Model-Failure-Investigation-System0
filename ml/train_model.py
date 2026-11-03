
from pathlib import Path
import joblib

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "email_classifier.pkl"

# Synthetic examples for a working demonstration.
# Replace with a larger, representative labeled dataset later.
examples = {
    "FINANCE": [
        "Your bank statement is available",
        "Credit card payment is due tomorrow",
        "Your loan EMI is due this week",
        "Your savings account balance was updated",
        "Monthly financial statement attached",
        "Your bank transfer was successful",
        "Invoice payment confirmation received",
        "Your account transaction summary is ready",
        "Payment receipt for your purchase",
        "Your loan repayment schedule is available",
    ],
    "WORK": [
        "Team meeting scheduled tomorrow",
        "Please review the project report",
        "Weekly team status update",
        "The manager scheduled a conference call",
        "Please submit your assignment report",
        "Project deadline has been extended",
        "Join the team discussion this afternoon",
        "Your office meeting agenda is attached",
        "Please review the presentation slides",
        "Employee performance review meeting",
    ],
    "SPAM": [
        "You won a free cash prize",
        "Claim your lottery winnings now",
        "Congratulations you won a million dollars",
        "Click here to collect your free reward",
        "You are selected for a surprise jackpot",
        "Urgent claim your prize immediately",
        "Free gift waiting for you click now",
        "You have won an exclusive lottery",
        "Get rich quickly with this secret offer",
        "Claim your guaranteed cash reward today",
    ],
    "PROMOTION": [
        "Special discount on your next purchase",
        "Our seasonal sale starts today",
        "Get twenty percent off selected products",
        "New collection available at discounted prices",
        "Exclusive member shopping offer",
        "Limited time sale on electronics",
        "Enjoy savings on your favorite products",
        "Weekend promotional offer for customers",
        "Buy one get one free this weekend",
        "Shop our latest product deals today",
    ],
}

texts = []
labels = []

for category, messages in examples.items():
    for message in messages:
        texts.append(message)
        labels.append(category)

X_train, X_test, y_train, y_test = train_test_split(
    texts,
    labels,
    test_size=0.25,
    random_state=42,
    stratify=labels
)

model = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
    ("classifier", LogisticRegression(max_iter=1000))
])

model.fit(X_train, y_train)

predictions = model.predict(X_test)

print("\nClassification report:")
print(classification_report(
    y_test,
    predictions,
    zero_division=0
))

# Retrain on all demonstration examples for the final prototype.
model.fit(texts, labels)

joblib.dump(model, MODEL_PATH)

print(f"\nModel saved to: {MODEL_PATH}")

sample = "Your credit card statement is ready"

print("\nSample prediction:")
print("Input:", sample)
print("Predicted class:", model.predict([sample])[0])
print("Confidence:", round(
    float(model.predict_proba([sample]).max()), 3
))
