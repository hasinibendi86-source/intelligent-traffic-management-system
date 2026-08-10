"""
signal_service.py
------------------
Calculates RECOMMENDED (not actually applied) traffic signal green-time
durations for the four approach roads based on relative traffic density,
handles emergency vehicle priority overrides, accident/abnormal traffic
alerts, weather-based rule adjustments, and simple alternative-route
suggestions.
"""

import random
from datetime import datetime

from services.storage import read_json, write_json, SIGNAL_JSON
from services import traffic_service

ROADS = ["North", "South", "East", "West"]

MIN_GREEN = 15
MAX_GREEN = 90
CYCLE_BUDGET = 160  # total seconds shared across the 4 roads per cycle

# In-memory per-road density, used to compute proportional signal timings.
_road_density = {"North": 40, "South": 25, "East": 55, "West": 30}


def get_road_density():
    return dict(_road_density)


def simulate_road_density():
    global _road_density
    _road_density = {
        road: max(3, int(random.gauss(45, 25))) for road in ROADS
    }
    return get_road_density()


def _weather_adjustment_seconds(weather):
    return {
        "Clear": 0,
        "Rain": 10,
        "Fog": 5,
        "Heavy Rain": 15,
    }.get(weather, 0)


def calculate_signal_timings():
    """
    Allocates the shared cycle budget across roads proportionally to
    their traffic density, then applies a weather-based rule-of-thumb
    adjustment, and clamps each value to [MIN_GREEN, MAX_GREEN].
    """
    density = get_road_density()
    total = sum(density.values()) or 1
    weather = traffic_service.get_current_state()["weather"]
    adjustment = _weather_adjustment_seconds(weather)

    timings = {}
    for road, count in density.items():
        share = count / total
        seconds = round(share * CYCLE_BUDGET) + adjustment
        seconds = max(MIN_GREEN, min(MAX_GREEN, seconds))
        timings[road] = seconds

    result = {
        **timings,
        "weather": weather,
        "weather_adjustment_seconds": adjustment,
        "road_density": density,
        "last_updated": datetime.now().isoformat(),
        "emergency_override": None,
    }
    write_json(SIGNAL_JSON, result)
    return result


def get_signal_recommendation():
    saved = read_json(SIGNAL_JSON, None)
    if not saved:
        return calculate_signal_timings()
    return saved


def most_congested_road():
    density = get_road_density()
    return max(density, key=density.get)


def trigger_emergency(road, vehicle_type="Ambulance", duration=60):
    if road not in ROADS:
        road = ROADS[0]

    timings = get_signal_recommendation()
    override = {
        "road": road,
        "vehicle_type": vehicle_type,
        "duration": duration,
        "triggered_at": datetime.now().isoformat(),
    }
    timings[road] = duration
    timings["emergency_override"] = override
    timings["last_updated"] = datetime.now().isoformat()
    write_json(SIGNAL_JSON, timings)

    traffic_service.add_alert(
        alert_type="EMERGENCY_VEHICLE",
        road=road,
        severity="HIGH",
        message=(
            f"{vehicle_type} detected on {road} Road. "
            f"Recommended action: give GREEN signal to {road} Road for {duration}s."
        ),
    )

    return {
        "message": f"🚨 Emergency Vehicle Detected",
        "road": f"{road} Road",
        "vehicle_type": vehicle_type,
        "recommended_action": f"Give GREEN signal to {road} Road",
        "duration": duration,
        "signal_timings": timings,
    }


def trigger_accident(location="Junction 2", severity="HIGH", road=None):
    road = road or random.choice(ROADS)
    alert = traffic_service.add_alert(
        alert_type="ACCIDENT",
        road=road,
        severity=severity,
        message=f"Accident detected at {location}. Traffic administrator notified.",
    )
    return {
        "message": "⚠️ ACCIDENT DETECTED",
        "location": location,
        "road": road,
        "severity": severity,
        "action": "Notify traffic administrator",
        "alert": alert,
    }


def apply_weather(weather):
    traffic_service.update_weather(weather)
    adjustment = _weather_adjustment_seconds(weather)
    timings = calculate_signal_timings()

    if weather in ("Rain", "Heavy Rain", "Fog"):
        expected = "HIGH" if weather == "Heavy Rain" else "MEDIUM"
        traffic_service.add_alert(
            alert_type="WEATHER",
            road="All Roads",
            severity="MEDIUM" if weather != "Heavy Rain" else "HIGH",
            message=(
                f"{weather} detected. Expected traffic: {expected}. "
                f"Recommended signal adjustment: +{adjustment}s"
            ),
        )

    return {
        "weather": weather,
        "expected_traffic": (
            "HIGH" if weather == "Heavy Rain"
            else "MEDIUM" if weather in ("Rain", "Fog")
            else "LOW"
        ),
        "recommended_signal_adjustment_seconds": adjustment,
        "signal_timings": timings,
    }


def get_alternative_routes():
    """Simple simulated alternative-route comparison (no external maps API)."""
    density = get_road_density()
    avg_density = sum(density.values()) / len(density)

    def route_from_density(name, factor, base_time):
        level = "HIGH" if factor > 1.15 else "MEDIUM" if factor > 0.85 else "LOW"
        est_time = round(base_time * factor, 1)
        return {"name": name, "traffic": level, "estimated_time_minutes": est_time}

    routes = [
        route_from_density("Route A (Main Road)", max(0.6, density["North"] / max(avg_density, 1)), 20),
        route_from_density("Route B (Ring Road)", max(0.6, density["East"] / max(avg_density, 1)), 22),
        route_from_density("Route C (Service Lane)", max(0.6, density["West"] / max(avg_density, 1)), 18),
    ]
    recommended = min(routes, key=lambda r: r["estimated_time_minutes"])

    return {"routes": routes, "recommended": recommended["name"]}
