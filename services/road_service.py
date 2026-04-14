from supabase import create_client
from math import radians, cos, sin, asin, sqrt
import os

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

VERIFICATION_THRESHOLD = 25
DEFAULT_RADIUS_KM       = 10.0

VALID_REPORT_TYPES = {
    "congestion", "closure", "checkpoint",
    "gas_station", "ev_charging", "road_damage",
}
VALID_SEVERITIES = {"low", "medium", "high"}


# ── Geo helper ────────────────────────────────────────────────────────────────

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km between two (lat, lng) points."""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * asin(sqrt(a))


def _filter_by_radius(
    items: list[dict],
    lat: float,
    lng: float,
    radius_km: float,
    attach_distance: bool = False,
) -> list[dict]:
    """Return only items within radius_km, optionally attaching distance_km."""
    result = []
    for item in items:
        dist = _haversine(lat, lng, item["latitude"], item["longitude"])
        if dist <= radius_km:
            result.append({**item, "distance_km": round(dist, 2)} if attach_distance else item)
    return result


# ── Reports ───────────────────────────────────────────────────────────────────

def create_report(data: dict) -> tuple[dict, int]:
    required = {"user_id", "report_type", "latitude", "longitude"}
    missing = required - data.keys()
    if missing:
        return {"error": f"Missing fields: {', '.join(missing)}"}, 400

    if data["report_type"] not in VALID_REPORT_TYPES:
        return {"error": f"Invalid report_type. Valid: {VALID_REPORT_TYPES}"}, 400

    if "severity" in data and data["severity"] not in VALID_SEVERITIES:
        return {"error": f"Invalid severity. Valid: {VALID_SEVERITIES}"}, 400

    payload = {
        "user_id":     data["user_id"],
        "report_type": data["report_type"],
        "latitude":    data["latitude"],
        "longitude":   data["longitude"],
        "description": data.get("description", ""),
        "road_name":   data.get("road_name"),
        "severity":    data.get("severity", "medium"),
        "match_count": 0,
        "is_verified": False,
        "is_active":   True,
    }

    result = supabase.table("road_reports").insert(payload).execute()
    return result.data[0], 201


def confirm_report(report_id: str, data: dict) -> tuple[dict, int]:
    """
    A user physically near the report location confirms it.
    - Increments match_count.
    - Flips is_verified to True when match_count reaches VERIFICATION_THRESHOLD.
    - Awards 1 point to the original reporter at the moment of verification.
    - Prevents a user from confirming the same report twice (DB unique constraint).
    """
    required = {"user_id", "latitude", "longitude"}
    missing = required - data.keys()
    if missing:
        return {"error": f"Missing fields: {', '.join(missing)}"}, 400

    # Fetch report
    report_res = supabase.table("road_reports").select("*").eq("id", report_id).single().execute()
    if not report_res.data:
        return {"error": "Report not found"}, 404
    report = report_res.data

    if not report["is_active"]:
        return {"error": "Cannot confirm an inactive report"}, 400

    # Log confirmation (DB unique constraint on report_id + user_id prevents duplicates)
    try:
        supabase.table("report_confirmations").insert({
            "report_id": report_id,
            "user_id":   data["user_id"],
            "latitude":  data["latitude"],
            "longitude": data["longitude"],
        }).execute()
    except Exception:
        return {"error": "You have already confirmed this report"}, 409

    new_count    = report["match_count"] + 1
    now_verified = new_count >= VERIFICATION_THRESHOLD
    crossed_threshold = now_verified and not report["is_verified"]

    update_payload = {"match_count": new_count}
    if crossed_threshold:
        update_payload["is_verified"] = True
        # Award 1 point to original reporter
        supabase.rpc("increment_user_points", {"uid": report["user_id"], "pts": 1}).execute()

    updated = supabase.table("road_reports").update(update_payload).eq("id", report_id).execute()
    return {
        **updated.data[0],
        "newly_verified": crossed_threshold,
    }, 200


def list_reports(
    report_type: str | None,
    verified_only: bool,
    lat: float | None,
    lng: float | None,
    radius_km: float,
) -> tuple[list, int]:
    query = (
        supabase.table("road_reports")
        .select("*")
        .eq("is_active", True)
        .order("created_at", desc=True)
    )

    if report_type:
        if report_type not in VALID_REPORT_TYPES:
            return {"error": f"Invalid report_type. Valid: {VALID_REPORT_TYPES}"}, 400
        query = query.eq("report_type", report_type)

    if verified_only:
        query = query.eq("is_verified", True)

    reports = query.execute().data

    if lat is not None and lng is not None:
        reports = _filter_by_radius(reports, lat, lng, radius_km)

    return reports, 200


def get_report_by_id(report_id: str) -> tuple[dict, int]:
    result = supabase.table("road_reports").select("*").eq("id", report_id).single().execute()
    if not result.data:
        return {"error": "Report not found"}, 404
    return result.data, 200


def list_checkpoints() -> tuple[list, int]:
    result = (
        supabase.table("road_reports")
        .select("*")
        .eq("report_type", "checkpoint")
        .eq("is_active", True)
        .eq("is_verified", True)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data, 200


def list_gas_stations() -> tuple[list, int]:
    result = (
        supabase.table("road_reports")
        .select("*")
        .eq("report_type", "gas_station")
        .eq("is_active", True)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data, 200


def update_report(report_id: str, data: dict) -> tuple[dict, int]:
    allowed = {"description", "severity", "is_active", "road_name"}

    if "severity" in data and data["severity"] not in VALID_SEVERITIES:
        return {"error": f"Invalid severity. Valid: {VALID_SEVERITIES}"}, 400

    update_payload = {k: v for k, v in data.items() if k in allowed}
    if not update_payload:
        return {"error": f"No valid fields. Allowed: {allowed}"}, 400

    result = supabase.table("road_reports").update(update_payload).eq("id", report_id).execute()
    if not result.data:
        return {"error": "Report not found"}, 404
    return result.data[0], 200


def delete_report(report_id: str) -> tuple[dict, int]:
    result = supabase.table("road_reports").delete().eq("id", report_id).execute()
    if not result.data:
        return {"error": "Report not found"}, 404
    return {"message": "Report deleted", "id": report_id}, 200