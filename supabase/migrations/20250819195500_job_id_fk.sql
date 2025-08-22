-- Migrate linkage between public.shipments and public.shipment_data to use job_id as the key
-- Drops data_id usage and foreign key, promotes shipment_data.job_id to primary key and FK to shipments(job_id)

set statement_timeout = 0;
set lock_timeout = 0;
set idle_in_transaction_session_timeout = 0;
set client_min_messages = warning;

begin;

-- 1) Add job_id column to shipment_data if missing
alter table public.shipment_data
  add column if not exists job_id text;

-- 2) Backfill shipment_data.job_id from shipments.data_id mapping
update public.shipment_data sd
set job_id = s.job_id
from public.shipments s
where s.data_id is not null
  and sd.data_id = s.data_id
  and (sd.job_id is null or sd.job_id <> s.job_id);

-- 3) As a fallback, derive job_id from payload->job->_id if present
update public.shipment_data
set job_id = coalesce(job_id, (payload->'job'->>'_id'))
where job_id is null
  and payload ? 'job';

-- 4) Drop FK on shipments.data_id -> shipment_data.data_id (if present)
do $$ begin
  if exists (
    select 1 from pg_constraint c
    join pg_class t on t.oid = c.conrelid
    where t.relname = 'shipments' and c.conname = 'shipments_data_fk'
  ) then
    alter table public.shipments drop constraint shipments_data_fk;
  end if;
end $$;

-- 5) Deduplicate shipment_data rows on job_id, keep first
with ranked as (
  select ctid, job_id, row_number() over(partition by job_id order by ctid) as rn
  from public.shipment_data
  where job_id is not null
)
delete from public.shipment_data d
using ranked r
where d.ctid = r.ctid and r.rn > 1;

-- 6) Enforce NOT NULL on job_id
alter table public.shipment_data
  alter column job_id set not null;

-- 7) Replace primary key from data_id to job_id (if needed)
do $$ begin
  if exists (
    select 1 from pg_constraint c
    join pg_class t on t.oid = c.conrelid
    where t.relname = 'shipment_data' and c.contype = 'p' and c.conname = 'shipment_data_pkey'
  ) then
    alter table public.shipment_data drop constraint shipment_data_pkey;
  end if;
end $$;

alter table public.shipment_data
  add constraint shipment_data_pkey primary key (job_id);

-- 8) Link shipment_data.job_id -> shipments.job_id
do $$ begin
  if not exists (
    select 1 from information_schema.table_constraints 
    where table_schema = 'public' and table_name = 'shipment_data' and constraint_name = 'shipment_data_shipments_job_fk'
  ) then
    alter table public.shipment_data
      add constraint shipment_data_shipments_job_fk
      foreign key (job_id) references public.shipments(job_id) on delete cascade;
  end if;
end $$;

-- 9) Drop data_id artifacts
do $$ begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'shipments' and column_name = 'data_id'
  ) then
    -- Drop index if exists
    if exists (select 1 from pg_class where relname = 'shipments_data_id_idx') then
      drop index if exists public.shipments_data_id_idx;
    end if;
    alter table public.shipments drop column data_id;
  end if;
end $$;

do $$ begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'shipment_data' and column_name = 'data_id'
  ) then
    alter table public.shipment_data drop column data_id;
  end if;
end $$;

-- 10) Update RPC: search_shipments_simple to stop returning data_id
-- Drop the old function first because return type is changing
drop function if exists public.search_shipments_simple(
  text, text, text, text, text, text, text, text, integer, integer
);

create or replace function public.search_shipments_simple(
  p_tenant_id    text default null,
  p_shipment_id  text default null,
  p_load_id      text default null,
  p_fleet_phone  text default null,
  p_fleet_name   text default null,
  p_customer_name text default null,
  p_carrier_id   text default null,
  p_job_id       text default null,
  p_limit        integer default 10,
  p_offset       integer default 0
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
  order by s.long_id nulls last
  limit coalesce(p_limit, 10)
  offset coalesce(p_offset, 0);
$$;

-- Re-grant permissions
grant all on function public.search_shipments_simple(
  text, text, text, text, text, text, text, text, integer, integer
) to anon;
grant all on function public.search_shipments_simple(
  text, text, text, text, text, text, text, text, integer, integer
) to authenticated;
grant all on function public.search_shipments_simple(
  text, text, text, text, text, text, text, text, integer, integer
) to service_role;

commit;


