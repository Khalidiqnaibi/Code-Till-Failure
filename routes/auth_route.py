from flask import Blueprint, request, jsonify , current_app , g
from services.auth_service import AuthService
from services.users_service import UserService
from dotenv import load_dotenv
import os
from db.supabase_adapter import SupabaseAdapter

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

load_dotenv("C:\\Users\\khaaf\\Documents\\GitHub\\Code-Till-Failure\\.env")
adapter = SupabaseAdapter(
    "https://mlosocwinwylysatnbtm.supabase.co",
    "sb_publishable_BXfqbXN8BV7pqEvMCdPexA_CeV1ERGQ"
)

auth_service = AuthService(adapter)
user_service = UserService(adapter)

# ---------------------------
# EXISTS
# ---------------------------
@auth_bp.route("/exists", methods=["POST"])
def exists():
    data = request.get_json(force=True)

    result = auth_service.user_exists(
        data.get("user_id")
    )
    if not result:
        user_service.create_user(
            user_id = data.get("user_id"),
            password = data.get("password"),
            display_name = data.get("display_name","user")
        )
        

    return jsonify({"exists": result}), 200


# ---------------------------
# VERIFIED
# ---------------------------
@auth_bp.route("/verified", methods=["POST"])
def verified():
    data = request.get_json(force=True)

    result = auth_service.is_user_verified(
        data.get("domain"),
        data.get("email")
    )

    return jsonify({"verified": result}), 200


# ---------------------------
# STATUS (BEST ONE)
# ---------------------------
@auth_bp.route("/status", methods=["POST"])
def status():
    data = request.get_json(force=True)

    result = auth_service.get_user_status(
        data.get("domain"),
        data.get("email")
    )

    return jsonify(result), 200