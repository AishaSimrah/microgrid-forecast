import os
import requests

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
j = r.json()
print({k: ("<hidden>" if "token" in k else v) for k, v in j.items()})
print("lengths:", len(os.environ["ZOHO_CLIENT_ID"]), len(os.environ["ZOHO_CLIENT_SECRET"]), len(os.environ["ZOHO_REFRESH_TOKEN"]))