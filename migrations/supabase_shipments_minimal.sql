-- Minimal raw ingestion table for shipments
-- Stores tenant_id (for indexing/partitioning later) and full payload JSON

CREATE TABLE IF NOT EXISTS public.shipments(
    id BIGSERIAL PRIMARY KEY,
    long_id TEXT UNIQUE,
    tenant_id TEXT,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shipments_tenant ON public.shipments (tenant_id);
CREATE INDEX IF NOT EXISTS idx_shipments_created_at ON public.shipments (created_at DESC);


