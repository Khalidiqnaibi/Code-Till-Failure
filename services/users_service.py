import uuid

class UserService:
    def __init__(self, adapter):
        self.adapter = adapter

    # ---------------------------
    # CREATE USER (optional helper)
    # ---------------------------
    def create_user(self, domain: str, email: str, display_name: str):
        user_data = {
            "id": str(uuid.uuid4()),
            "password": email,
            "display_name": display_name,
        }

        return self.adapter.upsert_user(domain, user_data)

    # ---------------------------
    # CHECK USER EXISTS (main thing)
    # ---------------------------
    def user_exists(self, domain: str, email: str) -> bool:
        result = (
            self.adapter._client
            .table("user_profiles")
            .select("id")
            .eq("email", email)
            .eq("domain", domain)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    # ---------------------------
    # GET USER
    # ---------------------------
    def get_user(self, domain: str, email: str):
        result = (
            self.adapter._client
            .table("user_profiles")
            .select("*")
            .eq("email", email)
            .eq("domain", domain)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None