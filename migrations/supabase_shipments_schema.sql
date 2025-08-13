-- NOTE: This file represented a normalized schema. The project has moved to a minimal raw
-- ingestion approach in `shipments_raw`. Keep this file for future reference only.

-- 1) Parent table: shipments
CREATE TABLE IF NOT EXISTS public.shipments (
    long_id TEXT PRIMARY KEY,
    load_id BIGINT,
    es_export_success BOOLEAN,
    load_status TEXT,
    status TEXT,
    type TEXT,
    load_appointment_type_status TEXT,
    ping_time INT,
    created_on_platform TEXT,
    freight_terms TEXT,
    enable_tracking_emails BOOLEAN,
    is_on_macropoint BOOLEAN,
    is_invoice_sent BOOLEAN,
    skip_sending_invoice BOOLEAN,
    price NUMERIC,
    price_type TEXT,
    distance TEXT,
    es_exported_at TIMESTAMPTZ,
    first_pickup_start_date TIMESTAMPTZ,
    first_dropoff_start_date TIMESTAMPTZ,
    last_dropoff_start_date TIMESTAMPTZ,
    created_at_src TIMESTAMPTZ,
    updated_at_src TIMESTAMPTZ,
    owning_company JSONB,
    customer JSONB,
    customer_user JSONB,
    operator JSONB,
    pricing_person JSONB,
    created_by_user JSONB,
    accounting JSONB,
    carrier_offer_info JSONB,
    timekeeper JSONB,
    last_contact JSONB,
    load JSONB,
    available_on_marketplaces JSONB,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shipments_updated_at ON public.shipments (updated_at_src DESC);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON public.shipments (status);

-- 2) Child table: shipment_stops (pickups and dropoffs)
CREATE TABLE IF NOT EXISTS public.shipment_stops (
    id BIGSERIAL PRIMARY KEY,
    shipment_long_id TEXT NOT NULL REFERENCES public.shipments(long_id) ON DELETE CASCADE,
    external_stop_id TEXT NOT NULL,
    stop_type TEXT CHECK (stop_type IN ('pickup','dropoff')) NOT NULL,
    status TEXT,
    admin_status TEXT,
    date_app_status TEXT,
    order_index INT,
    appt_type TEXT,
    drop_trailer BOOLEAN,
    past_due_email_sent BOOLEAN,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    time_zone_id TEXT,
    location JSONB,
    primary_contact JSONB,
    distances JSONB,
    notes JSONB,
    private_notes JSONB,
    edi_private_notes JSONB,
    start_date_local_text TEXT,
    start_date_local DATE,
    start_time_local TIME,
    sort_date TIMESTAMPTZ,
    raw JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (shipment_long_id, external_stop_id)
);

CREATE INDEX IF NOT EXISTS idx_stops_by_shipment_type_order
ON public.shipment_stops (shipment_long_id, stop_type, order_index);

-- 3) Child table: shipment_offers
CREATE TABLE IF NOT EXISTS public.shipment_offers (
    id BIGSERIAL PRIMARY KEY,
    shipment_long_id TEXT NOT NULL REFERENCES public.shipments(long_id) ON DELETE CASCADE,
    offer_id TEXT NOT NULL,
    price NUMERIC,
    status TEXT,
    created_at_src TIMESTAMPTZ,
    updated_at_src TIMESTAMPTZ,
    created_by_user JSONB,
    created_for_user JSONB,
    raw JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (shipment_long_id, offer_id)
);

CREATE INDEX IF NOT EXISTS idx_offers_by_shipment ON public.shipment_offers (shipment_long_id);

-- 4) Child table: shipment_jobs
CREATE TABLE IF NOT EXISTS public.shipment_jobs (
    id BIGSERIAL PRIMARY KEY,
    shipment_long_id TEXT NOT NULL REFERENCES public.shipments(long_id) ON DELETE CASCADE,
    job_id TEXT NOT NULL,
    status TEXT,
    truck_status TEXT,
    is_on_macropoint BOOLEAN,
    tracked_on_mobile BOOLEAN,
    pick_ups JSONB,
    drop_offs JSONB,
    is_bill_sent BOOLEAN,
    shipment TEXT,
    offer TEXT,
    carrier_id TEXT,
    fleet_manager JSONB,
    contact TEXT,
    driver JSONB,
    second_driver JSONB,
    managed_by_user JSONB,
    price JSONB,
    distances JSONB,
    trailer_number TEXT,
    created_at_src TIMESTAMPTZ,
    updated_at_src TIMESTAMPTZ,
    order_index INT,
    raw JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (shipment_long_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_by_shipment_order
ON public.shipment_jobs (shipment_long_id, order_index);

-- Optional: simple view to summarize stops per shipment
CREATE OR REPLACE VIEW public.v_shipment_stop_counts AS
SELECT s.long_id,
       COUNT(*) FILTER (WHERE st.stop_type = 'pickup') AS pickups,
       COUNT(*) FILTER (WHERE st.stop_type = 'dropoff') AS dropoffs
FROM public.shipments s
LEFT JOIN public.shipment_stops st ON st.shipment_long_id = s.long_id
GROUP BY s.long_id;


