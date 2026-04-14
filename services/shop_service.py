from supabase import create_client
from math import radians, cos, sin, asin, sqrt
import os

supabase = create_client("https://mlosocwinwylysatnbtm.supabase.co", "sb_publishable_BXfqbXN8BV7pqEvMCdPexA_CeV1ERGQ")

DEFAULT_RADIUS_KM = 5.0
VALID_CATEGORIES  = {
    "pharmacy", "grocery", "bakery", "restaurant",
    "cafe", "electronics", "clothing", "hardware", "other",
}


# ── Geo helper ────────────────────────────────────────────────────────────────

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * asin(sqrt(a))


def _attach_distance_and_filter(
    shops: list[dict],
    lat: float,
    lng: float,
    radius_km: float,
) -> list[dict]:
    """Filter shops to radius_km and attach distance_km, sorted nearest first."""
    result = []
    for shop in shops:
        dist = _haversine(lat, lng, shop["latitude"], shop["longitude"])
        if dist <= radius_km:
            result.append({**shop, "distance_km": round(dist, 2)})
    result.sort(key=lambda s: s["distance_km"])
    return result


# ── Shops CRUD ────────────────────────────────────────────────────────────────

def create_shop(data: dict) -> tuple[dict, int]:
    required = {"name", "category", "latitude", "longitude"}
    missing = required - data.keys()
    if missing:
        return {"error": f"Missing fields: {', '.join(missing)}"}, 400

    if data["category"] not in VALID_CATEGORIES:
        return {"error": f"Invalid category. Valid: {VALID_CATEGORIES}"}, 400

    payload = {
        "name":      data["name"],
        "category":  data["category"],
        "latitude":  data["latitude"],
        "longitude": data["longitude"],
        "address":   data.get("address"),
        "phone":     data.get("phone"),
        "is_open":   data.get("is_open", True),
    }

    result = supabase.table("shops").insert(payload).execute()
    return result.data[0], 201


def list_shops(
    category: str | None,
    is_open: bool | None,
    search: str | None,
    lat: float | None,
    lng: float | None,
    radius_km: float,
) -> tuple[list | dict, int]:
    if category and category not in VALID_CATEGORIES:
        return {"error": f"Invalid category. Valid: {VALID_CATEGORIES}"}, 400

    query = supabase.table("shops").select("*")

    if category:
        query = query.eq("category", category)
    if is_open is not None:
        query = query.eq("is_open", is_open)
    if search:
        query = query.ilike("name", f"%{search}%")

    shops = query.order("name").execute().data

    if lat is not None and lng is not None:
        shops = _attach_distance_and_filter(shops, lat, lng, radius_km)

    return shops, 200


def get_shop_by_id(shop_id: str) -> tuple[dict, int]:
    result = supabase.table("shops").select("*").eq("id", shop_id).single().execute()
    if not result.data:
        return {"error": "Shop not found"}, 404
    return result.data, 200


def update_shop(shop_id: str, data: dict) -> tuple[dict, int]:
    allowed = {"name", "category", "address", "phone", "latitude", "longitude"}

    if "category" in data and data["category"] not in VALID_CATEGORIES:
        return {"error": f"Invalid category. Valid: {VALID_CATEGORIES}"}, 400

    update_payload = {k: v for k, v in data.items() if k in allowed}
    if not update_payload:
        return {"error": f"No valid fields to update. Allowed: {allowed}"}, 400

    result = supabase.table("shops").update(update_payload).eq("id", shop_id).execute()
    if not result.data:
        return {"error": "Shop not found"}, 404
    return result.data[0], 200


def delete_shop(shop_id: str) -> tuple[dict, int]:
    result = supabase.table("shops").delete().eq("id", shop_id).execute()
    if not result.data:
        return {"error": "Shop not found"}, 404
    return {"message": "Shop deleted", "id": shop_id}, 200


# ── Status Updates ────────────────────────────────────────────────────────────

def report_shop_status(shop_id: str, data: dict) -> tuple[dict, int]:
    """
    Community member reports current open/closed status.
    Validates GPS presence, logs the update, and flips the shop's live status.
    """
    required = {"user_id", "is_open", "latitude", "longitude"}
    missing = required - data.keys()
    if missing:
        return {"error": f"Missing fields: {', '.join(missing)}"}, 400

    if not isinstance(data["is_open"], bool):
        return {"error": "is_open must be a boolean"}, 400

    # Verify shop exists
    shop_res = supabase.table("shops").select("id, latitude, longitude").eq("id", shop_id).single().execute()
    if not shop_res.data:
        return {"error": "Shop not found"}, 404

    # Log the community report
    supabase.table("shop_status_logs").insert({
        "shop_id":   shop_id,
        "user_id":   data["user_id"],
        "is_open":   data["is_open"],
        "latitude":  data["latitude"],
        "longitude": data["longitude"],
    }).execute()

    # Update live status on the shop record
    updated = supabase.table("shops").update({"is_open": data["is_open"]}).eq("id", shop_id).execute()
    return {
        "message":  "Status updated",
        "shop_id":  shop_id,
        "is_open":  data["is_open"],
        "shop":     updated.data[0],
    }, 200


def get_status_history(shop_id: str, limit: int = 20) -> tuple[list | dict, int]:
    # Verify shop exists first
    shop_res = supabase.table("shops").select("id").eq("id", shop_id).single().execute()
    if not shop_res.data:
        return {"error": "Shop not found"}, 404

    result = (
        supabase.table("shop_status_logs")
        .select("*")
        .eq("shop_id", shop_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data, 200


# ── Pharmacies (convenience wrapper) ─────────────────────────────────────────

def list_pharmacies(
    is_open: bool | None,
    lat: float | None,
    lng: float | None,
    radius_km: float,
) -> tuple[list | dict, int]:
    """Thin wrapper around list_shops locked to the pharmacy category."""
    return list_shops(
        category="pharmacy",
        is_open=is_open,
        search=None,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
    )