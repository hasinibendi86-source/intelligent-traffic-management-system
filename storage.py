"""
storage.py
----------
Small shared helpers for reading/writing the CSV and JSON files that
act as this project's "database". Keeping this in one place means
every service reads/writes data consistently and file paths only
live here.
"""

import os
import json
import pandas as pd
from threading import Lock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

TRAFFIC_CSV = os.path.join(DATA_DIR, "traffic_data.csv")
PREDICTIONS_JSON = os.path.join(DATA_DIR, "predictions.json")
ALERTS_JSON = os.path.join(DATA_DIR, "alerts.json")
SIGNAL_JSON = os.path.join(DATA_DIR, "signal_timings.json")

_file_lock = Lock()


def read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default


def write_json(path, data):
    with _file_lock:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)


def read_traffic_csv():
    if not os.path.exists(TRAFFIC_CSV):
        return pd.DataFrame(columns=[
            "vehicle_count", "average_speed", "hour", "day_of_week",
            "weather", "previous_congestion", "congestion"
        ])
    return pd.read_csv(TRAFFIC_CSV)


def append_traffic_row(row: dict):
    with _file_lock:
        df = read_traffic_csv()
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        df.to_csv(TRAFFIC_CSV, index=False)
    return df
