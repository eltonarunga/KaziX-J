-- Allow server-side service_role writes without depending on auth.uid().
-- Human admin access remains gated by public.is_admin().

drop policy if exists profiles_admin_all on public.profiles;
create policy profiles_admin_all
  on public.profiles
  for all
  to authenticated
  using (public.is_admin())
  with check (public.is_admin());

drop policy if exists profiles_service_role_all on public.profiles;
create policy profiles_service_role_all
  on public.profiles
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists fundi_profiles_admin_all on public.fundi_profiles;
create policy fundi_profiles_admin_all
  on public.fundi_profiles
  for all
  to authenticated
  using (public.is_admin())
  with check (public.is_admin());

drop policy if exists fundi_profiles_service_role_all on public.fundi_profiles;
create policy fundi_profiles_service_role_all
  on public.fundi_profiles
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists jobs_service_role_all on public.jobs;
create policy jobs_service_role_all
  on public.jobs
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists applications_service_role_all on public.applications;
create policy applications_service_role_all
  on public.applications
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists bookings_service_role_all on public.bookings;
create policy bookings_service_role_all
  on public.bookings
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists transactions_service_role_all on public.transactions;
create policy transactions_service_role_all
  on public.transactions
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists disputes_service_role_all on public.disputes;
create policy disputes_service_role_all
  on public.disputes
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists notifications_service_role_all on public.notifications;
create policy notifications_service_role_all
  on public.notifications
  for all
  to service_role
  using (true)
  with check (true);
