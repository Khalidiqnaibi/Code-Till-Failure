
"""
google_provider.py
------------------
Google OAuth provider implementation. Uses client secrets file referenced in config.
"""

import json
import os
from typing import Dict
from urllib.parse import urlencode
import requests

class GoogleAuthProvider():
    def __init__(self, client_secrets_path: str, redirect_uri: str, scopes: list):
        self.client_secrets = json.load(open(client_secrets_path))
        self.client_id = self.client_secrets["web"]["client_id"]
        self.client_secret = self.client_secrets["web"]["client_secret"]
        self.redirect_uri = redirect_uri
        self.scopes = scopes

    def get_authorization_url(self, state: str = None) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "prompt": "consent"
        }
        if state:
            params["state"] = state
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def exchange_code_for_user(self, code: str) -> Dict:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }
        resp = requests.post(token_url, data=data, timeout=10)
        resp.raise_for_status()
        tokens = resp.json()
        # fetch userinfo
        userinfo = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}, timeout=10
        ).json()
        return {
            "id": userinfo.get("sub"),
            "email": userinfo.get("email"),
            "name": userinfo.get("name") or userinfo.get("email"),
            "raw": {"tokens": tokens, "userinfo": userinfo}
        }
