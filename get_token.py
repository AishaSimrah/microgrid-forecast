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
    timeout=30,
)
j = r.json()
if "refresh_token" in j:
    with open("zoho_refresh_token.txt", "w") as f:
        f.write(j["refresh_token"])
    print("OK: refresh token saved to zoho_refresh_token.txt")
else:
    print({k: ("<hidden>" if "token" in k else v) for k, v in j.items()})