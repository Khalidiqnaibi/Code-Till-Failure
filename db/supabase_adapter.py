"""
db_adapter.py
-------------
Supabase database adapter for the Hebron Guide application.

Provides a clean, typed interface over the Supabase Python client for all four
modules: Tickets, Government Documents, Road Status, and Shops & Pharmacies,
plus the Live Utility Prices extra feature.

All public functions follow the project naming convention (snake_case verbs),
return explicit dicts with { "status", "data", "message" } shapes, and never
mutate input arguments.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from supabase import Client, create_client

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_RETRIES: int = 3
REPORT_VERIFICATION_THRESHOLD: int = 25  # matching reports required to verify
DEFAULT_RADIUS_METERS: int = 500  # proximity for shops / road reports

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


class SupabaseAdapter:
    """
    Central adapter wrapping the Supabase client.

    Instantiate once per process and inject where needed.

    Args:
        url (str): Supabase project URL.
        key (str): Supabase anon or service-role key.

    Example:
        adapter = SupabaseAdapter(url=SUPABASE_URL, key=SUPABASE_KEY)
    """

    def __init__(self, url: str, key: str) -> None:
        self._client: Client = create_client(url, key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ok(self, data: Any, message: str = "") -> dict:
        """Wrap a successful result in the standard response envelope."""
        return {"status": "success", "data": data, "message": message}

    def _err(self, message: str, data: Any = None) -> dict:
        """Wrap an error in the standard response envelope."""
        logger.error("db_adapter error: %s", message)
        return {"status": "error", "data": data, "message": message}

    def _safe_execute(self, query) -> tuple[Any, str | None]:
        """
        Execute a Supabase query and return (data, error_message).

        Args:
            query: A Supabase query builder object with an .execute() method.

        Returns:
            tuple: (response_data, error_string_or_None)
        """
        try:
            response = query.execute()
            return response.data, None
        except Exception as exc:  # noqa: BLE001
            return None, str(exc)

    # ==================================================================
    # MODULE 1 — TICKETS
    # ==================================================================

    def get_tickets_by_national_id(self, national_id: str) -> dict:
        """
        Fetch all tickets associated with a citizen's national ID.

        Args:
            national_id (str): The citizen's national identification number.

        Returns:
            dict: Standard envelope; data is a list of ticket records.

        Example:
            result = adapter.get_tickets_by_national_id("12345678")
        """
        if not national_id or not national_id.strip():
            return self._err("national_id cannot be empty")

        query = (
            self._client.table("tickets")
            .select("*")
            .eq("national_id", national_id.strip())
            .order("issued_at", desc=True)
        )
        data, error = self._safe_execute(query)
        if error:
            return self._err(f"Failed to fetch tickets by national ID: {error}")
        return self._ok(data)

    def get_tickets_by_plate(self, plate_number: str) -> dict:
        """
        Fetch all tickets associated with a vehicle plate number.

        Args:
            plate_number (str): The vehicle's plate/license number.

        Returns:
            dict: Standard envelope; data is a list of ticket records.

        Example:
            result = adapter.get_tickets_by_plate("A-12345")
        """
        if not plate_number or not plate_number.strip():
            return self._err("plate_number cannot be empty")

        query = (
            self._client.table("tickets")
            .select("*")
            .eq("plate_number", plate_number.strip().upper())
            .order("issued_at", desc=True)
        )
        data, error = self._safe_execute(query)
        if error:
            return self._err(f"Failed to fetch tickets by plate: {error}")
        return self._ok(data)

    def create_payment_record(self, ticket_id: str, payment_payload: dict) -> dict:
        """
        Insert a payment record and mark the linked ticket as paid.

        Args:
            ticket_id (str): UUID of the ticket being paid.
            payment_payload (dict): Payment details (method, amount, reference_id, …).

        Returns:
            dict: Standard envelope; data contains the created payment row.

        Side effects:
            Updates tickets.status to 'paid' for the given ticket_id.

        Example:
            result = adapter.create_payment_record(
                "abc-123",
                {"method": "visa", "amount": 150, "reference_id": "PAY-001"}
            )
        """
        if not ticket_id:
            return self._err("ticket_id cannot be empty")
        if not payment_payload:
            return self._err("payment_payload cannot be empty")

        # NOTE: A real implementation should wrap these two writes in a
        # Supabase database function / RPC call to ensure atomicity.
        record = {
            **payment_payload,
            "ticket_id": ticket_id,
            "paid_at": datetime.utcnow().isoformat(),
        }
        insert_query = self._client.table("payments").insert(record)
        payment_data, error = self._safe_execute(insert_query)
        if error:
            return self._err(f"Failed to create payment record: {error}")

        update_query = (
            self._client.table("tickets")
            .update({"status": "paid"})
            .eq("id", ticket_id)
        )
        _, update_error = self._safe_execute(update_query)
        if update_error:
            return self._err(
                f"Payment recorded but ticket status update failed: {update_error}",
                data=payment_data,
            )

        return self._ok(payment_data, message="Payment recorded and ticket marked paid")

    # ==================================================================
    # MODULE 2 — GOVERNMENT DOCUMENTS
    # ==================================================================

    def list_document_templates(self, category: str | None = None) -> dict:
        """
        Retrieve the library of government document templates.

        Args:
            category (str, optional): Filter by category slug
                (e.g. 'municipality', 'solar', 'civil_registry').

        Returns:
            dict: Standard envelope; data is a list of template metadata rows.

        Example:
            result = adapter.list_document_templates(category="solar")
        """
        query = self._client.table("document_templates").select(
            "id, title, category, description, checklist, created_at"
        )
        if category:
            query = query.eq("category", category)
        query = query.order("title")

        data, error = self._safe_execute(query)
        if error:
            return self._err(f"Failed to list document templates: {error}")
        return self._ok(data)

    def get_document_template(self, template_id: str) -> dict:
        """
        Fetch a single document template including its filling guide.

        Args:
            template_id (str): UUID of the template.

        Returns:
            dict: Standard envelope; data is the full template row (including
                  checklist_items and filling_guide fields).

        Example:
            result = adapter.get_document_template("tmpl-uuid-here")
        
        """
        if not template_id:
            return self._err("template_id cannot be empty")

        query = (
            self._client.table("document_templates")
            .select("*")
            .eq("id", template_id)
            .limit(1)
        )
        data, error = self._safe_execute(query)
        if error:
            return self._err(f"Failed to fetch template: {error}")
        if not data:
            return self._err("Template not found", data=[])
        return self._ok(data[0])

    def save_ocr_submission(self, user_id: str, template_id: str, ocr_payload: dict) -> dict:
        """
        Persist an OCR-filled document submission for a user.

        Args:
            user_id (str): UUID of the authenticated user.
            template_id (str): UUID of the template being filled.
            ocr_payload (dict): Extracted field values from the OCR scan.

        Returns:
            dict: Standard envelope; data is the created submission row.

        Example:
            result = adapter.save_ocr_submission(
                user_id="usr-001",
                template_id="tmpl-abc",
                ocr_payload={"owner_name": "Ahmad", "plot_number": "42B"}
            )
        """
        if not user_id or not template_id:
            return self._err("user_id and template_id are required")
        if not ocr_payload:
            return self._err("ocr_payload cannot be empty")

        record = {
            "user_id": user_id,
            "template_id": template_id,
            "fields": ocr_payload,
            "submitted_at": datetime.utcnow().isoformat(),
            "status": "draft",
        }
        query = self._client.table("document_submissions").insert(record)
        data, error = self._safe_execute(query)
        if error:
            return self._err(f"Failed to save OCR submission: {error}")
        return self._ok(data, message="Submission saved")

    # ==================================================================
    # MODULE 3 — ROAD STATUS
    # ==================================================================

    def submit_road_report(self, report: dict) -> dict:
        """
        Insert a new community road-status report.

        The report is created with status='pending'; it transitions to
        'verified' once REPORT_VERIFICATION_THRESHOLD matching reports exist
        (enforced by a Supabase trigger or a separate verification job).

        Args:
            report (dict): Must include:
                - user_id (str)
                - report_type (str): 'congestion'|'checkpoint'|'closure'|'gas_station'|'ev_charger'
                - latitude (float)
                - longitude (float)
                - description (str, optional)

        Returns:
            dict: Standard envelope; data is the created report row.

        Example:
            result = adapter.submit_road_report({
                "user_id": "usr-001",
                "report_type": "checkpoint",
                "latitude": 31.5326,
                "longitude": 35.0998,
                "description": "IDF checkpoint on Jaber street"
            })
        """
        required_fields = {"user_id", "report_type", "latitude", "longitude"}
        missing = required_fields - report.keys()
        if missing:
            return self._err(f"Missing required report fields: {missing}")

        record = {
            **report,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }
        query = self._client.table("road_reports").insert(record)
        data, error = self._safe_execute(query)
        if error:
            return self._err(f"Failed to submit road report: {error}")

        # Award 1 point for the submission (verified separately)
        self._increment_user_points(report["user_id"], delta=0)  # points on verify

        return self._ok(data, message="Report submitted; pending verification")

    def get_road_reports_near(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = DEFAULT_RADIUS_METERS,
        report_type: str | None = None,
    ) -> dict:
        """
        Fetch active road reports within a given radius using PostGIS RPC.

        Args:
            latitude (float): Observer's latitude.
            longitude (float): Observer's longitude.
            radius_meters (int): Search radius in metres (default 500).
            report_type (str, optional): Filter by report type.

        Returns:
            dict: Standard envelope; data is a list of nearby report rows.

        Example:
            result = adapter.get_road_reports_near(31.5326, 35.0998, radius_meters=1000)
        """
        params: dict = {
            "lat": latitude,
            "lng": longitude,
            "radius_m": radius_meters,
        }
        if report_type:
            params["filter_type"] = report_type

        # NOTE: Requires a Supabase RPC function `get_nearby_reports(lat, lng, radius_m, filter_type)`
        query = self._client.rpc("get_nearby_reports", params)
        data, error = self._safe_execute(query)
        if error:
            return self._err(f"Failed to fetch nearby road reports: {error}")
        return self._ok(data)

    def verify_road_report(self, report_id: str, verifying_user_id: str) -> dict:
        """
        Record a user's corroboration of an existing road report and check
        whether the verification threshold has been reached.

        Args:
            report_id (str): UUID of the report being corroborated.
            verifying_user_id (str): UUID of the user confirming the report.

        Returns:
            dict: Standard envelope; data includes updated report status and
                  whether the threshold was crossed.

        Side effects:
            - Inserts a row into report_verifications.
            - If threshold reached, updates road_reports.status to 'verified'
              and awards the original reporter 1 point.

        Example:
            result = adapter.verify_road_report("rpt-001", "usr-002")
        """
        if not report_id or not verifying_user_id:
            return self._err("report_id and verifying_user_id are required")

        # Insert verification record
        verification = {
            "report_id": report_id,
            "user_id": verifying_user_id,
            "created_at": datetime.utcnow().isoformat(),
        }
        insert_query = self._client.table("report_verifications").insert(verification)
        _, error = self._safe_execute(insert_query)
        if error:
            return self._err(f"Failed to record verification: {error}")

        # Count total verifications for this report
        count_query = (
            self._client.table("report_verifications")
            .select("id", count="exact")
            .eq("report_id", report_id)
        )
        count_response = count_query.execute()
        total_verifications = count_response.count or 0

        threshold_reached = total_verifications >= REPORT_VERIFICATION_THRESHOLD
        if threshold_reached:
            # Mark report as verified
            self._client.table("road_reports").update(
                {"status": "verified"}
            ).eq("id", report_id).execute()

            # Award original reporter 1 point
            original = (
                self._client.table("road_reports")
                .select("user_id")
                .eq("id", report_id)
                .limit(1)
                .execute()
            )
            if original.data:
                self._increment_user_points(original.data[0]["user_id"], delta=1)

        return self._ok(
            {
                "report_id": report_id,
                "verification_count": total_verifications,
                "threshold_reached": threshold_reached,
            },
            message="Verified" if threshold_reached else "Verification recorded",
        )

    # ==================================================================
    # MODULE 4 — SHOPS & PHARMACIES
    # ==================================================================

    def list_shops_near(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = DEFAULT_RADIUS_METERS,
        category: str | None = None,
    ) -> dict:
        """
        Return shops/pharmacies near a GPS coordinate, optionally filtered by category.

        Args:
            latitude (float): User's latitude.
            longitude (float): User's longitude.
            radius_meters (int): Search radius (default 500 m).
            category (str, optional): e.g. 'pharmacy', 'grocery', 'bakery'.

        Returns:
            dict: Standard envelope; data is a list of shop rows with
                  current open/closed status.

        Example:
            result = adapter.list_shops_near(31.5326, 35.0998, category="pharmacy")
        """
        params: dict = {
            "lat": latitude,
            "lng": longitude,
            "radius_m": radius_meters,
        }
        if category:
            params["filter_category"] = category

        # NOTE: Requires Supabase RPC `get_nearby_shops(lat, lng, radius_m, filter_category)`
        query = self._client.rpc("get_nearby_shops", params)
        data, error = self._safe_execute(query)
        if error:
            return self._err(f"Failed to fetch nearby shops: {error}")
        return self._ok(data)

    def update_shop_status(
        self, shop_id: str, reporter_user_id: str, is_open: bool, latitude: float, longitude: float
    ) -> dict:
        """
        Record a crowd-sourced open/closed status update for a shop.

        GPS coordinates are stored so an AI / moderation layer can reject
        updates from users not physically near the location.

        Args:
            shop_id (str): UUID of the shop.
            reporter_user_id (str): UUID of the reporting user.
            is_open (bool): True if reporting open, False if closed.
            latitude (float): Reporter's current latitude.
            longitude (float): Reporter's current longitude.

        Returns:
            dict: Standard envelope; data is the created status_update row.

        Example:
            result = adapter.update_shop_status(
                "shop-uuid", "usr-001", is_open=True, latitude=31.53, longitude=35.09
            )
        """
        if not shop_id or not reporter_user_id:
            return self._err("shop_id and reporter_user_id are required")

        record = {
            "shop_id": shop_id,
            "user_id": reporter_user_id,
            "is_open": is_open,
            "reported_at": datetime.utcnow().isoformat(),
            "latitude": latitude,
            "longitude": longitude,
        }
        query = self._client.table("shop_status_updates").insert(record)
        data, error = self._safe_execute(query)
        if error:
            return self._err(f"Failed to update shop status: {error}")
        return self._ok(data, message="Shop status update recorded")

    def get_shop_by_id(self, shop_id: str) -> dict:
        """
        Fetch a single shop record including its latest crowd-sourced status.

        Args:
            shop_id (str): UUID of the shop.

        Returns:
            dict: Standard envelope; data is the shop row with latest_status field.

        Example:
            result = adapter.get_shop_by_id("shop-uuid")
        """
        if not shop_id:
            return self._err("shop_id cannot be empty")

        query = (
            self._client.table("shops")
            .select("*, shop_status_updates(is_open, reported_at)")
            .eq("id", shop_id)
            .order("shop_status_updates.reported_at", desc=True)
            .limit(1)
        )
        data, error = self._safe_execute(query)
        if error:
            return self._err(f"Failed to fetch shop: {error}")
        if not data:
            return self._err("Shop not found", data=[])
        return self._ok(data[0])

    # ==================================================================
    # EXTRA FEATURE — LIVE UTILITY PRICES
    # ==================================================================

    def get_utility_prices(self, utility_type: str | None = None) -> dict:
        """
        Fetch current utility pricing from the database.

        Prices are ingested via a separate ETL job that pulls from
        the Hebron Electric Institution and water authority feeds.

        Args:
            utility_type (str, optional): Filter by type —
                'electricity' | 'water' | 'gas'.

        Returns:
            dict: Standard envelope; data is a list of price records
                  with unit, rate, effective_date, and source fields.

        Example:
            result = adapter.get_utility_prices(utility_type="electricity")
        """
        query = self._client.table("utility_prices").select(
            "id, utility_type, rate, unit, effective_date, source, updated_at"
        )
        if utility_type:
            query = query.eq("utility_type", utility_type)
        query = query.order("effective_date", desc=True)

        data, error = self._safe_execute(query)
        if error:
            return self._err(f"Failed to fetch utility prices: {error}")
        return self._ok(data)

    def upsert_utility_price(self, price_record: dict) -> dict:
        """
        Insert or update a utility price row (used by the ETL ingestion job).

        Args:
            price_record (dict): Must include:
                - utility_type (str)
                - rate (float)
                - unit (str): e.g. 'kWh', 'm³', 'liter'
                - effective_date (str): ISO date string
                - source (str): Originating institution name

        Returns:
            dict: Standard envelope; data is the upserted row.

        Example:
            result = adapter.upsert_utility_price({
                "utility_type": "electricity",
                "rate": 0.68,
                "unit": "kWh",
                "effective_date": "2025-07-01",
                "source": "Hebron Electric Institution"
            })
        """
        required_fields = {"utility_type", "rate", "unit", "effective_date", "source"}
        missing = required_fields - price_record.keys()
        if missing:
            return self._err(f"Missing required price fields: {missing}")

        record = {
            **price_record,
            "updated_at": datetime.utcnow().isoformat(),
        }
        query = self._client.table("utility_prices").upsert(
            record, on_conflict="utility_type,effective_date"
        )
        data, error = self._safe_execute(query)
        if error:
            return self._err(f"Failed to upsert utility price: {error}")
        return self._ok(data, message="Utility price upserted")

    # ==================================================================
    # USER / POINTS HELPER
    # ==================================================================

    def _increment_user_points(self, user_id: str, delta: int) -> None:
        """
        Atomically increment a user's point balance.

        Args:
            user_id (str): UUID of the user.
            delta (int): Points to add (may be 0 for no-op).

        Side effects:
            Calls Supabase RPC `increment_user_points(uid, delta)`.
        """
        if delta <= 0:
            return
        try:
            self._client.rpc(
                "increment_user_points", {"uid": user_id, "delta": delta}
            ).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to increment points for %s: %s", user_id, exc)

    def get_user_points(self, user_id: str) -> dict:
        """
        Retrieve the total point balance for a user.

        Args:
            user_id (str): UUID of the user.

        Returns:
            dict: Standard envelope; data contains { user_id, points }.

        Example:
            result = adapter.get_user_points("usr-001")
        """
        if not user_id:
            return self._err("user_id cannot be empty")

        query = (
            self._client.table("user_profiles")
            .select("id, points")
            .eq("id", user_id)
            .limit(1)
        )
        data, error = self._safe_execute(query)
        if error:
            return self._err(f"Failed to fetch user points: {error}")
        if not data:
            return self._err("User not found", data={})
        return self._ok({"user_id": user_id, "points": data[0].get("points", 0)})