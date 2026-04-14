from supabase import create_client
import os

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

VALID_SUBMISSION_STATUSES = {"submitted", "processing", "approved", "rejected"}


# ── Document Templates ───────────────────────────────────────────────────────

def create_document(data: dict) -> tuple[dict, int]:
    required = {"title", "issuing_body", "category", "description", "checklist", "filling_guide"}
    missing = required - data.keys()
    if missing:
        return {"error": f"Missing fields: {', '.join(missing)}"}, 400

    if not isinstance(data["checklist"], list):
        return {"error": "checklist must be a list of strings"}, 400

    payload = {
        "title":         data["title"],
        "issuing_body":  data["issuing_body"],
        "category":      data["category"],
        "description":   data["description"],
        "checklist":     data["checklist"],
        "filling_guide": data["filling_guide"],
        "template_url":  data.get("template_url"),
        "common_errors": data.get("common_errors", []),
    }

    result = supabase.table("documents").insert(payload).execute()
    return result.data[0], 201


def list_documents(category: str | None, search: str | None) -> tuple[list, int]:
    query = supabase.table("documents").select(
        "id, title, issuing_body, category, description, template_url"
    )

    if category:
        query = query.eq("category", category)
    if search:
        query = query.ilike("title", f"%{search}%")

    result = query.order("title").execute()
    return result.data, 200


def get_document_by_id(doc_id: str) -> tuple[dict, int]:
    result = supabase.table("documents").select("*").eq("id", doc_id).single().execute()
    if not result.data:
        return {"error": "Document not found"}, 404
    return result.data, 200


def update_document(doc_id: str, data: dict) -> tuple[dict, int]:
    allowed = {
        "title", "issuing_body", "category", "description",
        "checklist", "filling_guide", "template_url", "common_errors",
    }
    update_payload = {k: v for k, v in data.items() if k in allowed}

    if not update_payload:
        return {"error": f"No valid fields to update. Allowed: {allowed}"}, 400

    if "checklist" in update_payload and not isinstance(update_payload["checklist"], list):
        return {"error": "checklist must be a list"}, 400

    result = supabase.table("documents").update(update_payload).eq("id", doc_id).execute()
    if not result.data:
        return {"error": "Document not found"}, 404
    return result.data[0], 200


def delete_document(doc_id: str) -> tuple[dict, int]:
    result = supabase.table("documents").delete().eq("id", doc_id).execute()
    if not result.data:
        return {"error": "Document not found"}, 404
    return {"message": "Document deleted", "id": doc_id}, 200


# ── Citizen Submissions ──────────────────────────────────────────────────────

def create_submission(data: dict) -> tuple[dict, int]:
    required = {"document_id", "user_id", "filled_fields"}
    missing = required - data.keys()
    if missing:
        return {"error": f"Missing fields: {', '.join(missing)}"}, 400

    if not isinstance(data["filled_fields"], dict):
        return {"error": "filled_fields must be a JSON object"}, 400

    # Verify the referenced document actually exists
    doc = supabase.table("documents").select("id").eq("id", data["document_id"]).single().execute()
    if not doc.data:
        return {"error": "Referenced document_id does not exist"}, 404

    payload = {
        "document_id":    data["document_id"],
        "user_id":        data["user_id"],
        "filled_fields":  data["filled_fields"],
        "ocr_source_url": data.get("ocr_source_url"),
        "status":         "submitted",
    }

    result = supabase.table("document_submissions").insert(payload).execute()
    return result.data[0], 201


def list_submissions_by_user(user_id: str) -> tuple[list | dict, int]:
    if not user_id:
        return {"error": "user_id is required"}, 400

    result = (
        supabase.table("document_submissions")
        .select("*, documents(title, issuing_body)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data, 200


def get_submission_by_id(submission_id: str) -> tuple[dict, int]:
    result = (
        supabase.table("document_submissions")
        .select("*")
        .eq("id", submission_id)
        .single()
        .execute()
    )
    if not result.data:
        return {"error": "Submission not found"}, 404
    return result.data, 200


def update_submission(submission_id: str, data: dict) -> tuple[dict, int]:
    allowed = {"filled_fields", "status"}

    if "status" in data and data["status"] not in VALID_SUBMISSION_STATUSES:
        return {"error": f"Invalid status. Valid: {VALID_SUBMISSION_STATUSES}"}, 400

    update_payload = {k: v for k, v in data.items() if k in allowed}
    if not update_payload:
        return {"error": f"No valid fields. Allowed: {allowed}"}, 400

    result = (
        supabase.table("document_submissions")
        .update(update_payload)
        .eq("id", submission_id)
        .execute()
    )
    if not result.data:
        return {"error": "Submission not found"}, 404
    return result.data[0], 200


def delete_submission(submission_id: str) -> tuple[dict, int]:
    result = supabase.table("document_submissions").delete().eq("id", submission_id).execute()
    if not result.data:
        return {"error": "Submission not found"}, 404
    return {"message": "Submission deleted", "id": submission_id}, 200