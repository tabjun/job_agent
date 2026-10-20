-- Apply to a dedicated Supabase project. Resume/profile data never enters here.
-- Owner-only operation: users are added in the dashboard (signups off) and
-- alert_save also checks the Vault secret 'job_alert_allowed_emails'.
-- Re-runnable: tables use if-not-exists, policies/functions are replaced.
create table if not exists public.alert_schema (version integer primary key, applied_at timestamptz not null default now());
alter table public.alert_schema enable row level security;
revoke all on public.alert_schema from anon, authenticated;
insert into public.alert_schema(version) values (2) on conflict do nothing;
alter default privileges in schema public revoke execute on functions from public, anon, authenticated;
create table if not exists public.alert_subscriptions (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  email text not null, name text not null check (length(name) between 1 and 60),
  platforms jsonb not null check (jsonb_typeof(platforms) = 'object'),
  schedule jsonb not null check (jsonb_typeof(schedule) = 'object'),
  max_results integer not null check (max_results between 1 and 30),
  enabled boolean not null default true, revision integer not null default 1,
  consent_version text not null default 'job-alerts/v1',
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  last_status text not null default '', last_collection jsonb not null default '{}'
);
alter table public.alert_subscriptions enable row level security;
revoke all on public.alert_subscriptions from anon, authenticated;
grant select on public.alert_subscriptions to authenticated;
drop policy if exists own_alerts on public.alert_subscriptions;
create policy own_alerts on public.alert_subscriptions for select to authenticated
  using (owner_id = (select auth.uid()));

create table if not exists public.alert_deliveries (
  id uuid primary key default gen_random_uuid(),
  subscription_id uuid not null references public.alert_subscriptions(id) on delete cascade,
  slot date not null, revision integer not null,
  state text not null default 'queued', attempts integer not null default 0,
  lease_until timestamptz, payload jsonb, provider_id text, error_code text,
  created_at timestamptz not null default now(), completed_at timestamptz,
  unique (subscription_id, slot)
);
create table if not exists public.alert_sent_urls (
  subscription_id uuid not null references public.alert_subscriptions(id) on delete cascade,
  url text not null, sent_at timestamptz not null default now(), primary key (subscription_id, url)
);
create table if not exists public.alert_code_limits (
  key text primary key, window_start timestamptz not null default now(), count integer not null default 0
);
alter table public.alert_deliveries enable row level security;
alter table public.alert_sent_urls enable row level security;
alter table public.alert_code_limits enable row level security;
revoke all on public.alert_deliveries, public.alert_sent_urls, public.alert_code_limits from anon, authenticated;
grant all on public.alert_subscriptions, public.alert_deliveries, public.alert_sent_urls, public.alert_code_limits to service_role;

drop function if exists public.alert_save(uuid,text,jsonb,jsonb,int,boolean);
create or replace function public.alert_save(p_id uuid, p_name text, p_platforms jsonb,
  p_schedule jsonb, p_limit integer, p_enabled boolean, p_consent_version text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare v_email text; v_allowed text; v_id uuid; v_result jsonb;
begin
  select email into v_email from auth.users where id = auth.uid() and email_confirmed_at is not null;
  if v_email is null then raise exception 'verified identity required'; end if;
  -- Same allowlist as the API (ALERT_ALLOWED_EMAILS), so a direct RPC call
  -- with some other account's JWT cannot create subscriptions either.
  select decrypted_secret into v_allowed from vault.decrypted_secrets where name='job_alert_allowed_emails';
  if v_allowed is null or not lower(v_email) = any(
       select btrim(x) from unnest(string_to_array(lower(v_allowed), ',')) as x) then
    raise exception 'address not allowed';
  end if;
  if p_consent_version is distinct from 'job-alerts/v2' then raise exception 'consent required'; end if;
  perform pg_advisory_xact_lock(410201);
  -- The API validates conditions too; repeat the shape/size checks here.
  if p_platforms is null or jsonb_typeof(p_platforms) <> 'object' or pg_column_size(p_platforms) > 16000
     or exists(select 1 from jsonb_object_keys(p_platforms) k
               where k not in ('catch','jobkorea','saramin','wanted','incruit'))
     or exists(select 1 from jsonb_each(p_platforms) e
               where jsonb_typeof(e.value) <> 'object' or jsonb_typeof(e.value->'role') <> 'string')
     or p_name is null or length(p_name) not between 1 and 60
     or p_schedule is null or jsonb_typeof(p_schedule) <> 'object'
     or not p_schedule ?& array['frequency','hour','weekday']
     or not p_schedule->>'frequency' = any(array['daily','weekdays','weekly'])
     or (p_schedule->>'hour')::int not between 0 and 23
     or (p_schedule->>'weekday')::int not between 0 and 6 then raise exception 'invalid conditions'; end if;
  if p_id is null then
    if (select count(*) from public.alert_subscriptions where owner_id=auth.uid()) >= 3
       or (select count(*) from public.alert_subscriptions) >= 50 then raise exception 'subscription capacity reached'; end if;
    insert into public.alert_subscriptions(owner_id,email,name,platforms,schedule,max_results,enabled,consent_version)
      values(auth.uid(),v_email,p_name,p_platforms,p_schedule,p_limit,p_enabled,p_consent_version) returning id into v_id;
  else
    update public.alert_subscriptions set email=v_email,name=p_name,platforms=p_platforms,
      schedule=p_schedule,max_results=p_limit,enabled=p_enabled,revision=revision+1,updated_at=now()
      where id=p_id and owner_id=auth.uid() returning id into v_id;
    if v_id is null then raise exception 'subscription unavailable'; end if;
  end if;
  select to_jsonb(s) into v_result from public.alert_subscriptions s where id=v_id;
  return v_result;
end $$;

create or replace function public.alert_delete(p_id uuid) returns boolean
language plpgsql security definer set search_path = '' as $$
begin
  if auth.uid() is null then raise exception 'identity required'; end if;
  delete from public.alert_subscriptions where id=p_id and owner_id=auth.uid();
  return true;
end $$;

-- Service-only rate limit; no raw email/IP values are stored in this table.
create or replace function public.alert_reserve_code(p_keys text[]) returns boolean
language plpgsql security definer set search_path = '' as $$
declare k text; v_count int; v_limit int; v_window interval;
begin
  if cardinality(p_keys) not between 1 and 4 then raise exception 'invalid rate keys'; end if;
  perform pg_advisory_xact_lock(410202);
  foreach k in array p_keys loop
    -- Code requests and code checks are limited separately; checks per address
    -- stop guessing a 6-8 digit code even though all visitors share one IP.
    v_limit := case when k like 'minute:%' then 1 when k like 'recipient:%' then 3 when k like 'ip:%' then 10
                    when k like 'verify:%' then 5 when k like 'verifyip:%' then 20 when k = 'verifyglobal' then 60
                    else 30 end;
    v_window := case when k like 'minute:%' then interval '1 minute' else interval '1 hour' end;
    insert into public.alert_code_limits(key) values(k) on conflict do nothing;
    update public.alert_code_limits set count=0,window_start=now() where key=k and window_start < now()-v_window;
    select count into v_count from public.alert_code_limits where key=k;
    if v_count >= v_limit then return false; end if;
  end loop;
  update public.alert_code_limits set count=count+1 where key=any(p_keys);
  delete from public.alert_code_limits where window_start < now()-interval '2 days';
  return true;
end $$;

-- Invoked every five minutes by an authenticated server scheduler. One leased
-- delivery per invocation bounds search work; concurrent invocations skip locks.
create or replace function public.alert_claim() returns jsonb
language plpgsql security definer set search_path = '' as $$
declare v_day date := (now() at time zone 'Asia/Seoul')::date;
  v_hour int := extract(hour from now() at time zone 'Asia/Seoul');
  v_dow int := extract(isodow from now() at time zone 'Asia/Seoul')-1;
  v_id uuid; v_result jsonb;
begin
  if not exists(select 1 from public.alert_code_limits where key='cleanup:'||v_day::text) then
    -- 14 days from creation whatever the state, so stuck/failed rows that
    -- hold an address and mail body do not outlive the stated retention.
    delete from public.alert_deliveries where created_at<now()-interval '14 days';
    delete from public.alert_sent_urls old using (
      select subscription_id,url,row_number() over(partition by subscription_id order by sent_at desc,url) as rank
      from public.alert_sent_urls
    ) ranked where old.subscription_id=ranked.subscription_id and old.url=ranked.url and ranked.rank>1000;
    insert into public.alert_code_limits(key,count) values('cleanup:'||v_day::text,1) on conflict do nothing;
  end if;
  insert into public.alert_deliveries(subscription_id,slot,revision)
    select s.id,v_day,s.revision from public.alert_subscriptions s
    join auth.users u on u.id=s.owner_id and u.email_confirmed_at is not null and u.email=s.email
    where s.enabled and (s.schedule->>'hour')::int <= v_hour and
      ((s.schedule->>'frequency')='daily' or
       ((s.schedule->>'frequency')='weekdays' and v_dow<5) or
       ((s.schedule->>'frequency')='weekly' and (s.schedule->>'weekday')::int=v_dow))
    on conflict (subscription_id,slot) do nothing;
  update public.alert_deliveries set state='unknown',error_code='smtp_outcome_unconfirmed',completed_at=now()
    where state='sending' and payload->>'transport'='smtp' and lease_until<now();
  update public.alert_deliveries set state='failed',error_code='attempts_exhausted',completed_at=now()
    where attempts>=3 and state in ('collecting','prepared','sending') and lease_until<now();
  select d.id into v_id from public.alert_deliveries d
    join public.alert_subscriptions s on s.id=d.subscription_id and s.enabled and s.revision=d.revision
    where d.state in ('queued','collecting','prepared','sending') and d.attempts<3
      and (d.lease_until is null or d.lease_until<now())
      and d.created_at>now()-interval '23 hours'
      and not (d.state='sending' and d.payload->>'transport'='smtp')
    order by d.created_at for update of d skip locked limit 1;
  if v_id is null then return null; end if;
  update public.alert_deliveries set attempts=attempts+1,lease_until=now()+interval '6 minutes',
    -- 'sending' stays visible so the worker resends the stored payload under
    -- the same provider idempotency key instead of re-checking and cancelling.
    state=case when payload is null then 'collecting' when state='sending' then 'sending' else 'prepared' end where id=v_id;
  select jsonb_build_object('delivery',to_jsonb(d),'subscription',to_jsonb(s),
    'sent_urls',coalesce((select jsonb_agg(url) from public.alert_sent_urls where subscription_id=s.id),'[]'))
    into v_result from public.alert_deliveries d join public.alert_subscriptions s on s.id=d.subscription_id where d.id=v_id;
  return v_result;
end $$;

create or replace function public.alert_prepare(p_id uuid,p_payload jsonb) returns boolean
language plpgsql security definer set search_path = '' as $$
begin
  update public.alert_deliveries d set payload=coalesce(d.payload,p_payload),state='prepared'
    from public.alert_subscriptions s where d.id=p_id and d.subscription_id=s.id
      and s.enabled and d.revision=s.revision and d.state in ('collecting','prepared')
      and d.lease_until>now();
  return found;
end $$;

create or replace function public.alert_can_send(p_id uuid) returns boolean
language plpgsql security definer set search_path = '' as $$
begin
  update public.alert_deliveries d set state='sending'
    from public.alert_subscriptions s,auth.users u where d.id=p_id and d.subscription_id=s.id
      and s.owner_id=u.id and s.email=u.email and u.email_confirmed_at is not null
      and s.enabled and d.revision=s.revision and d.payload is not null
      and d.lease_until>now() and d.state='prepared';
  return found;
end $$;

create or replace function public.alert_finish(p_id uuid,p_state text,p_provider_id text,p_error text) returns boolean
language plpgsql security definer set search_path = '' as $$
declare v_job public.alert_deliveries;
begin
  if p_state not in ('sent','empty','retry','unknown','failed','cancelled') then raise exception 'invalid state'; end if;
  select * into v_job from public.alert_deliveries where id=p_id for update;
  if v_job.id is null or v_job.state in ('sent','empty','cancelled') then return false; end if;
  if p_state='sent' then
    insert into public.alert_sent_urls(subscription_id,url)
      select v_job.subscription_id,jsonb_array_elements_text(v_job.payload->'urls') on conflict do nothing;
  end if;
  update public.alert_deliveries set state=case when p_state='retry' and v_job.state='sending' then 'sending'
      when p_state='retry' then 'prepared' else p_state end,
    lease_until=case when p_state='retry' then now()+interval '5 minutes' else null end,
    completed_at=case when p_state='retry' then null else now() end,
    provider_id=p_provider_id,error_code=p_error where id=p_id;
  update public.alert_subscriptions set last_status=p_state,
    last_collection=coalesce(v_job.payload->'collection','{}') where id=v_job.subscription_id;
  return true;
end $$;

create or replace function public.alert_unsubscribe(p_id uuid) returns boolean
language plpgsql security definer set search_path = '' as $$
begin
  update public.alert_subscriptions set enabled=false,revision=revision+1,updated_at=now() where id=p_id;
  return true;
end $$;

revoke all on function public.alert_save(uuid,text,jsonb,jsonb,int,boolean,text), public.alert_delete(uuid) from public, anon;
grant execute on function public.alert_save(uuid,text,jsonb,jsonb,int,boolean,text), public.alert_delete(uuid) to authenticated;
revoke all on function public.alert_reserve_code(text[]),public.alert_claim(),public.alert_prepare(uuid,jsonb),
  public.alert_can_send(uuid),public.alert_finish(uuid,text,text,text),public.alert_unsubscribe(uuid) from public,anon,authenticated;
grant execute on function public.alert_reserve_code(text[]),public.alert_claim(),public.alert_prepare(uuid,jsonb),
  public.alert_can_send(uuid),public.alert_finish(uuid,text,text,text),public.alert_unsubscribe(uuid) to service_role;
