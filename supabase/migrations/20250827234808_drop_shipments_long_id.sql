-- Drop long_id column and recreate search_shipments_simple without it

set statement_timeout = 0;
set lock_timeout = 0;
set idle_in_transaction_session_timeout = 0;
set client_min_messages = warning;

begin;

-- Drop the partial unique index if it exists
DROP INDEX IF EXISTS public.shipments_long_id_uk;

-- Drop the column from public.shipments
ALTER TABLE public.shipments
  DROP COLUMN IF EXISTS long_id;

-- Drop the current version of search_shipments_simple (11 params incl. p_sort_dir)
drop function if exists public.search_shipments_simple(
  text, text, text, text, text, text, text, text, integer, integer, text
);

-- Recreate keeping same signature/logic, but without long_id in the result
create or replace function public.search_shipments_simple(
  p_tenant_id     text default null,
  p_shipment_id   text default null,
  p_load_id       text default null,
  p_fleet_phone   text default null,
  p_fleet_name    text default null,
  p_customer_name text default null,
  p_carrier_id    text default null,
  p_job_id        text default null,
  p_limit         integer default 10,
  p_offset        integer default 0,
  p_sort_dir      text default 'desc'
)
returns table(
  tenant_id   text,
  shipment_id text,
  load_id     text,
  fleet_phone text,
  fleet_name  text,
  customer_name text,
  carrier_id  text,
  job_id      text,
  updated_at  timestamptz,
  total_count bigint
) language sql stable as $$
  select
    s.tenant_id,
    s.shipment_id,
    s.load_id,
    s.fleet_phone,
    s.fleet_name,
    s.customer_name,
    s.carrier_id,
    s.job_id,
    s.updated_at,
    count(*) over() as total_count
  from public.shipments s
  where (p_tenant_id is null     or s.tenant_id     = p_tenant_id)
    and (p_shipment_id is null   or s.shipment_id   = p_shipment_id)
    and (p_load_id is null       or s.load_id       = p_load_id)
    and (
      p_fleet_phone is null
      or s.fleet_phone = p_fleet_phone
      or regexp_replace(coalesce(s.fleet_phone, ''), '[^0-9]', '', 'g') = regexp_replace(p_fleet_phone, '[^0-9]', '', 'g')
    )
    and (
      p_fleet_name is null
      or btrim(p_fleet_name) = ''
      or s.fleet_name ilike ('%' || btrim(p_fleet_name) || '%')
    )
    and (
      p_customer_name is null
      or btrim(p_customer_name) = ''
      or s.customer_name ilike ('%' || btrim(p_customer_name) || '%')
    )
    and (p_carrier_id is null    or s.carrier_id    = p_carrier_id)
    and (p_job_id is null        or s.job_id        = p_job_id)
  order by
    case when lower(coalesce(p_sort_dir, 'desc')) = 'asc' then s.updated_at end asc,
    case when lower(coalesce(p_sort_dir, 'desc')) <> 'asc' then s.updated_at end desc,
    s.job_id asc
  limit coalesce(p_limit, 10)
  offset coalesce(p_offset, 0);
$$;

-- Restore grants
grant all on function public.search_shipments_simple(
  text, text, text, text, text, text, text, text, integer, integer, text
) to anon;
grant all on function public.search_shipments_simple(
  text, text, text, text, text, text, text, text, integer, integer, text
) to authenticated;
grant all on function public.search_shipments_simple(
  text, text, text, text, text, text, text, text, integer, integer, text
) to service_role;

commit;
