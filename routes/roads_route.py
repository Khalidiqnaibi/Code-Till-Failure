from flask import Blueprint, request, jsonify
from services.road_service import (
    create_report,
    confirm_report,
    list_reports,
    get_report_by_id,
    list_checkpoints,
    list_gas_stations,
    update_report,
    delete_report,
    DEFAULT_RADIUS_KM,
)

roads_bp = Blueprint("roads", __name__, url_prefix="/api/roads")


@roads_bp.route("/reports", methods=["POST"])
def handle_create_report():
    data, status = create_report(request.get_json(force=True))
    return jsonify(data), status


@roads_bp.route("/reports/<string:report_id>/confirm", methods=["POST"])
def handle_confirm_report(report_id):
    data, status = confirm_report(report_id, request.get_json(force=True))
    return jsonify(data), status


@roads_bp.route("/reports", methods=["GET"])
def handle_list_reports():
    data, status = list_reports(
        report_type=request.args.get("report_type"),
        verified_only=request.args.get("verified_only", "false").lower() == "true",
        lat=request.args.get("lat", type=float),
        lng=request.args.get("lng", type=float),
        radius_km=request.args.get("radius_km", DEFAULT_RADIUS_KM, type=float),
    )
    return jsonify(data), status


@roads_bp.route("/reports/<string:report_id>", methods=["GET"])
def handle_get_report(report_id):
    data, status = get_report_by_id(report_id)
    return jsonify(data), status


@roads_bp.route("/checkpoints", methods=["GET"])
def handle_list_checkpoints():
    data, status = list_checkpoints()
    return jsonify(data), status


@roads_bp.route("/gas-stations", methods=["GET"])
def handle_list_gas_stations():
    data, status = list_gas_stations()
    return jsonify(data), status


@roads_bp.route("/reports/<string:report_id>", methods=["PUT"])
def handle_update_report(report_id):
    data, status = update_report(report_id, request.get_json(force=True))
    return jsonify(data), status


@roads_bp.route("/reports/<string:report_id>", methods=["DELETE"])
def handle_delete_report(report_id):
    data, status = delete_report(report_id)
    return jsonify(data), status