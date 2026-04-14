"""
auth_service.py
----------------
Adapter-only authentication service built to work with the User dataclass.

- Google OAuth flow
- User provisioning using the User model
- JWT access + refresh token lifecycle
- Metadata refresh_token storage
- No repository, no Binder
"""

import time
import jwt
from typing import Dict, Any, Optional, Tuple
from dataclasses import asdict

from ..auth.provider.google_provider import GoogleAuthProvider

class AuthService:
    """
    Authentication service that uses only the adapter for storage.
    Ensures users are always saved using the User dataclass structure.
    """

    def __init__(
        self,
        adapter,
        legacy_adapter,
        file_adapter,
        google_config: Dict[str, Any],
        jwt_secret: str,
        access_token_ttl: int = 3600,
        refresh_token_ttl: int = 60 * 60 * 24 * 30,
    ):
        self.adapter = adapter
        self.legacy_adapter = legacy_adapter
        self.file_adapter = file_adapter
        self.jwt_secret = jwt_secret
        self.access_token_ttl = access_token_ttl
        self.refresh_token_ttl = refresh_token_ttl

        # OAuth provider
        self.providers = {
            "google": GoogleAuthProvider(
                client_secrets_path=google_config["client_secrets_path"],
                redirect_uri=google_config["redirect_uri"],
                scopes=google_config["scopes"],
            )
        }

    def get_authorization_url(self, provider: str, state: Optional[str]) -> str:
        return self.providers[provider].get_authorization_url(state)


    def handle_provider_callback(
        self,
        domain:str,
        provider: str,
        code: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:

        provider_user = self.providers[provider].exchange_code_for_user(code)
        
        user = provider_user

        tokens = self._create_tokens_for_user(user.id)
        self._save_refresh_token(domain,user.id, tokens["refresh_token"])

        return user.to_dict(), tokens

    def _create_tokens_for_user(self, user_id: str) -> Dict[str, Any]:
        now = int(time.time())

        access_payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + self.access_token_ttl,
        }

        refresh_payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + self.refresh_token_ttl,
            "type": "refresh",
        }

        return {
            "access_token": jwt.encode(access_payload, self.jwt_secret, algorithm="HS256"),
            "refresh_token": jwt.encode(refresh_payload, self.jwt_secret, algorithm="HS256"),
            "expires_in": self.access_token_ttl,
        }

    def verify_token_and_get_user(self,domain:str, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            raw_user = self.adapter.get_user(domain,payload["sub"])
            return raw_user if raw_user else None
        except Exception:
            return None


    def sign_out(self,domain:str, user_id: str) -> None:
        self._save_refresh_token(domain,user_id, None)

    def _save_refresh_token(self,domain:str, user_id: str, token: Optional[str]):
        raw = self.adapter.get_user(domain,user_id)
        if not raw:
            return

        # LEGACY SAFE
        if "metadata" not in raw or "first" in raw:
            raw["metadata"] = {}

        raw["metadata"]["refresh_token"] = token

        # Save back without enforcing dataclass structure
        self.adapter.update_user(domain,user_id, raw)

    def _get_stored_refresh_token(self,domain:str, user_id: str) -> Optional[str]:
        raw = self.adapter.get_user(domain,user_id)
        if not raw:
            return None

        # NEW FORMAT
        if "metadata" in raw and "first" not in raw:
            return raw.get("metadata", {}).get("refresh_token")

        # LEGACY FORMAT
        if "settings" in raw:
            return raw.get("settings", {}).get("refresh_token")

        return None