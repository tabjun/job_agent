-- Supabase Cron + Vault: create the named Vault secrets in the dashboard
-- (job_alert_server_origin, job_alert_worker_secret, job_alert_allowed_emails);
-- never paste their values into this tracked migration. Re-runnable.
create extension if not exists pg_cron with schema pg_catalog;
create extension if not exists pg_net with schema extensions;

create or replace function public.invoke_alert_worker() returns bigint
language plpgsql security definer set search_path = '' as $$
declare v_origin text; v_secret text;
begin
  select decrypted_secret into v_origin from vault.decrypted_secrets where name='job_alert_server_origin';
  select decrypted_secret into v_secret from vault.decrypted_secrets where name='job_alert_worker_secret';
  if v_origin is null or v_secret is null then raise exception 'scheduler not configured'; end if;
  return net.http_post(url:=v_origin||'/api/alert-worker', body:='{}'::jsonb,
    headers:=jsonb_build_object('Authorization','Bearer '||v_secret,'Content-Type','application/json'),
    timeout_milliseconds:=290000);
end $$;
revoke all on function public.invoke_alert_worker() from public,anon,authenticated;
grant execute on function public.invoke_alert_worker() to service_role;

-- What the API checks before saying "ready": schema version, an active cron
-- job and the Vault secret names (never their values).
create or replace function public.alert_health() returns jsonb
language plpgsql security definer set search_path = '' as $$
declare v_schema boolean; v_cron boolean; v_vault int; v_last int;
begin
  select exists(select 1 from public.alert_schema where version=2) into v_schema;
  select exists(select 1 from cron.job where jobname='job-agent-alert-worker' and active) into v_cron;
  select count(*) into v_vault from vault.secrets
    where name in ('job_alert_server_origin','job_alert_worker_secret','job_alert_allowed_emails');
  select status_code into v_last from net._http_response order by created desc limit 1;
  return jsonb_build_object('ready', v_schema and v_cron and v_vault=3,
    'schema', v_schema, 'cron', v_cron, 'vault_secrets', v_vault, 'last_worker_status', v_last);
end $$;
revoke all on function public.alert_health() from public,anon,authenticated;
grant execute on function public.alert_health() to service_role;

select cron.unschedule(jobid) from cron.job where jobname='job-agent-alert-worker';
select cron.schedule('job-agent-alert-worker','*/5 * * * *','select public.invoke_alert_worker();');
