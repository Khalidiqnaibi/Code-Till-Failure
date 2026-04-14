class AuthService:
    def __init__(self, adapter):
        self.adapter = adapter

    # ---------------------------
    # EXISTS CHECK (logic inside service)
    # ---------------------------
    def user_exists(self, user_id: str) -> bool:
        result = (
            self.adapter._client
            .table("user_profiles")
            .select("id",user_id)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    # ---------------------------
    # VERIFIED CHECK
    # ---------------------------
    def is_user_verified(self, domain: str, email: str) -> bool:
        result = (
            self.adapter._client
            .table("user_profiles")
            .select("is_verified")
            .eq("domain", domain)
            .eq("email", email)
            .limit(1)
            .execute()
        )

        if not result.data:
            return False

        return result.data[0].get("is_verified", False)

    # ---------------------------
    # STATUS (ALL LOGIC HERE)
    # ---------------------------
    def get_user_status(self, domain: str, email: str) -> dict:
        result = (
            self.adapter._client
            .table("user_profiles")
            .select("id, is_verified")
            .eq("domain", domain)
            .eq("email", email)
            .limit(1)
            .execute()
        )

        if not result.data:
            return {
                "exists": False,
                "verified": False
            }

        user = result.data[0]

        return {
            "exists": True,
            "verified": user.get("is_verified", False)
        }