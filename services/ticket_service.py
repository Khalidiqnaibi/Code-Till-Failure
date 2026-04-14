from supabase import create_client
import os

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

VALID_STATUSES        = {"unpaid", "paid", "disputed"}
VALID_PAYMENT_METHODS = {"visa", "jawwal_pay", "paltel_pay"}


def create_ticket(data: dict) -> tuple[dict, int]:
    required = {"violation_type", "location", "latitude", "longitude", "fine_amount", "issued_by"}
    missing = required - data.keys()
    if missing:
        return {"error": f"Missing fields: {', '.join(missing)}"}, 400

    if not data.get("national_id") and not data.get("plate_number"):
        return {"error": "Provide at least national_id or plate_number"}, 400

    payload = {
        "national_id":    data.get("national_id"),
        "plate_number":   data.get("plate_number"),
        "violation_type": data["violation_type"],
        "location":       data["location"],
        "latitude":       data["latitude"],
        "longitude":      data["longitude"],
        "fine_amount":    data["fine_amount"],
        "photo_url":      data.get("photo_url"),
        "issued_by":      data["issued_by"],
        "status":         "unpaid",
    }

    result = supabase.table("tickets").insert(payload).execute()
    return result.data[0], 201


def get_tickets_by_owner(national_id: str | None, plate_number: str | None) -> tuple[list | dict, int]:
    if not national_id and not plate_number:
        return {"error": "Provide national_id or plate_number as a query param"}, 400

    query = supabase.table("tickets").select("*")

    if national_id and plate_number:
        query = query.or_(f"national_id.eq.{national_id},plate_number.eq.{plate_number}")
    elif national_id:
        query = query.eq("national_id", national_id)
    else:
        query = query.eq("plate_number", plate_number)

    result = query.order("created_at", desc=True).execute()
    return result.data, 200


def get_ticket_by_id(ticket_id: str) -> tuple[dict, int]:
    result = supabase.table("tickets").select("*").eq("id", ticket_id).single().execute()
    if not result.data:
        return {"error": "Ticket not found"}, 404
    return result.data, 200


def update_ticket(ticket_id: str, data: dict) -> tuple[dict, int]:
    allowed = {"status", "photo_url", "fine_amount"}

    if "status" in data and data["status"] not in VALID_STATUSES:
        return {"error": f"Invalid status. Valid: {VALID_STATUSES}"}, 400

    update_payload = {k: v for k, v in data.items() if k in allowed}
    if not update_payload:
        return {"error": f"No valid fields to update. Allowed: {allowed}"}, 400

    result = supabase.table("tickets").update(update_payload).eq("id", ticket_id).execute()
    if not result.data:
        return {"error": "Ticket not found"}, 404
    return result.data[0], 200


def pay_ticket(ticket_id: str, data: dict) -> tuple[dict, int]:
    if not data.get("payment_method") or not data.get("transaction_ref"):
        return {"error": "payment_method and transaction_ref are required"}, 400

    if data["payment_method"] not in VALID_PAYMENT_METHODS:
        return {"error": f"Invalid payment_method. Valid: {VALID_PAYMENT_METHODS}"}, 400

    result = (
        supabase.table("tickets")
        .update({
            "status":          "paid",
            "payment_method":  data["payment_method"],
            "transaction_ref": data["transaction_ref"],
        })
        .eq("id", ticket_id)
        .eq("status", "unpaid")     # guard: cannot re-pay an already-paid ticket
        .execute()
    )
    if not result.data:
        return {"error": "Ticket not found or already paid"}, 404
    return result.data[0], 200


def delete_ticket(ticket_id: str) -> tuple[dict, int]:
    result = supabase.table("tickets").delete().eq("id", ticket_id).execute()
    if not result.data:
        return {"error": "Ticket not found"}, 404
    return {"message": "Ticket deleted", "id": ticket_id}, 200