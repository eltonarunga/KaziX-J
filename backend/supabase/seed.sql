-- KaziX seed/bootstrap hooks
-- This file is intentionally idempotent.
-- It only applies if the target profile already exists.

-- Option 1: promote a known bootstrap admin by email (replace before production use).
update public.profiles
set role = 'admin',
    is_verified = true,
    is_suspended = false,
    updated_at = now()
where lower(coalesce(email, '')) = lower('admin@kazix.local');

-- Option 2: promote a known bootstrap admin by phone (replace before production use).
update public.profiles
set role = 'admin',
    is_verified = true,
    is_suspended = false,
    updated_at = now()
where phone = '+254700000001';

-- Optional welcome notification for admins (insert once per admin).
insert into public.notifications (user_id, type, title, body, action_url, metadata, read)
select
  p.id,
  'system',
  'Admin Access Enabled',
  'Your KaziX account now has admin permissions.',
  '/admin-dashboard.html',
  jsonb_build_object('source', 'seed.sql'),
  false
from public.profiles p
where p.role = 'admin'
  and not exists (
    select 1
    from public.notifications n
    where n.user_id = p.id
      and n.type = 'system'
      and n.title = 'Admin Access Enabled'
  );
