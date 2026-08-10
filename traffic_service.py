"""
traffic_service.py
-------------------
Owns the "live" traffic state (vehicle counts by type, average speed,
weather, current congestion) and the historical CSV dataset. Also
provides simple simulation helpers used when no real camera/sensor
is connected, and analytics aggregation for the Analytics page.
"""

import random
import uuid
from datetime import datetime

from services.storage import (
    read_traffic_csv, append_traffic_row, read_json, write_json, ALERTS_JSON,
)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEATHERS = ["Clear", "Rain", "Fog", "Heavy Rain"]

# In-memory "live" state -- represents the most recent reading.
# This is what /traffic/current and the dashboard read from.
_state = {
    "cars": 45,
    "bikes": 32,
    "buses": 5,
    "trucks": 3,
    "average_speed": 28,
    "weather": "Clear",
    "congestion": "MEDIUM",
    "timestamp": datetime.now().isoformat(),
    "mode": "simulation",
}


def _total_vehicles(state):
    return state["cars"] + state["bikes"] + state["buses"] + state["trucks"]


def get_current_state():
    state = dict(_state)
    state["total_vehicles"] = _total_vehicles(state)
    return state


def get_current_hour_day():
    now = datetime.now()
    return now.hour, DAYS[now.weekday()]


def record_traffic(cars, bikes, buses, trucks, average_speed, weather,
                    congestion=None, mode="manual"):
    """Update the live state and append a row to the historical CSV."""
    global _state
    hour, day = get_current_hour_day()
    prev_congestion = _state.get("congestion", "LOW")

    _state = {
        "cars": cars,
        "bikes": bikes,
        "buses": buses,
        "trucks": trucks,
        "average_speed": average_speed,
        "weather": weather,
        "congestion": congestion or prev_congestion,
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
    }

    total_vehicles = _total_vehicles(_state)

    append_traffic_row({
        "vehicle_count": total_vehicles,
        "average_speed": average_speed,
        "hour": hour,
        "day_of_week": day,
        "weather": weather,
        "previous_congestion": prev_congestion,
        "congestion": congestion or prev_congestion,
    })

    return get_current_state()


def update_congestion(congestion_label):
    """Called by the prediction service after a fresh prediction."""
    _state["congestion"] = congestion_label


def update_weather(weather):
    if weather not in WEATHERS:
        weather = "Clear"
    _state["weather"] = weather
    return get_current_state()


def simulate_traffic(scenario="normal"):
    """
    Generate a plausible-looking traffic reading for demo purposes.
    scenario: "normal" | "light" | "heavy"
    """
    hour, _ = get_current_hour_day()
    rush_hour = hour in (8, 9, 17, 18, 19)

    if scenario == "heavy" or rush_hour:
        base = 90
    elif scenario == "light":
        base = 20
    else:
        base = 55

    cars = max(2, int(random.gauss(base * 0.55, base * 0.12)))
    bikes = max(0, int(random.gauss(base * 0.30, base * 0.10)))
    buses = max(0, int(random.gauss(base * 0.06, 2)))
    trucks = max(0, int(random.gauss(base * 0.05, 2)))

    total = cars + bikes + buses + trucks
    average_speed = max(4, int(random.gauss(55 - total / 2.2, 8)))

    weather = _state.get("weather", "Clear")
    if weather in ("Rain", "Heavy Rain"):
        average_speed = max(4, average_speed - random.randint(5, 15))

    return record_traffic(cars, bikes, buses, trucks, average_speed,
                           weather, congestion=None, mode="simulation")


def get_history(limit=100):
    df = read_traffic_csv()
    if df.empty:
        return []
    return df.tail(limit).to_dict(orient="records")


def get_analytics():
    df = read_traffic_csv()
    if df.empty:
        return {
            "hourly_traffic": [],
            "daily_traffic": [],
            "average_speed_trend": [],
            "congestion_distribution": [],
            "peak_hour": None,
            "most_congested_road": "North",
            "total_vehicles": 0,
        }

    hourly = (
        df.groupby("hour")["vehicle_count"].mean().round(1)
        .reset_index().rename(columns={"vehicle_count": "avg_vehicles"})
        .to_dict(orient="records")
    )

    daily = (
        df.groupby("day_of_week")["vehicle_count"].mean().round(1)
        .reindex(DAYS).fillna(0)
        .reset_index().rename(columns={"vehicle_count": "avg_vehicles"})
        .to_dict(orient="records")
    )

    speed_trend = (
        df.groupby("hour")["average_speed"].mean().round(1)
        .reset_index().rename(columns={"average_speed": "avg_speed"})
        .to_dict(orient="records")
    )

    congestion_counts = df["congestion"].value_counts().to_dict()
    congestion_distribution = [
        {"name": k, "value": int(v)} for k, v in congestion_counts.items()
    ]

    peak_row = df.groupby("hour")["vehicle_count"].mean().idxmax()

    return {
        "hourly_traffic": hourly,
        "daily_traffic": daily,
        "average_speed_trend": speed_trend,
        "congestion_distribution": congestion_distribution,
        "peak_hour": int(peak_row),
        "most_congested_road": "North",  # derived alongside signal service in main.py
        "total_vehicles": int(df["vehicle_count"].sum()),
    }


# ---------------------------------------------------------------------
# Alerts (shared JSON store used by traffic, signal & prediction flows)
# ---------------------------------------------------------------------
def add_alert(alert_type, road, severity, message, status="ACTIVE"):
    alerts = read_json(ALERTS_JSON, [])
    alert = {
        "id": str(uuid.uuid4())[:8],
        "type": alert_type,
        "road": road,
        "severity": severity,
        "message": message,
        "status": status,
        "time": datetime.now().isoformat(),
    }
    alerts.insert(0, alert)
    alerts = alerts[:200]  # keep the list from growing forever
    write_json(ALERTS_JSON, alerts)
    return alert


def get_alerts(limit=50):
    alerts = read_json(ALERTS_JSON, [])
    return alerts[:limit]


def resolve_alert(alert_id):
    alerts = read_json(ALERTS_JSON, [])
    for alert in alerts:
        if alert["id"] == alert_id:
            alert["status"] = "RESOLVED"
    write_json(ALERTS_JSON, alerts)
    return alerts
