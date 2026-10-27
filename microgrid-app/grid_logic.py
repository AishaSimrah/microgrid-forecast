import pandas as pd


def classify(demand_kw, hour):
    """Return (grid_mode, overload_alert) for one forecast hour."""
    renewable = demand_kw > 160 or 18 <= hour <= 22
    mode = "Renewable Storage Mode" if renewable else "Main Grid Mode"
    overload = demand_kw >= 200  # independent of grid mode
    return mode, overload


def dispatch(timestamps, demands):
    """Apply the rules to every forecast row."""
    rows = []
    for ts, d in zip(pd.to_datetime(timestamps), demands):
        mode, overload = classify(float(d), ts.hour)
        rows.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "predicted_demand_kw": round(float(d), 2),
            "grid_mode": mode,
            "overload_alert": overload,
        })
    return rows


if __name__ == "__main__":
    # edge cases straight from the problem statement
    assert classify(160, 10) == ("Main Grid Mode", False)        # exactly 160, outside window
    assert classify(160.01, 10) == ("Renewable Storage Mode", False)
    assert classify(100, 18) == ("Renewable Storage Mode", False)  # window start inclusive
    assert classify(100, 22) == ("Renewable Storage Mode", False)  # window end inclusive
    assert classify(100, 17) == ("Main Grid Mode", False)
    assert classify(100, 23) == ("Main Grid Mode", False)
    assert classify(200, 10) == ("Renewable Storage Mode", True)   # exactly 200 triggers alert
    assert classify(199.99, 10) == ("Renewable Storage Mode", False)
    assert classify(210, 20) == ("Renewable Storage Mode", True)
    print("All checks passed")