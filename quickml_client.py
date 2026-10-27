import os
import numpy as np
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor

URL = os.environ.get("QUICKML_ENDPOINT_URL", "")


def get_token():
    r = requests.post(
        "https://accounts.zoho.in/oauth/v2/token",
        data={
            "grant_type": "refresh_token",
            "client_id": os.environ["ZOHO_CLIENT_ID"],
            "client_secret": os.environ["ZOHO_CLIENT_SECRET"],
            "refresh_token": os.environ["ZOHO_REFRESH_TOKEN"],
        },
        timeout=30,
    )
    return r.json()["access_token"]


def headers():
    return {
        "X-QUICKML-ENDPOINT-KEY": os.environ["QUICKML_ENDPOINT_KEY"],
        "CATALYST-ORG": os.environ["CATALYST_ORG"],
        "Environment": "Development",
        "Authorization": "Zoho-oauthtoken " + get_token(),
    }


def add_features(df):
    df = df.copy()
    ts = pd.to_datetime(df["timestamp"])
    for col in ["ambient_temp_c", "humidity_pct", "solar_irradiance_wm2"]:
        df[col] = df[col].interpolate().bfill().ffill()
    df["timestamp"] = ts.dt.strftime("%Y-%m-%d %H:%M:%S")
    df["hour"] = ts.dt.hour
    df["is_peak"] = ts.dt.hour.between(18, 22).astype(int)
    df["dayofweek"] = ts.dt.dayofweek
    return df


def predict_parallel(input_df, workers=10):
    hdrs = headers()
    rows = add_features(input_df).to_dict(orient="records")

    def one(row):
        r = requests.post(URL, headers=hdrs, json={"data": row}, timeout=30)
        r.raise_for_status()
        return float(r.json()["result"][0])

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return np.array(list(ex.map(one, rows)))