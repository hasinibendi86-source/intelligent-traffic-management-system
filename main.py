"""
main.py
-------
FastAPI backend for the Intelligent Traffic Congestion Prediction &
Signal Optimization System.

Run with:
    uvicorn main:app --reload --port 8000

Make sure you've trained the ML model first:
    python ml/train_model.py
"""

from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services import traffic_service, prediction_service, signal_service
from ml.predict import ModelNotTrainedError
from ml.vehicle_detection import simulate_vehicle_count

app = FastAPI(
    title="Intelligent Traffic Congestion Prediction & Signal Optimization API",
    description="Backend for a smart-city traffic monitoring, prediction & signal-timing demo.",
    version="1.0.0",
)

# ---------------------------------------------------------------------
# CORS - allow the Vite dev server (and any localhost port) to call this API
# ---------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =======================================================================
# Pydantic request models
# =======================================================================
class TrafficInput(BaseModel):
    cars: int = Field(ge=0)
    bikes: int = Field(ge=0)
    buses: int = Field(ge=0)
    trucks: int = Field(ge=0)
    average_speed: float = Field(ge=0)
    weather: str = "Clear"


class PredictInput(BaseModel):
    vehicle_count: Optional[int] = None
    average_speed: Optional[float] = None
    hour: Optional[int] = None
    day_of_week: Optional[str] = None
    weather: Optional[str] = None
    previous_congestion: Optional[str] = None


class SignalOptimizeInput(BaseModel):
    north: Optional[int] = None
    south: Optional[int] = None
    east: Optional[int] = None
    west: Optional[int] = None


class AlertInput(BaseModel):
    type: str
    road: str
    severity: str
    message: str


class SimulateTrafficInput(BaseModel):
    scenario: str = "normal"  # normal | light | heavy


class SimulateEmergencyInput(BaseModel):
    road: str = "North"
    vehicle_type: str = "Ambulance"
    duration: int = 60


class SimulateAccidentInput(BaseModel):
    location: str = "Junction 2"
    severity: str = "HIGH"
    road: Optional[str] = None


class SimulateWeatherInput(BaseModel):
    weather: str  # Clear | Rain | Fog | Heavy Rain


# =======================================================================
# Health check
# =======================================================================
@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_trained": prediction_service.get_latest_prediction().get("error") is None,
    }


# =======================================================================
# Traffic endpoints
# =======================================================================
@app.post("/traffic")
def post_traffic(data: TrafficInput):
    state = traffic_service.record_traffic(
        cars=data.cars, bikes=data.bikes, buses=data.buses, trucks=data.trucks,
        average_speed=data.average_speed, weather=data.weather, mode="manual",
    )
    return state


@app.get("/traffic/current")
def get_traffic_current():
    return traffic_service.get_current_state()


@app.get("/traffic/history")
def get_traffic_history(limit: int = 100):
    return traffic_service.get_history(limit=limit)


# =======================================================================
# Prediction endpoints
# =======================================================================
@app.post("/predict")
def post_predict(data: PredictInput):
    try:
        return prediction_service.predict_current(
            vehicle_count=data.vehicle_count,
            average_speed=data.average_speed,
            hour=data.hour,
            day_of_week=data.day_of_week,
            weather=data.weather,
            previous_congestion=data.previous_congestion,
        )
    except ModelNotTrainedError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/prediction/current")
def get_prediction_current():
    result = prediction_service.get_forecast()
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


# =======================================================================
# Signal optimization endpoints
# =======================================================================
@app.get("/signal/recommendation")
def get_signal_recommendation():
    return signal_service.get_signal_recommendation()


@app.post("/signal/optimize")
def post_signal_optimize(data: SignalOptimizeInput):
    provided = {
        "North": data.north, "South": data.south,
        "East": data.east, "West": data.west,
    }
    if any(v is not None for v in provided.values()):
        for road, value in provided.items():
            if value is not None:
                signal_service._road_density[road] = value
    return signal_service.calculate_signal_timings()


# =======================================================================
# Analytics
# =======================================================================
@app.get("/analytics")
def get_analytics():
    analytics = traffic_service.get_analytics()
    analytics["most_congested_road"] = signal_service.most_congested_road()
    analytics["road_density"] = signal_service.get_road_density()
    analytics["alternative_routes"] = signal_service.get_alternative_routes()
    return analytics


# =======================================================================
# Alerts
# =======================================================================
@app.get("/alerts")
def get_alerts(limit: int = 50):
    return traffic_service.get_alerts(limit=limit)


@app.post("/alerts")
def post_alert(data: AlertInput):
    return traffic_service.add_alert(
        alert_type=data.type, road=data.road,
        severity=data.severity, message=data.message,
    )


# =======================================================================
# Simulation endpoints (used by the Admin dashboard demo controls)
# =======================================================================
@app.post("/simulate/traffic")
def simulate_traffic(data: SimulateTrafficInput):
    state = traffic_service.simulate_traffic(scenario=data.scenario)
    signal_service.simulate_road_density()
    try:
        prediction = prediction_service.predict_current()
    except ModelNotTrainedError:
        prediction = None

    if prediction and prediction["congestion"] == "HIGH":
        traffic_service.add_alert(
            alert_type="HIGH_CONGESTION", road=signal_service.most_congested_road(),
            severity="HIGH", message="High congestion detected during traffic simulation.",
        )
    if state["average_speed"] < 10:
        traffic_service.add_alert(
            alert_type="LOW_SPEED", road=signal_service.most_congested_road(),
            severity="MEDIUM", message=f"Extremely low average speed detected: {state['average_speed']} km/h.",
        )

    return {"traffic_state": state, "prediction": prediction}


@app.post("/simulate/emergency")
def simulate_emergency(data: SimulateEmergencyInput):
    return signal_service.trigger_emergency(
        road=data.road, vehicle_type=data.vehicle_type, duration=data.duration,
    )


@app.post("/simulate/accident")
def simulate_accident(data: SimulateAccidentInput):
    return signal_service.trigger_accident(
        location=data.location, severity=data.severity, road=data.road,
    )


@app.post("/simulate/weather")
def simulate_weather(data: SimulateWeatherInput):
    return signal_service.apply_weather(data.weather)


# =======================================================================
# Vehicle detection (simulated counting endpoint for the Live Traffic page)
# =======================================================================
@app.get("/vehicle-detection/simulate")
def vehicle_detection_simulate():
    return simulate_vehicle_count()
