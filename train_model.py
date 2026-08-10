"""
train_model.py
----------------
Trains a Random Forest classifier to predict traffic congestion level
(LOW / MEDIUM / HIGH) from traffic features, and saves the trained
model + encoders to traffic_model.pkl.

Run this once before starting the backend:
    python ml/train_model.py
"""

import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "traffic_data.csv")
MODEL_PATH = os.path.join(BASE_DIR, "ml", "traffic_model.pkl")


def train():
    print("Loading dataset from:", DATA_PATH)
    df = pd.read_csv(DATA_PATH)

    # -------------------------------------------------------------
    # Encode categorical columns (day_of_week, weather, previous_congestion)
    # -------------------------------------------------------------
    day_encoder = LabelEncoder()
    weather_encoder = LabelEncoder()
    prev_congestion_encoder = LabelEncoder()
    congestion_encoder = LabelEncoder()

    df["day_of_week_enc"] = day_encoder.fit_transform(df["day_of_week"])
    df["weather_enc"] = weather_encoder.fit_transform(df["weather"])
    df["previous_congestion_enc"] = prev_congestion_encoder.fit_transform(df["previous_congestion"])
    df["congestion_enc"] = congestion_encoder.fit_transform(df["congestion"])

    feature_cols = [
        "vehicle_count",
        "average_speed",
        "hour",
        "day_of_week_enc",
        "weather_enc",
        "previous_congestion_enc",
    ]

    X = df[feature_cols]
    y = df["congestion_enc"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # -------------------------------------------------------------
    # Train Random Forest Classifier
    # -------------------------------------------------------------
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    # -------------------------------------------------------------
    # Evaluate
    # -------------------------------------------------------------
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nModel trained successfully. Test accuracy: {acc * 100:.2f}%\n")
    print(classification_report(
        y_test, y_pred, target_names=congestion_encoder.classes_
    ))

    # -------------------------------------------------------------
    # Save model + encoders + feature order together
    # -------------------------------------------------------------
    bundle = {
        "model": model,
        "day_encoder": day_encoder,
        "weather_encoder": weather_encoder,
        "previous_congestion_encoder": prev_congestion_encoder,
        "congestion_encoder": congestion_encoder,
        "feature_cols": feature_cols,
    }
    joblib.dump(bundle, MODEL_PATH)
    print("Model bundle saved to:", MODEL_PATH)


if __name__ == "__main__":
    train()
