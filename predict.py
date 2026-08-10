"""
predict.py
----------
Loads the trained Random Forest model bundle (traffic_model.pkl) and
exposes a simple predict_congestion() function used by the FastAPI
backend to turn traffic features into a congestion prediction.
"""

import os
import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "ml", "traffic_model.pkl")

_bundle = None


class ModelNotTrainedError(Exception):
    """Raised when traffic_model.pkl does not exist yet."""
    pass


def _load_bundle():
    global _bundle
    if _bundle is None:
        if not os.path.exists(MODEL_PATH):
            raise ModelNotTrainedError(
                "Trained model not found at "
                f"'{MODEL_PATH}'. Please train it first by running:\n"
                "    python ml/train_model.py"
            )
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


def _safe_encode(encoder, value, fallback_index=0):
    """Encode a categorical value, falling back gracefully if unseen."""
    try:
        return int(encoder.transform([value])[0])
    except ValueError:
        return fallback_index


def predict_congestion(vehicle_count, average_speed, hour, day_of_week,
                        weather, previous_congestion):
    """
    Returns a dict: {"congestion": "HIGH", "confidence": 92.3}
    """
    bundle = _load_bundle()
    model = bundle["model"]
    day_encoder = bundle["day_encoder"]
    weather_encoder = bundle["weather_encoder"]
    prev_encoder = bundle["previous_congestion_encoder"]
    congestion_encoder = bundle["congestion_encoder"]

    day_enc = _safe_encode(day_encoder, day_of_week)
    weather_enc = _safe_encode(weather_encoder, weather)
    prev_enc = _safe_encode(prev_encoder, previous_congestion)

    features = [[
        vehicle_count,
        average_speed,
        hour,
        day_enc,
        weather_enc,
        prev_enc,
    ]]

    pred_class = model.predict(features)[0]
    probabilities = model.predict_proba(features)[0]
    confidence = round(float(max(probabilities)) * 100, 1)
    congestion_label = congestion_encoder.inverse_transform([pred_class])[0]

    return {
        "congestion": str(congestion_label),
        "confidence": confidence,
    }


def is_model_trained():
    return os.path.exists(MODEL_PATH)
