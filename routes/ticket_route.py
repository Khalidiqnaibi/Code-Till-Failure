from flask import Blueprint, request, jsonify
from services.ticket_service import (
    create_ticket,
    get_tickets_by_owner,
    get_ticket_by_id,
    update_ticket,
    pay_ticket,
    delete_ticket,
)

tickets_bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")


@tickets_bp.route("/", methods=["POST"])
def handle_create_ticket():
    data, status = create_ticket(request.get_json(force=True))
    return jsonify(data), status


@tickets_bp.route("/", methods=["GET"])
def handle_get_tickets():
    data, status = get_tickets_by_owner(
        national_id=request.args.get("national_id"),
        plate_number=request.args.get("plate_number"),
    )
    return jsonify(data), status


@tickets_bp.route("/<string:ticket_id>", methods=["GET"])
def handle_get_ticket(ticket_id):
    data, status = get_ticket_by_id(ticket_id)
    return jsonify(data), status


@tickets_bp.route("/<string:ticket_id>", methods=["PUT"])
def handle_update_ticket(ticket_id):
    data, status = update_ticket(ticket_id, request.get_json(force=True))
    return jsonify(data), status


@tickets_bp.route("/<string:ticket_id>/pay", methods=["POST"])
def handle_pay_ticket(ticket_id):
    data, status = pay_ticket(ticket_id, request.get_json(force=True))
    return jsonify(data), status


@tickets_bp.route("/<string:ticket_id>", methods=["DELETE"])
def handle_delete_ticket(ticket_id):
    data, status = delete_ticket(ticket_id)
    return jsonify(data), status