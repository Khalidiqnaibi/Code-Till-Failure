"""
auth_service.py
---------------
Authentication service for Hebron Guide, backed exclusively by SupabaseAdapter.

Responsibilities:
  - Google OAuth authorisation URL generation and callback handling.
  - JWT access + refresh token creation and verification.
  - Refresh token persistence inside user_profiles.metadata.
  - Sign-out (refresh token revocation).

No legacy adapter, file adapter, or dual-format refresh token logic.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Tuple

import jwt

from ..auth.provider.google_provider import GoogleAuthProvider
from db import SupabaseAdapter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ACCESS_TOKEN_TTL: int = 3_600            # 1 hour  (seconds)
DEFAULT_REFRESH_TOKEN_TTL: int = 60 * 60 * 24 * 30  # 30 days (seconds)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AuthService:
    """
    Stateless authentication service.

    All persistence is delegated to a SupabaseAdapter instance so there is
    exactly one storage layer in the system.

    Args:
        adapter (SupabaseAdapter): The shared Supabase adapter.
        google_config (dict): Keys: client_secrets_path, redirect_uri, scopes.
        jwt_secret (str): HMAC-SHA256 signing secret for JWT tokens.
        access_token_ttl (int): Access token lifetime in seconds.
        refresh_token_ttl (int): Refresh token lifetime in seconds.

    Example:
        service = AuthService(
            adapter=supabase_adapter,
            google_config={...},
            jwt_secret=os.environ["JWT_SECRET"],
        )
    """

    def __init__(
        self,
        adapter: SupabaseAdapter,
        google_config: Dict[str, Any],
        jwt_secret: str,
        access_token_ttl: int = DEFAULT_ACCESS_TOKEN_TTL,
        refresh_token_ttl: int = DEFAULT_REFRESH_TOKEN_TTL,
    ) -> None:
        self.adapter = adapter
        self.jwt_secret = jwt_secret
        self.access_token_ttl = access_token_ttl
        self.refresh_token_ttl = refresh_token_ttl

        self.providers = {
            "google": GoogleAuthProvider(
                client_secrets_path=google_config["client_secrets_path"],
                redirect_uri=google_config["redirect_uri"],
                scopes=google_config["scopes"],
            )
        }

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def get_authorization_url(self, provider: str, state: Optional[str] = None) -> str:
        """
        Return the OAuth provider's authorisation redirect URL.

        Args:
            provider (str): Provider key, e.g. 'google'.
            state (str, optional): CSRF state token to round-trip through OAuth.

        Returns:
            str: Full authorisation URL to redirect the user to.

        Example:
            url = service.get_authorization_url("google", state="csrf-xyz")
        """
        return self.providers[provider].get_authorization_url(state)

    def handle_provider_callback(
        self,
        domain: str,
        provider: str,
        code: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Exchange an OAuth authorisation code for a user profile and tokens.

        Upserts the user into user_profiles so first-time logins are
        provisioned automatically.

        Args:
            domain (str): Tenant domain (e.g. 'hebron-guide').
            provider (str): Provider key, e.g. 'google'.
            code (str): One-time authorisation code from the OAuth callback.

        Returns:
            tuple:
                - user dict (public profile fields)
                - tokens dict (access_token, refresh_token, expires_in)

        Example:
            user, tokens = service.handle_provider_callback(
                "hebron-guide", "google", request.args["code"]
            )
        """
        provider_user = self.providers[provider].exchange_code_for_user(code)

        # Persist / update the user in Supabase on every login so profile
        # data (name, avatar) stays fresh without a separate sync job.
        self.adapter.upsert_user(domain, provider_user.to_dict())

        tokens = self._create_tokens_for_user(provider_user.id)
        self._save_refresh_token(domain, provider_user.id, tokens["refresh_token"])

        return provider_user.to_dict(), tokens

    # ------------------------------------------------------------------
    # Token lifecycle
    # ------------------------------------------------------------------

    def verify_token_and_get_user(
        self, domain: str, token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Decode a JWT access token and return the corresponding user profile.

        Returns None (not an exception) for any invalid/expired token so
        callers can treat this as a simple authenticated/not-authenticated check.

        Args:
            domain (str): Tenant domain.
            token (str): Raw JWT access token string.

        Returns:
            dict | None: User profile row, or None if token is invalid.

        Example:
            user = service.verify_token_and_get_user("hebron-guide", bearer_token)
            if not user:
                raise HTTPException(401)
        """
        if not token:
            return None

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            logger.debug("JWT decode failed: %s", exc)
            return None

        return self.adapter.get_user(domain, payload["sub"])

    def sign_out(self, domain: str, user_id: str) -> None:
        """
        Revoke the stored refresh token for a user (effectively signing them out).

        Args:
            domain (str): Tenant domain.
            user_id (str): UUID of the user to sign out.

        Example:
            service.sign_out("hebron-guide", current_user["id"])
        """
        self._save_refresh_token(domain, user_id, None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_tokens_for_user(self, user_id: str) -> Dict[str, Any]:
        """
        Mint a fresh access + refresh token pair for a user.

        Args:
            user_id (str): UUID to embed as the JWT subject claim.

        Returns:
            dict: { access_token, refresh_token, expires_in }
        """
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
            "access_token": jwt.encode(
                access_payload, self.jwt_secret, algorithm="HS256"
            ),
            "refresh_token": jwt.encode(
                refresh_payload, self.jwt_secret, algorithm="HS256"
            ),
            "expires_in": self.access_token_ttl,
        }

    def _save_refresh_token(
        self, domain: str, user_id: str, token: Optional[str]
    ) -> None:
        """
        Persist (or clear) the refresh token in user_profiles.metadata.

        Fetches the current metadata first to avoid overwriting unrelated keys.

        Args:
            domain (str): Tenant domain.
            user_id (str): UUID of the user.
            token (str | None): New refresh token value, or None to revoke.

        Side effects:
            Calls adapter.update_user to patch the metadata column.
        """
        raw = self.adapter.get_user(domain, user_id)
        if not raw:
            logger.warning(
                "_save_refresh_token: user %s not found in domain %s", user_id, domain
            )
            return

        # Preserve any existing metadata keys (e.g. preferences) and only
        # patch the refresh_token slot.
        existing_metadata: dict = raw.get("metadata") or {}
        updated_metadata = {**existing_metadata, "refresh_token": token}

        self.adapter.update_user(domain, user_id, {"metadata": updated_metadata})

    def _get_stored_refresh_token(
        self, domain: str, user_id: str
    ) -> Optional[str]:
        """
        Read the persisted refresh token for a user.

        Args:
            domain (str): Tenant domain.
            user_id (str): UUID of the user.

        Returns:
            str | None: Stored refresh token, or None if absent.
        """
        raw = self.adapter.get_user(domain, user_id)
        if not raw:
            return None
        return raw.get("metadata", {}).get("refresh_token")