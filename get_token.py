import os
import requests

r = requests.post(
    "https://accounts.zoho.in/oauth/v2/token",
    data={
        "grant_type": "authorization_code",
        "client_id": os.environ["ZOHO_CLIENT_ID"],
        "client_secret": os.environ["ZOHO_CLIENT_SECRET"],
        "code": os.environ["ZOHO_CODE"],
    },
)
print(r.json())