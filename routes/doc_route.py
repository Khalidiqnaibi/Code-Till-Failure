from flask import Blueprint, request, jsonify
from services.document_service import (
    create_document,
    list_documents,
    get_document_by_id,
    update_document,
    delete_document,
    create_submission,
    list_submissions_by_user,
    get_submission_by_id,
    update_submission,
    delete_submission,
)

documents_bp = Blueprint("docs", __name__, url_prefix="/api/documents")


# ── Templates ────────────────────────────────────────────────────────────────

@documents_bp.route("/", methods=["POST"])
def handle_create_document():
    data, status = create_document(request.get_json(force=True))
    return jsonify(data), status


@documents_bp.route("/", methods=["GET"])
def handle_list_documents():
    data, status = list_documents(
        category=request.args.get("category"),
        search=request.args.get("search"),
    )
    return jsonify(data), status


@documents_bp.route("/<string:doc_id>", methods=["GET"])
def handle_get_document(doc_id):
    data, status = get_document_by_id(doc_id)
    return jsonify(data), status


@documents_bp.route("/<string:doc_id>", methods=["PUT"])
def handle_update_document(doc_id):
    data, status = update_document(doc_id, request.get_json(force=True))
    return jsonify(data), status


@documents_bp.route("/<string:doc_id>", methods=["DELETE"])
def handle_delete_document(doc_id):
    data, status = delete_document(doc_id)
    return jsonify(data), status


# ── Submissions ───────────────────────────────────────────────────────────────

@documents_bp.route("/submissions", methods=["POST"])
def handle_create_submission():
    data, status = create_submission(request.get_json(force=True))
    return jsonify(data), status


@documents_bp.route("/submissions", methods=["GET"])
def handle_list_submissions():
    data, status = list_submissions_by_user(request.args.get("user_id"))
    return jsonify(data), status


@documents_bp.route("/submissions/<string:submission_id>", methods=["GET"])
def handle_get_submission(submission_id):
    data, status = get_submission_by_id(submission_id)
    return jsonify(data), status


@documents_bp.route("/submissions/<string:submission_id>", methods=["PUT"])
def handle_update_submission(submission_id):
    data, status = update_submission(submission_id, request.get_json(force=True))
    return jsonify(data), status


@documents_bp.route("/submissions/<string:submission_id>", methods=["DELETE"])
def handle_delete_submission(submission_id):
    data, status = delete_submission(submission_id)
    return jsonify(data), status