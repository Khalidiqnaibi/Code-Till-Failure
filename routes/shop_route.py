from flask import Blueprint, request, jsonify
from services.shop_service import (
    create_shop,
    list_shops,
    get_shop_by_id,
    update_shop,
    delete_shop,
    report_shop_status,
    get_status_history,
    list_pharmacies,
    DEFAULT_RADIUS_KM,
)

shops_bp = Blueprint("shops", __name__, url_prefix="/api/shops")


def _parse_is_open() -> bool | None:
    raw = request.args.get("is_open")
    if raw is None:
        return None
    return raw.lower() == "true"


@shops_bp.route("/", methods=["POST"])
def handle_create_shop():
    data, status = create_shop(request.get_json(force=True))
    return jsonify(data), status


@shops_bp.route("/", methods=["GET"])
def handle_list_shops():
    data, status = list_shops(
        category=request.args.get("category"),
        is_open=_parse_is_open(),
        search=request.args.get("search"),
        lat=request.args.get("lat", type=float),
        lng=request.args.get("lng", type=float),
        radius_km=request.args.get("radius_km", DEFAULT_RADIUS_KM, type=float),
    )
    return jsonify(data), status


@shops_bp.route("/pharmacies", methods=["GET"])
def handle_list_pharmacies():
    data, status = list_pharmacies(
        is_open=_parse_is_open(),
        lat=request.args.get("lat", type=float),
        lng=request.args.get("lng", type=float),
        radius_km=request.args.get("radius_km", DEFAULT_RADIUS_KM, type=float),
    )
    return jsonify(data), status


@shops_bp.route("/<string:shop_id>", methods=["GET"])
def handle_get_shop(shop_id):
    data, status = get_shop_by_id(shop_id)
    return jsonify(data), status


@shops_bp.route("/<string:shop_id>", methods=["PUT"])
def handle_update_shop(shop_id):
    data, status = update_shop(shop_id, request.get_json(force=True))
    return jsonify(data), status


@shops_bp.route("/<string:shop_id>", methods=["DELETE"])
def handle_delete_shop(shop_id):
    data, status = delete_shop(shop_id)
    return jsonify(data), status


@shops_bp.route("/<string:shop_id>/status-updates", methods=["POST"])
def handle_report_status(shop_id):
    data, status = report_shop_status(shop_id, request.get_json(force=True))
    return jsonify(data), status


@shops_bp.route("/<string:shop_id>/status-history", methods=["GET"])
def handle_status_history(shop_id):
    data, status = get_status_history(
        shop_id,
        limit=request.args.get("limit", 20, type=int),
    )
    return jsonify(data), status