# Smart Energy Microgrid Forecast (HackSphere 3.0)

Predicts hourly demand for a microgrid and decides the power source.

Live app: https://microgrid-api-50047158873.development.catalystappsail.in

## Architecture
- Model: Random Forest regression trained in Zoho Catalyst QuickML (validation RMSE 10.05, R2 0.959).
- API: Flask app on Catalyst AppSail (microgrid-app/app.py).
  - POST /predict takes {"data": [rows]} and returns {"predictions": [...]}. This is what predict.py calls.
  - POST /forecast powers the dashboard (demand, grid mode, alerts, battery).
  - The API calls the QuickML endpoint, so no credentials are needed by the caller.
- Dashboard: microgrid-app/static/index.html (chart, grid state badge, battery charge, alert banners, system log, CSV upload and form).

## Switching rules
- Demand above 160 kW, or hour 18 to 22 inclusive: Renewable Storage Mode. Otherwise Main Grid Mode.
- Demand of 200 kW or more: also Critical Overload Alert.
- The battery model on the dashboard (1200 kWh, 90% start) is an assumption.

## Run predict.py
python predict.py --input sample_test_input.csv --output predictions.csv
python test_eval.py

## Deploy
cd microgrid-app
catalyst deploy

## Environment variables (names only, set in the Catalyst console)
OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_REFRESH_TOKEN, QUICKML_ENDPOINT_URL, QUICKML_ENDPOINT_KEY, QUICKML_ORG
