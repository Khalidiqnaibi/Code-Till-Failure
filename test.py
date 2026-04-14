from dotenv import load_dotenv
import os
import uuid
from db.supabase_adapter import SupabaseAdapter
from services.auth_service import AuthService
def _generate_uuid(self):
    return str(uuid.uuid4())
load_dotenv()


adapter = SupabaseAdapter(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)

service = AuthService(
    adapter=adapter,

)

service = AuthService(adapter)

print(service.user_exists("hebron-guide", "test@gmail.com"))

user = service.create_user("hebron-guide", "test@gmail.com", "Ahmad")
print(user)