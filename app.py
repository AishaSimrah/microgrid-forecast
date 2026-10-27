import os
import time
import numpy as np
import pandas as pd
import requests
from flask import Flask, jsonify, request

import grid_logic
import quickml_client as q

app = Flask(__name__)
_tok = {"value": None, "exp": 0}


def token():
    if _tok["value"] and time.time() < _tok["exp"] - 60:
        return _tok["value"]
    r = requests.post(
        "https://accounts.zoho.in/oauth/v2/token",
        data={
            "grant_type": "refresh_token",
            "client_id": os.environ["ZOHO_CLIENT_ID"],
            "client_secret": os.environ["ZOHO_CLIENT_SECRET"],
            "refresh_token": os.environ["ZOHO_REFRESH_TOKEN"],
        },
        timeout=30,
    ).json()
    _tok["value"] = r["access_token"]
    _tok["exp"] = time.time() + r.get("expires_in", 3600)
    return _tok["value"]


def run_model(df):
    rows = q.add_features(df).to_dict(orient="records")
    hdrs = {
        "X-QUICKML-ENDPOINT-KEY": os.environ["QUICKML_ENDPOINT_KEY"],
        "CATALYST-ORG": os.environ["CATALYST_ORG"],
        "Environment": "Development",
        "Authorization": "Zoho-oauthtoken " + token(),
    }
    out = []
    for i in range(0, len(rows), 200):
        r = requests.post(os.environ["QUICKML_ENDPOINT_URL"], headers=hdrs,
                          json={"data": rows[i:i + 200]}, timeout=60)
        r.raise_for_status()
        out += [float(x) for x in r.json()["result"]]
    return out


def read_df():
    data = (request.get_json(silent=True) or {}).get("data")
    if not data:
        return None
    df = pd.DataFrame(data)
    need = ["timestamp", "ambient_temp_c", "humidity_pct", "solar_irradiance_wm2"]
    return df if all(c in df.columns for c in need) else None


@app.post("/predict")
def predict_route():
    df = read_df()
    if df is None:
        return jsonify({"error": "send {'data': [rows with timestamp and 3 weather columns]}"}), 400
    return jsonify({"predictions": run_model(df)})


@app.post("/forecast")
def forecast_route():
    df = read_df()
    if df is None:
        return jsonify({"error": "bad input"}), 400
    preds = run_model(df)
    return jsonify({"forecast": grid_logic.dispatch(df["timestamp"], preds)})


if __name__ == "__main__":
    app.run(port=5000)