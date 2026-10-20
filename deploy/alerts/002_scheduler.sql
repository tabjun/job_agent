-- Supabase Cron + Vault: configure the two named Vault secrets through the
-- owner setup flow, never paste their values into this tracked migration.
create extension if not exists pg_cron with schema pg_catalog;
create extension if not exists pg_net with schema extensions;

create or replace function public.invoke_alert_worker() returns bigint
language plpgsql security definer set search_path = '' as $$
declare v_origin text; v_secret text;
begin
  select decrypted_secret into v_origin from vault.decrypted_secrets where name='job_alert_server_origin';
  select decrypted_secret into v_secret from vault.decrypted_secrets where name='job_alert_server_secret';
  if v_origin is null or v_secret is null then raise exception 'scheduler not configured'; end if;
  return net.http_get(url:=v_origin||'/api/alert-worker',
    headers:=jsonb_build_object('Authorization','Bearer '||v_secret),timeout_milliseconds:=290000);
end $$;
revoke all on function public.invoke_alert_worker() from public,anon,authenticated;
grant execute on function public.invoke_alert_worker() to service_role;
select cron.schedule('job-agent-alert-worker','*/5 * * * *','select public.invoke_alert_worker();');
