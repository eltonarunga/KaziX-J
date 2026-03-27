-- KaziX row-level security policies

create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.profiles p
    where p.id = auth.uid()
      and p.role = 'admin'
      and coalesce(p.is_suspended, false) = false
  );
$$;

revoke all on function public.is_admin() from public;
grant execute on function public.is_admin() to anon, authenticated, service_role;

alter table public.profiles enable row level security;
alter table public.fundi_profiles enable row level security;
alter table public.jobs enable row level security;
alter table public.applications enable row level security;
alter table public.bookings enable row level security;
alter table public.transactions enable row level security;
alter table public.disputes enable row level security;
alter table public.notifications enable row level security;

-- Profiles
create policy profiles_public_read
  on public.profiles
  for select
  to anon, authenticated
  using (true);

create policy profiles_self_insert
  on public.profiles
  for insert
  to authenticated
  with check (id = auth.uid());

create policy profiles_self_update
  on public.profiles
  for update
  to authenticated
  using (id = auth.uid())
  with check (id = auth.uid());

create policy profiles_admin_all
  on public.profiles
  for all
  to authenticated
  using (public.is_admin())
  with check (public.is_admin());

-- Fundi profiles
create policy fundi_profiles_public_read
  on public.fundi_profiles
  for select
  to anon, authenticated
  using (true);

create policy fundi_profiles_self_insert
  on public.fundi_profiles
  for insert
  to authenticated
  with check (id = auth.uid());

create policy fundi_profiles_self_update
  on public.fundi_profiles
  for update
  to authenticated
  using (id = auth.uid())
  with check (id = auth.uid());

create policy fundi_profiles_admin_all
  on public.fundi_profiles
  for all
  to authenticated
  using (public.is_admin())
  with check (public.is_admin());

-- Jobs
create policy jobs_public_read
  on public.jobs
  for select
  to anon, authenticated
  using (
    status in ('open', 'reviewing', 'active', 'completed')
    or client_id = auth.uid()
    or public.is_admin()
  );

create policy jobs_owner_insert
  on public.jobs
  for insert
  to authenticated
  with check (client_id = auth.uid() or public.is_admin());

create policy jobs_owner_update
  on public.jobs
  for update
  to authenticated
  using (client_id = auth.uid() or public.is_admin())
  with check (client_id = auth.uid() or public.is_admin());

create policy jobs_owner_delete
  on public.jobs
  for delete
  to authenticated
  using (client_id = auth.uid() or public.is_admin());

-- Applications
create policy applications_participant_read
  on public.applications
  for select
  to authenticated
  using (
    fundi_id = auth.uid()
    or public.is_admin()
    or exists (
      select 1
      from public.jobs j
      where j.id = applications.job_id
        and j.client_id = auth.uid()
    )
  );

create policy applications_fundi_insert
  on public.applications
  for insert
  to authenticated
  with check (fundi_id = auth.uid() or public.is_admin());

create policy applications_participant_update
  on public.applications
  for update
  to authenticated
  using (
    fundi_id = auth.uid()
    or public.is_admin()
    or exists (
      select 1
      from public.jobs j
      where j.id = applications.job_id
        and j.client_id = auth.uid()
    )
  )
  with check (
    fundi_id = auth.uid()
    or public.is_admin()
    or exists (
      select 1
      from public.jobs j
      where j.id = applications.job_id
        and j.client_id = auth.uid()
    )
  );

-- Bookings
create policy bookings_participant_read
  on public.bookings
  for select
  to authenticated
  using (
    client_id = auth.uid()
    or fundi_id = auth.uid()
    or public.is_admin()
  );

create policy bookings_participant_update
  on public.bookings
  for update
  to authenticated
  using (
    client_id = auth.uid()
    or fundi_id = auth.uid()
    or public.is_admin()
  )
  with check (
    client_id = auth.uid()
    or fundi_id = auth.uid()
    or public.is_admin()
  );

create policy bookings_owner_insert
  on public.bookings
  for insert
  to authenticated
  with check (client_id = auth.uid() or public.is_admin());

-- Transactions
create policy transactions_participant_read
  on public.transactions
  for select
  to authenticated
  using (
    public.is_admin()
    or exists (
      select 1
      from public.bookings b
      where b.id = transactions.booking_id
        and (b.client_id = auth.uid() or b.fundi_id = auth.uid())
    )
  );

create policy transactions_admin_write
  on public.transactions
  for all
  to authenticated
  using (public.is_admin())
  with check (public.is_admin());

-- Disputes
create policy disputes_participant_read
  on public.disputes
  for select
  to authenticated
  using (
    raised_by = auth.uid()
    or public.is_admin()
    or exists (
      select 1
      from public.bookings b
      where b.id = disputes.booking_id
        and (b.client_id = auth.uid() or b.fundi_id = auth.uid())
    )
  );

create policy disputes_participant_insert
  on public.disputes
  for insert
  to authenticated
  with check (
    public.is_admin()
    or (
      raised_by = auth.uid()
      and exists (
        select 1
        from public.bookings b
        where b.id = disputes.booking_id
          and (b.client_id = auth.uid() or b.fundi_id = auth.uid())
      )
    )
  );

create policy disputes_owner_or_admin_update
  on public.disputes
  for update
  to authenticated
  using (raised_by = auth.uid() or public.is_admin())
  with check (raised_by = auth.uid() or public.is_admin());

-- Notifications
create policy notifications_owner_read
  on public.notifications
  for select
  to authenticated
  using (user_id = auth.uid() or public.is_admin());

create policy notifications_owner_update
  on public.notifications
  for update
  to authenticated
  using (user_id = auth.uid() or public.is_admin())
  with check (user_id = auth.uid() or public.is_admin());

create policy notifications_owner_insert
  on public.notifications
  for insert
  to authenticated
  with check (user_id = auth.uid() or public.is_admin());
