-- Add updated_at column to public.shipments and enable datetime sort in search RPC

set statement_timeout = 0;
set lock_timeout = 0;
set idle_in_transaction_session_timeout = 0;
set client_min_messages = warning;

begin;

-- 1) Add updated_at column if missing
alter table public.shipments
  add column if not exists updated_at timestamptz default now();

-- 2) Ensure helper trigger function exists (created in earlier migrations)
--    Reuse public.update_updated_at_column() to set NEW.updated_at = now()

-- 3) Add/replace trigger to auto-update updated_at on row updates
do $$ begin
  if exists (
    select 1 from pg_trigger
    where tgname = 'update_shipments_updated_at'
  ) then
    drop trigger update_shipments_updated_at on public.shipments;
  end if;
end $$;

create trigger update_shipments_updated_at
before update on public.shipments
for each row execute function public.update_updated_at_column();

-- 4) Update RPC to support datetime sorting and expose updated_at
-- Drop the previous search_shipments_simple with 10 params
drop function if exists public.search_shipments_simple(
  text, text, text, text, text, text, text, text, integer, integer
);

-- Recreate with optional sort_dir and returning updated_at
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
  long_id text,
  tenant_id text,
  shipment_id text,
  load_id text,
  fleet_phone text,
  fleet_name text,
  customer_name text,
  carrier_id text,
  job_id text,
  updated_at timestamptz,
  total_count bigint
) language sql stable as $$
  select
    s.long_id,
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

-- Grants
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


