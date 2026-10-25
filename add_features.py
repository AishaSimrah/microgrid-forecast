import pandas as pd

df = pd.read_csv("train_telemetry.csv")
df = df.dropna(how="all")

ts = pd.to_datetime(df["timestamp"])
df["hour"] = ts.dt.hour
df["is_peak"] = ts.dt.hour.between(18, 22).astype(int)
df["dayofweek"] = ts.dt.dayofweek

df.to_csv("train_features.csv", index=False)
print(df.shape)
print(df.head())
print(df.isna().sum())