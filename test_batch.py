import time
import pandas as pd
import quickml_client as q

df = pd.read_csv("sample_test_input.csv")
rows = q.add_features(df.head(5)).to_dict(orient="records")

t = time.perf_counter()
r = q.requests.post(q.URL, headers=q.headers(), json={"data": rows}, timeout=60)
print("BATCH:", r.status_code, f"{time.perf_counter() - t:.1f}s")
print(r.text[:300])

t = time.perf_counter()
preds = q.predict_parallel(df.head(50))
print(f"PARALLEL: 50 rows in {time.perf_counter() - t:.1f}s")
print(preds[:5])