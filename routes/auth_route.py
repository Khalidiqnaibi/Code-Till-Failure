from flask import Blueprint, request, jsonify

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ---------------------------
# EXISTS
# ---------------------------
@auth_bp.route("/exists", methods=["POST"])
def exists():
    data = request.get_json(force=True)

    result = auth_service.user_exists(
        data.get("domain"),
        data.get("email")
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