"""
prediction_service.py
----------------------
Wraps the trained ML model (ml/predict.py) to produce congestion
predictions, persists them to predictions.json, and generates a
short-term forecast (current / +15 min / +30 min) used by the
Traffic Prediction feature.
"""

from datetime import datetime

from ml.predict import predict_congestion, ModelNotTrainedError
from services.storage import read_json, write_json, PREDICTIONS_JSON
from services import traffic_service

CONGESTION_ORDER = ["LOW", "MEDIUM", "HIGH"]


def _save_prediction(record):
    predictions = read_json(PREDICTIONS_JSON, [])
    predictions.insert(0, record)
    predictions = predictions[:200]
    write_json(PREDICTIONS_JSON, predictions)
    return record


def predict_current(vehicle_count=None, average_speed=None, hour=None,
                     day_of_week=None, weather=None, previous_congestion=None):
    """
    Runs a prediction using either explicitly supplied values, or the
    current live traffic state as sensible defaults.
    """
    state = traffic_service.get_current_state()
    cur_hour, cur_day = traffic_service.get_current_hour_day()

    vehicle_count = vehicle_count if vehicle_count is not None else state["total_vehicles"]
    average_speed = average_speed if average_speed is not None else state["average_speed"]
    hour = hour if hour is not None else cur_hour
    day_of_week = day_of_week or cur_day
    weather = weather or state["weather"]
    previous_congestion = previous_congestion or state["congestion"]

    result = predict_congestion(
        vehicle_count=vehicle_count,
        average_speed=average_speed,
        hour=hour,
        day_of_week=day_of_week,
        weather=weather,
        previous_congestion=previous_congestion,
    )

    record = {
        "congestion": result["congestion"],
        "confidence": result["confidence"],
        "vehicle_count": vehicle_count,
        "average_speed": average_speed,
        "hour": hour,
        "day_of_week": day_of_week,
        "weather": weather,
        "timestamp": datetime.now().isoformat(),
    }
    _save_prediction(record)

    # Feed the prediction back into the live traffic state so the
    # dashboard congestion badge stays in sync.
    traffic_service.update_congestion(result["congestion"])

    return record


def get_latest_prediction():
    predictions = read_json(PREDICTIONS_JSON, [])
    if predictions:
        return predictions[0]
    # No predictions yet -- generate one on the fly using live state.
    try:
        return predict_current()
    except ModelNotTrainedError as e:
        return {"error": str(e)}


def get_forecast():
    """
    Produces a simple 0 / +15 / +30 minute forecast by nudging the
    vehicle_count up or down based on the current trend and re-running
    the model. This keeps the "prediction" feature honest (it's the
    same trained model, just fed plausible near-future inputs) without
    needing real streaming sensor data.
    """
    state = traffic_service.get_current_state()
    hour, day = traffic_service.get_current_hour_day()
    weather = state["weather"]
    base_vehicles = state["total_vehicles"]
    base_speed = state["average_speed"]

    try:
        current = predict_congestion(
            vehicle_count=base_vehicles, average_speed=base_speed,
            hour=hour, day_of_week=day, weather=weather,
            previous_congestion=state["congestion"],
        )
        plus_15 = predict_congestion(
            vehicle_count=int(base_vehicles * 1.10), average_speed=max(4, int(base_speed * 0.95)),
            hour=hour, day_of_week=day, weather=weather,
            previous_congestion=current["congestion"],
        )
        plus_30 = predict_congestion(
            vehicle_count=int(base_vehicles * 1.20), average_speed=max(4, int(base_speed * 0.90)),
            hour=hour, day_of_week=day, weather=weather,
            previous_congestion=plus_15["congestion"],
        )
    except ModelNotTrainedError as e:
        return {"error": str(e)}

    return {
        "current": current,
        "next_15_min": plus_15,
        "next_30_min": plus_30,
        "generated_at": datetime.now().isoformat(),
    }


def get_prediction_history(limit=50):
    predictions = read_json(PREDICTIONS_JSON, [])
    return predictions[:limit]
