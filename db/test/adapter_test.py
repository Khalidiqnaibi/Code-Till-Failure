"""
test_db_adapter.py
------------------
Unit tests for db_adapter.SupabaseAdapter.

Uses unittest.mock to stub the Supabase client so tests remain fast and
offline — no real database connection is required.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from supabase_adapter import SupabaseAdapter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def adapter():
    """Return a SupabaseAdapter with a fully mocked Supabase client."""
    with patch("db_adapter.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        inst = SupabaseAdapter(url="https://fake.supabase.co", key="fake-key")
        inst._client = mock_client
        yield inst, mock_client


def _mock_query(data=None, count=None):
    """Build a mock query chain that returns the given data on .execute()."""
    response = SimpleNamespace(data=data or [], count=count)
    query = MagicMock()
    query.execute.return_value = response
    # Make every chained call return the same mock so .select().eq().limit() works
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.insert.return_value = query
    query.update.return_value = query
    query.upsert.return_value = query
    query.rpc.return_value = query
    return query


# ---------------------------------------------------------------------------
# Module 1 — Tickets
# ---------------------------------------------------------------------------


class TestGetTicketsByNationalId:
    def test_get_tickets_by_national_id_returns_tickets(self, adapter):
        inst, client = adapter
        expected = [{"id": "t1", "national_id": "99999"}]
        q = _mock_query(data=expected)
        client.table.return_value = q

        result = inst.get_tickets_by_national_id("99999")

        assert result["status"] == "success"
        assert result["data"] == expected

    def test_get_tickets_by_national_id_rejects_empty_id(self, adapter):
        inst, _ = adapter
        result = inst.get_tickets_by_national_id("")
        assert result["status"] == "error"

    def test_get_tickets_by_plate_returns_tickets(self, adapter):
        inst, client = adapter
        expected = [{"id": "t2", "plate_number": "A-123"}]
        q = _mock_query(data=expected)
        client.table.return_value = q

        result = inst.get_tickets_by_plate("a-123")  # should upper-case internally

        assert result["status"] == "success"
        assert result["data"] == expected


class TestCreatePaymentRecord:
    def test_create_payment_record_success(self, adapter):
        inst, client = adapter
        payment_row = [{"id": "pay-1", "ticket_id": "t1"}]
        q = _mock_query(data=payment_row)
        client.table.return_value = q

        result = inst.create_payment_record(
            "t1", {"method": "visa", "amount": 150, "reference_id": "REF-1"}
        )

        assert result["status"] == "success"

    def test_create_payment_record_rejects_empty_ticket_id(self, adapter):
        inst, _ = adapter
        result = inst.create_payment_record("", {"method": "visa", "amount": 50})
        assert result["status"] == "error"

    def test_create_payment_record_rejects_empty_payload(self, adapter):
        inst, _ = adapter
        result = inst.create_payment_record("t1", {})
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Module 2 — Government Documents
# ---------------------------------------------------------------------------


class TestDocumentTemplates:
    def test_list_document_templates_no_filter(self, adapter):
        inst, client = adapter
        templates = [{"id": "tmpl-1", "title": "Solar Permit", "category": "solar"}]
        q = _mock_query(data=templates)
        client.table.return_value = q

        result = inst.list_document_templates()

        assert result["status"] == "success"
        assert len(result["data"]) == 1

    def test_get_document_template_not_found(self, adapter):
        inst, client = adapter
        q = _mock_query(data=[])
        client.table.return_value = q

        result = inst.get_document_template("nonexistent-id")

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    def test_get_document_template_returns_single_record(self, adapter):
        inst, client = adapter
        record = {"id": "tmpl-1", "title": "Solar Permit"}
        q = _mock_query(data=[record])
        client.table.return_value = q

        result = inst.get_document_template("tmpl-1")

        assert result["status"] == "success"
        assert result["data"]["id"] == "tmpl-1"

    def test_save_ocr_submission_rejects_missing_ids(self, adapter):
        inst, _ = adapter
        result = inst.save_ocr_submission("", "tmpl-1", {"field": "value"})
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Module 3 — Road Status
# ---------------------------------------------------------------------------


class TestRoadReports:
    def test_submit_road_report_success(self, adapter):
        inst, client = adapter
        created = [{"id": "rpt-1", "status": "pending"}]
        q = _mock_query(data=created)
        client.table.return_value = q
        client.rpc.return_value = q

        result = inst.submit_road_report(
            {
                "user_id": "usr-1",
                "report_type": "checkpoint",
                "latitude": 31.5,
                "longitude": 35.1,
            }
        )

        assert result["status"] == "success"

    def test_submit_road_report_missing_fields(self, adapter):
        inst, _ = adapter
        result = inst.submit_road_report({"user_id": "usr-1"})  # missing lat/lng/type
        assert result["status"] == "error"
        assert "Missing required" in result["message"]

    def test_verify_road_report_awards_points_at_threshold(self, adapter):
        inst, client = adapter

        # Simulate verification count == REPORT_VERIFICATION_THRESHOLD (25)
        verify_insert_q = _mock_query(data=[{"id": "v-1"}])
        count_response = SimpleNamespace(data=[], count=25)
        count_q = MagicMock()
        count_q.select.return_value = count_q
        count_q.eq.return_value = count_q
        count_q.execute.return_value = count_response

        original_report_q = _mock_query(data=[{"user_id": "usr-original"}])

        def table_side_effect(name):
            if name == "report_verifications":
                return verify_insert_q
            if name == "road_reports":
                return original_report_q
            return verify_insert_q

        client.table.side_effect = table_side_effect
        # Override internal count call
        inst._client.table = client.table

        # Patch the internal count query to return 25
        with patch.object(inst._client, "table") as mock_table:
            mock_table.return_value = count_q
            # Re-route only the count call; simplest approach: use full mock
            count_q.insert.return_value = count_q
            count_q.update.return_value = count_q
            count_q.limit.return_value = count_q
            count_q.order.return_value = count_q

            result = inst.verify_road_report("rpt-1", "usr-2")

        # Because all table() calls hit count_q which returns count=25
        assert result["status"] == "success"
        assert result["data"]["verification_count"] == 25
        assert result["data"]["threshold_reached"] is True


# ---------------------------------------------------------------------------
# Module 4 — Shops & Pharmacies
# ---------------------------------------------------------------------------


class TestShops:
    def test_update_shop_status_success(self, adapter):
        inst, client = adapter
        row = [{"id": "upd-1", "shop_id": "shop-1", "is_open": True}]
        q = _mock_query(data=row)
        client.table.return_value = q

        result = inst.update_shop_status("shop-1", "usr-1", True, 31.5, 35.1)

        assert result["status"] == "success"

    def test_update_shop_status_rejects_missing_ids(self, adapter):
        inst, _ = adapter
        result = inst.update_shop_status("", "usr-1", True, 31.5, 35.1)
        assert result["status"] == "error"

    def test_get_shop_by_id_not_found(self, adapter):
        inst, client = adapter
        q = _mock_query(data=[])
        client.table.return_value = q

        result = inst.get_shop_by_id("nonexistent")

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Extra Feature — Utility Prices
# ---------------------------------------------------------------------------


class TestUtilityPrices:
    def test_get_utility_prices_all(self, adapter):
        inst, client = adapter
        rows = [{"utility_type": "electricity", "rate": 0.68}]
        q = _mock_query(data=rows)
        client.table.return_value = q

        result = inst.get_utility_prices()

        assert result["status"] == "success"
        assert result["data"][0]["utility_type"] == "electricity"

    def test_upsert_utility_price_missing_fields(self, adapter):
        inst, _ = adapter
        result = inst.upsert_utility_price({"utility_type": "water"})  # incomplete
        assert result["status"] == "error"
        assert "Missing required" in result["message"]

    def test_upsert_utility_price_success(self, adapter):
        inst, client = adapter
        row = [{"id": "up-1"}]
        q = _mock_query(data=row)
        client.table.return_value = q

        result = inst.upsert_utility_price(
            {
                "utility_type": "electricity",
                "rate": 0.68,
                "unit": "kWh",
                "effective_date": "2025-07-01",
                "source": "Hebron Electric Institution",
            }
        )

        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# User Points
# ---------------------------------------------------------------------------


class TestUserPoints:
    def test_get_user_points_success(self, adapter):
        inst, client = adapter
        q = _mock_query(data=[{"id": "usr-1", "points": 7}])
        client.table.return_value = q

        result = inst.get_user_points("usr-1")

        assert result["status"] == "success"
        assert result["data"]["points"] == 7

    def test_get_user_points_rejects_empty_user_id(self, adapter):
        inst, _ = adapter
        result = inst.get_user_points("")
        assert result["status"] == "error"

    def test_get_user_points_user_not_found(self, adapter):
        inst, client = adapter
        q = _mock_query(data=[])
        client.table.return_value = q

        result = inst.get_user_points("ghost-user")

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()