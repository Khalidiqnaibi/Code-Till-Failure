-- =============================================================================
-- schema.sql
-- ----------
-- Supabase (PostgreSQL + PostGIS) schema for the Hebron Guide application.
-- Run this against your Supabase project via the SQL editor or migration tool.
-- =============================================================================

-- Enable PostGIS for geospatial queries
CREATE EXTENSION IF NOT EXISTS postgis;


CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- =============================================================================
-- USER PROFILES
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    points      INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Atomic point increment (called from db_adapter._increment_user_points)
CREATE OR REPLACE FUNCTION increment_user_points(uid UUID, delta INTEGER)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    UPDATE user_profiles SET points = points + delta WHERE id = uid;
END;
$$;

-- =============================================================================
-- MODULE 1 — TICKETS
-- =============================================================================

CREATE TABLE IF NOT EXISTS tickets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    national_id     TEXT,                          -- nullable if plate-only violation
    plate_number    TEXT,                          -- nullable if ID-only violation
    violation_type  TEXT NOT NULL,
    location_text   TEXT,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    photo_url       TEXT,
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status          TEXT NOT NULL DEFAULT 'unpaid', -- 'unpaid' | 'paid' | 'disputed'
    amount          NUMERIC(10, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tickets_national_id ON tickets(national_id);
CREATE INDEX IF NOT EXISTS idx_tickets_plate_number ON tickets(plate_number);

CREATE TABLE IF NOT EXISTS payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id       UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    method          TEXT NOT NULL,                 -- 'visa' | 'palestine_pay' | etc.
    amount          NUMERIC(10, 2) NOT NULL,
    reference_id    TEXT,
    paid_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- MODULE 2 — GOVERNMENT DOCUMENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    category        TEXT NOT NULL,                 -- 'municipality' | 'solar' | 'civil_registry' …
    description     TEXT,
    checklist       JSONB,                         -- ordered list of required items
    filling_guide   JSONB,                         -- per-field explanations + common errors
    file_url        TEXT,                          -- downloadable blank form
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_doc_templates_category ON document_templates(category);

CREATE TABLE IF NOT EXISTS document_submissions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    template_id     UUID NOT NULL REFERENCES document_templates(id),
    fields          JSONB NOT NULL,                -- OCR-extracted + user-edited field values
    status          TEXT NOT NULL DEFAULT 'draft', -- 'draft' | 'submitted' | 'approved'
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- MODULE 3 — ROAD STATUS
-- =============================================================================

CREATE TABLE IF NOT EXISTS road_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES user_profiles(id) ON DELETE SET NULL,
    report_type     TEXT NOT NULL,
    -- 'congestion' | 'checkpoint' | 'closure' | 'gas_station' | 'ev_charger'
    description     TEXT,
    location        GEOGRAPHY(POINT, 4326) NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending', -- 'pending' | 'verified' | 'expired'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ GENERATED ALWAYS AS (created_at + INTERVAL '4 hours') STORED
);

CREATE INDEX IF NOT EXISTS idx_road_reports_location ON road_reports USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_road_reports_status   ON road_reports(status);

CREATE TABLE IF NOT EXISTS report_verifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id   UUID NOT NULL REFERENCES road_reports(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (report_id, user_id)                    -- one verification per user per report
);

-- RPC used by db_adapter.get_road_reports_near
CREATE OR REPLACE FUNCTION get_nearby_reports(
    lat          DOUBLE PRECISION,
    lng          DOUBLE PRECISION,
    radius_m     INTEGER,
    filter_type  TEXT DEFAULT NULL
)
RETURNS SETOF road_reports LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT r.*
    FROM road_reports r
    WHERE ST_DWithin(
            r.location,
            ST_SetSRID(ST_MakePoint(lng, lat), 4326)::GEOGRAPHY,
            radius_m
          )
      AND r.status != 'expired'
      AND (filter_type IS NULL OR r.report_type = filter_type)
    ORDER BY r.created_at DESC;
END;
$$;

-- =============================================================================
-- MODULE 4 — SHOPS & PHARMACIES
-- =============================================================================

CREATE TABLE IF NOT EXISTS shops (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,                     -- 'pharmacy' | 'grocery' | 'bakery' | …
    address     TEXT,
    location    GEOGRAPHY(POINT, 4326) NOT NULL,
    phone       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shops_location ON shops USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_shops_category ON shops(category);

CREATE TABLE IF NOT EXISTS shop_status_updates (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shop_id     UUID NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES user_profiles(id) ON DELETE SET NULL,
    is_open     BOOLEAN NOT NULL,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL,
    reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shop_status_shop_id ON shop_status_updates(shop_id, reported_at DESC);

-- RPC used by db_adapter.list_shops_near
CREATE OR REPLACE FUNCTION get_nearby_shops(
    lat             DOUBLE PRECISION,
    lng             DOUBLE PRECISION,
    radius_m        INTEGER,
    filter_category TEXT DEFAULT NULL
)
RETURNS TABLE (
    id          UUID,
    name        TEXT,
    category    TEXT,
    address     TEXT,
    phone       TEXT,
    is_open     BOOLEAN,
    last_update TIMESTAMPTZ
) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.id, s.name, s.category, s.address, s.phone,
        su.is_open,
        su.reported_at AS last_update
    FROM shops s
    LEFT JOIN LATERAL (
        SELECT is_open, reported_at
        FROM shop_status_updates
        WHERE shop_id = s.id
        ORDER BY reported_at DESC
        LIMIT 1
    ) su ON TRUE
    WHERE ST_DWithin(
            s.location,
            ST_SetSRID(ST_MakePoint(lng, lat), 4326)::GEOGRAPHY,
            radius_m
          )
      AND (filter_category IS NULL OR s.category = filter_category)
    ORDER BY ST_Distance(
        s.location,
        ST_SetSRID(ST_MakePoint(lng, lat), 4326)::GEOGRAPHY
    );
END;
$$;

-- =============================================================================
-- EXTRA FEATURE — UTILITY PRICES
-- =============================================================================

CREATE TABLE IF NOT EXISTS utility_prices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    utility_type    TEXT NOT NULL,                 -- 'electricity' | 'water' | 'gas'
    rate            NUMERIC(10, 4) NOT NULL,
    unit            TEXT NOT NULL,                 -- 'kWh' | 'm³' | 'liter'
    effective_date  DATE NOT NULL,
    source          TEXT NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (utility_type, effective_date)
);