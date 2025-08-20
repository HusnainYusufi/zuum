-- Address review comments:
-- 1) Safely drop old RPC with potential dependencies using CASCADE
-- 2) Add index on public.shipments.updated_at for sort performance

set statement_timeout = 0;
set lock_timeout = 0;
set idle_in_transaction_session_timeout = 0;
set client_min_messages = warning;

begin;

-- 1) Drop previous signature of search_shipments_simple with CASCADE if it still exists
do $$ begin
  if exists (
    select 1
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'search_shipments_simple'
      and pg_catalog.pg_get_function_identity_arguments(p.oid) = 'text, text, text, text, text, text, text, text, integer, integer'
  ) then
    execute 'drop function public.search_shipments_simple(text, text, text, text, text, text, text, text, integer, integer) cascade';
  end if;
end $$;

-- 2) Index to support ORDER BY updated_at
create index if not exists shipments_updated_at_idx on public.shipments (updated_at desc);

commit;


