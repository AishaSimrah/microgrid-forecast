import time
import pandas as pd
import quickml_client as q

df = pd.read_csv("sample_test_input.csv")
rows = q.add_features(df).to_dict(orient="records")

t = time.perf_counter()
r = q.requests.post(q.URL, headers=q.headers(), json={"data": rows}, timeout=120)
print(r.status_code, f"{time.perf_counter() - t:.1f}s")
res = r.json().get("result", [])
print(len(res), "predictions; first 3:", [round(x, 1) for x in res[:3]])