-- KaziX baseline schema
-- Generated from backend API table usage.

create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  role text not null default 'client' check (role in ('client', 'fundi', 'admin')),
  full_name text not null default 'User',
  phone text not null check (phone ~ '^\\+254[0-9]{9}$'),
  email text,
  county text,
  area text,
  mpesa_number text check (mpesa_number is null or mpesa_number ~ '^\\+254[0-9]{9}$'),
  preferred_language text not null default 'en' check (preferred_language in ('en', 'sw')),
  avatar_url text,
  is_verified boolean not null default false,
  is_suspended boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_profiles_phone unique (phone)
);

create table public.fundi_profiles (
  id uuid primary key references public.profiles (id) on delete cascade,
  trade text not null check (
    trade in (
      'plumber', 'electrician', 'mason', 'mama_fua', 'carpenter',
      'painter', 'roofer', 'gardener', 'driver_mover', 'security', 'other'
    )
  ),
  bio text,
  rate_min integer check (rate_min is null or rate_min >= 0),
  rate_max integer check (rate_max is null or rate_max >= 0),
  experience_years integer check (experience_years is null or (experience_years >= 0 and experience_years <= 60)),
  skills text[] not null default '{}',
  service_radius_km integer not null default 15 check (service_radius_km >= 0),
  rating_avg numeric(3,2) not null default 0.00 check (rating_avg >= 0 and rating_avg <= 5),
  jobs_completed integer not null default 0 check (jobs_completed >= 0),
  is_available boolean not null default true,
  kyc_status text not null default 'pending' check (kyc_status in ('pending', 'approved', 'rejected', 'resubmission_requested')),
  kyc_reviewed_at timestamptz,
  kyc_reviewer_id uuid references public.profiles (id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint ck_fundi_rate_range check (rate_min is null or rate_max is null or rate_max >= rate_min)
);

create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.profiles (id) on delete cascade,
  title text not null check (char_length(title) >= 5 and char_length(title) <= 200),
  description text not null check (char_length(description) >= 20),
  trade text not null check (
    trade in (
      'plumber', 'electrician', 'mason', 'mama_fua', 'carpenter',
      'painter', 'roofer', 'gardener', 'driver_mover', 'security', 'other'
    )
  ),
  county text not null,
  area text not null,
  street text,
  budget_min integer check (budget_min is null or budget_min >= 0),
  budget_max integer check (budget_max is null or budget_max >= 0),
  payment_type text not null default 'negotiable' check (payment_type in ('fixed', 'hourly', 'daily', 'negotiable')),
  urgency text not null default 'flexible' check (urgency in ('flexible', 'urgent')),
  preferred_date date,
  preferred_time text,
  materials_provided boolean not null default false,
  status text not null default 'open' check (status in ('open', 'reviewing', 'active', 'completed', 'cancelled', 'expired')),
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint ck_jobs_budget_range check (budget_min is null or budget_max is null or budget_max >= budget_min)
);

create table public.applications (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs (id) on delete cascade,
  fundi_id uuid not null references public.profiles (id) on delete cascade,
  constraint fk_applications_fundi_profile
    foreign key (fundi_id) references public.fundi_profiles (id) on delete cascade,
  bid_amount integer check (bid_amount is null or bid_amount > 0),
  cover_note text check (cover_note is null or char_length(cover_note) <= 1000),
  status text not null default 'pending' check (status in ('pending', 'shortlisted', 'hired', 'rejected', 'withdrawn')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_application unique (job_id, fundi_id)
);

create table public.bookings (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs (id) on delete restrict,
  application_id uuid not null references public.applications (id) on delete restrict,
  client_id uuid not null references public.profiles (id) on delete restrict,
  fundi_id uuid not null references public.profiles (id) on delete restrict,
  agreed_amount integer not null check (agreed_amount > 0),
  start_date date,
  status text not null default 'confirmed' check (status in ('confirmed', 'in_progress', 'completed', 'cancelled')),
  escrow_status text not null default 'pending' check (escrow_status in ('pending', 'held', 'released', 'refunded', 'failed')),
  mpesa_receipt text,
  escrow_held_at timestamptz,
  escrow_released_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_booking_application unique (application_id)
);

create table public.transactions (
  id uuid primary key default gen_random_uuid(),
  booking_id uuid not null references public.bookings (id) on delete cascade,
  type text not null check (type in ('escrow_in', 'escrow_out', 'refund', 'adjustment')),
  amount integer not null check (amount > 0),
  mpesa_ref text not null,
  from_phone text,
  to_phone text,
  status text not null default 'pending' check (status in ('pending', 'confirmed', 'failed', 'reversed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_transactions_mpesa_ref unique (mpesa_ref)
);

create table public.disputes (
  id uuid primary key default gen_random_uuid(),
  booking_id uuid not null references public.bookings (id) on delete cascade,
  raised_by uuid not null references public.profiles (id) on delete restrict,
  reason text,
  details text,
  status text not null default 'open' check (status in ('open', 'investigating', 'resolved_client', 'resolved_fundi', 'withdrawn')),
  admin_notes text,
  resolved_by uuid references public.profiles (id) on delete set null,
  resolved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  type text not null,
  title text not null,
  body text not null,
  action_url text,
  metadata jsonb not null default '{}'::jsonb,
  read boolean not null default false,
  created_at timestamptz not null default now()
);

create index idx_fundi_profiles_trade on public.fundi_profiles (trade);
create index idx_fundi_profiles_kyc_status on public.fundi_profiles (kyc_status);

create index idx_jobs_status_created_at on public.jobs (status, created_at desc);
create index idx_jobs_trade on public.jobs (trade);
create index idx_jobs_county on public.jobs (county);
create index idx_jobs_client_id on public.jobs (client_id);

create index idx_applications_job_id_created_at on public.applications (job_id, created_at);
create index idx_applications_fundi_id_created_at on public.applications (fundi_id, created_at desc);
create index idx_applications_status on public.applications (status);

create index idx_bookings_client_id_created_at on public.bookings (client_id, created_at desc);
create index idx_bookings_fundi_id_created_at on public.bookings (fundi_id, created_at desc);
create index idx_bookings_job_id on public.bookings (job_id);
create index idx_bookings_status on public.bookings (status);
create index idx_bookings_escrow_status on public.bookings (escrow_status);

create index idx_transactions_booking_id_created_at on public.transactions (booking_id, created_at desc);
create index idx_transactions_status on public.transactions (status);

create index idx_disputes_status_created_at on public.disputes (status, created_at);
create index idx_disputes_booking_id on public.disputes (booking_id);

create index idx_notifications_user_id_read_created_at on public.notifications (user_id, read, created_at desc);

create trigger trg_profiles_set_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

create trigger trg_fundi_profiles_set_updated_at
before update on public.fundi_profiles
for each row execute function public.set_updated_at();

create trigger trg_jobs_set_updated_at
before update on public.jobs
for each row execute function public.set_updated_at();

create trigger trg_applications_set_updated_at
before update on public.applications
for each row execute function public.set_updated_at();

create trigger trg_bookings_set_updated_at
before update on public.bookings
for each row execute function public.set_updated_at();

create trigger trg_transactions_set_updated_at
before update on public.transactions
for each row execute function public.set_updated_at();

create trigger trg_disputes_set_updated_at
before update on public.disputes
for each row execute function public.set_updated_at();
