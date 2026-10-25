import numpy as np

import pandas as pd

import requests


QUICKML_ENDPOINT_URL = "YOUR_PUBLISHED_QUICKML_ENDPOINT_URL_HERE"


def predict(input_df: pd.DataFrame):

    """Parameters:


        input_df (pandas.DataFrame): DataFrame with columns

        ['timestamp', 'ambient_temp_c', 'humidity_pct', 'solar_irradiance_wm2']


    Returns:

        numpy.ndarray or list: Predicted demand (kW) for each input row.

    """


    if QUICKML_ENDPOINT_URL != "YOUR_PUBLISHED_QUICKML_ENDPOINT_URL_HERE":

        try:


            payload = {"data": input_df.to_dict(orient="records")}


            response = requests.post(

                QUICKML_ENDPOINT_URL, json=payload, timeout=10

            )

            response.raise_for_status()


            result = response.json()

            return np.array(result["predictions"], dtype=float)


        except Exception as e:

            print(f"Warning: QuickML endpoint call failed ({e}).")


    hours = pd.to_datetime(input_df["timestamp"]).dt.hour

    base_load = 120.0 + 30.0 * np.sin(2 * np.pi * (hours - 6) / 24)

    cooling_load = np.maximum(0.0, input_df["ambient_temp_c"] - 24.0) * 8.5


    dummy_predictions = (base_load + cooling_load).values

    return np.array(dummy_predictions, dtype=float)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="sample_test_input.csv")
    parser.add_argument("--output", default="predictions.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    preds = predict(df)
    pd.DataFrame(
        {"timestamp": df["timestamp"], "target_demand_kw": np.round(preds, 2)}
    ).to_csv(args.output, index=False)
    print(f"Wrote {len(preds)} predictions to {args.output}")