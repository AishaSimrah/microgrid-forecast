import os
import sys
import time
 
# Packages installed by the predeploy step live in ./libs
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs"))
 
import pandas as pd
import requests
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
 
import grid_logic
 
BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
 
NUM_COLS = ["ambient_temp_c", "humidity_pct", "solar_irradiance_wm2"]
FALLBACK = {"ambient_temp_c": 20.0, "humidity_pct": 60.0, "solar_irradiance_wm2": 0.0}
 
# Battery model. The brief gives no battery data, so these are assumptions.
BATTERY_KWH = 1200.0          # usable capacity
START_SOC = 90.0              # state of charge (%) at the first forecast hour
GRID_CHARGE_KW = 100.0        # charge rate while the microgrid runs on Main Grid
SOLAR_CHARGE_KW = 150.0       # extra charge at 1000 W/m2 irradiance, any mode
 
_tok = {"value": None, "exp": 0.0}
 
 
# ---------- QuickML access ----------
 
def token():
    if _tok["value"] and time.time() < _tok["exp"] - 60:
        return _tok["value"]
    r = requests.post(
        "https://accounts.zoho.in/oauth/v2/token",
        data={
            "grant_type": "refresh_token",
            "client_id": os.environ["OAUTH_CLIENT_ID"],
            "client_secret": os.environ["OAUTH_CLIENT_SECRET"],
            "refresh_token": os.environ["OAUTH_REFRESH_TOKEN"],
        },
        timeout=30,
    ).json()
    _tok["value"] = r["access_token"]
    _tok["exp"] = time.time() + r.get("expires_in", 3600)
    return _tok["value"]
 
 
def run_model(rows):
    hdrs = {
        "X-QUICKML-ENDPOINT-KEY": os.environ["QUICKML_ENDPOINT_KEY"],
        "CATALYST-ORG": os.environ["QUICKML_ORG"],
        "Environment": "Development",
        "Authorization": "Zoho-oauthtoken " + token(),
    }
    out = []
    for i in range(0, len(rows), 200):
        r = requests.post(
            os.environ["QUICKML_ENDPOINT_URL"],
            headers=hdrs,
            json={"data": rows[i:i + 200]},
            timeout=60,
        )
        r.raise_for_status()
        out += [float(x) for x in r.json()["result"]]
    return out
 
 
# ---------- cleaning and features ----------
 
def parse_ts(series):
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except (TypeError, ValueError):
        return pd.to_datetime(series, errors="coerce")
 
 
def prepare(data, keep_all):
    """Clean input rows.
 
    keep_all=True  keeps every row in its original order (used by /predict, so the
                   predictions line up one-to-one with the caller's rows).
    keep_all=False sorts, de-duplicates and drops rows without a valid timestamp
                   (used by the dashboard).
    """
    df = pd.DataFrame(data)
    missing = [c for c in ["timestamp"] + NUM_COLS if c not in df.columns]
    if missing:
        raise ValueError("missing column(s): " + ", ".join(missing))
 
    info = {"rows_in": int(len(df)), "dropped_rows": 0, "duplicates_removed": 0,
            "filled_values": 0}
    ts = parse_ts(df["timestamp"])
    if keep_all:
        ts = ts.ffill().bfill()
        if ts.isna().any():
            raise ValueError("no valid timestamps")
        df["timestamp"] = ts
    else:
        bad = ts.isna()
        info["dropped_rows"] = int(bad.sum())
        df["timestamp"] = ts
        df = df[~bad]
        before = len(df)
        df = df.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
        info["duplicates_removed"] = int(before - len(df))
        if df.empty:
            raise ValueError("no valid rows to forecast")
 
    for c in NUM_COLS:
        s = pd.to_numeric(df[c], errors="coerce")
        info["filled_values"] += int(s.isna().sum())
        df[c] = s.interpolate(limit_direction="both").fillna(FALLBACK[c])
    df["solar_irradiance_wm2"] = df["solar_irradiance_wm2"].clip(lower=0)
    return df.reset_index(drop=True), info
 
 
def model_rows(df):
    out = df.copy()
    ts = out["timestamp"]
    out["timestamp"] = ts.dt.strftime("%Y-%m-%d %H:%M:%S")
    out["hour"] = ts.dt.hour
    out["is_peak"] = ts.dt.hour.between(18, 22).astype(int)
    out["dayofweek"] = ts.dt.dayofweek
    cols = ["timestamp"] + NUM_COLS + ["hour", "is_peak", "dayofweek"]
    return out[cols].to_dict(orient="records")
 
 
# ---------- battery ----------
 
def simulate_battery(rows, solar):
    kwh = START_SOC / 100.0 * BATTERY_KWH
    for r, sun in zip(rows, solar):
        charge = SOLAR_CHARGE_KW * float(sun) / 1000.0
        if r["grid_mode"] == "Renewable Storage Mode":
            kwh += charge - r["predicted_demand_kw"]
        else:
            kwh += charge + GRID_CHARGE_KW
        depleted = kwh <= 0
        kwh = min(max(kwh, 0.0), BATTERY_KWH)
        r["battery_soc_pct"] = round(kwh / BATTERY_KWH * 100.0, 1)
        r["battery_depleted"] = bool(depleted)
 
 
# ---------- routes ----------
 
@app.get("/")
def home():
    return send_from_directory(os.path.join(BASE, "static"), "index.html")
 
 
@app.get("/health")
def health():
    return jsonify({"status": "ok"})
 
 
def get_data():
    data = (request.get_json(silent=True) or {}).get("data")
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not data:
        return None
    return data
 
 
@app.post("/predict")
def predict_route():
    data = get_data()
    if data is None:
        return jsonify({"error": "send {'data': [rows with timestamp and 3 weather columns]}"}), 400
    try:
        df, _ = prepare(data, keep_all=True)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"predictions": run_model(model_rows(df))})
 
 
@app.post("/forecast")
def forecast_route():
    body = request.get_json(silent=True) or {}
    data = get_data()
    if data is None:
        return jsonify({"error": "send {'data': [rows with timestamp and 3 weather columns]}"}), 400
    try:
        hours = int(body.get("hours", 24))
    except (TypeError, ValueError):
        hours = 24
    hours = max(1, min(hours, 168))
 
    try:
        df, info = prepare(data, keep_all=False)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    info["hours_requested"] = hours
    if len(df) > hours:
        df = df.head(hours)
    info["rows_used"] = int(len(df))
 
    preds = run_model(model_rows(df))
    rows = grid_logic.dispatch(df["timestamp"], preds)
    simulate_battery(rows, df["solar_irradiance_wm2"].tolist())
 
    peak = max(rows, key=lambda r: r["predicted_demand_kw"])
    summary = {
        "peak_kw": peak["predicted_demand_kw"],
        "peak_time": peak["timestamp"],
        "overload_hours": sum(1 for r in rows if r["overload_alert"]),
        "storage_hours": sum(1 for r in rows if r["grid_mode"] == "Renewable Storage Mode"),
        "main_grid_hours": sum(1 for r in rows if r["grid_mode"] == "Main Grid Mode"),
        "depleted_hours": sum(1 for r in rows if r["battery_depleted"]),
        "end_soc_pct": rows[-1]["battery_soc_pct"],
    }
    return jsonify({
        "forecast": rows,
        "summary": summary,
        "cleaning": info,
        "battery": {
            "capacity_kwh": BATTERY_KWH,
            "start_soc_pct": START_SOC,
            "grid_charge_kw": GRID_CHARGE_KW,
            "solar_charge_kw": SOLAR_CHARGE_KW,
        },
    })
 
 
@app.errorhandler(Exception)
def on_error(e):
    if isinstance(e, HTTPException):
        return e
    app.logger.exception("request failed")
    return jsonify({"error": "The forecast could not be produced.",
                    "detail": type(e).__name__}), 500
 
 
if __name__ == "__main__":
    port = int(os.environ.get("X_ZOHO_CATALYST_LISTEN_PORT", 5000))
    app.run(host="0.0.0.0", port=port)
 