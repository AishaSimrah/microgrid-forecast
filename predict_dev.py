import os
import time
import numpy as np
import pandas as pd
import requests

URL = os.environ["QUICKML_ENDPOINT_URL"]
HEADERS = {
    "X-QUICKML-ENDPOINT-KEY": os.environ["QUICKML_ENDPOINT_KEY"],
    "CATALYST-ORG": os.environ["CATALYST_ORG"],
    "Environment": "Development",
    "Authorization": "Zoho-oauthtoken " + os.environ["QUICKML_ACCESS_TOKEN"],
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


def predict(input_df):
    rows = add_features(input_df).to_dict(orient="records")
    preds = []
    for row in rows:
        r = requests.post(URL, headers=HEADERS, json={"data": row}, timeout=30)
        r.raise_for_status()
        preds.append(float(r.json()["result"][0]))
    return np.array(preds)


if __name__ == "__main__":
    df = pd.read_csv("sample_test_input.csv").head(5)
    start = time.perf_counter()
    print(predict(df))
    print(f"Took {time.perf_counter() - start:.1f} seconds for 5 rows")