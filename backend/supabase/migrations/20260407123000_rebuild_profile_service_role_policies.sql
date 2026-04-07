-- Re-assert profile write policies so service_role traffic does not depend on
-- auth.uid(), while authenticated users can still manage their own rows.

drop policy if exists profiles_self_insert on public.profiles;
create policy profiles_self_insert
  on public.profiles
  for insert
  to authenticated
  with check (id = auth.uid());

drop policy if exists profiles_self_update on public.profiles;
create policy profiles_self_update
  on public.profiles
  for update
  to authenticated
  using (id = auth.uid())
  with check (id = auth.uid());

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

drop policy if exists fundi_profiles_self_insert on public.fundi_profiles;
create policy fundi_profiles_self_insert
  on public.fundi_profiles
  for insert
  to authenticated
  with check (id = auth.uid());

drop policy if exists fundi_profiles_self_update on public.fundi_profiles;
create policy fundi_profiles_self_update
  on public.fundi_profiles
  for update
  to authenticated
  using (id = auth.uid())
  with check (id = auth.uid());

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
