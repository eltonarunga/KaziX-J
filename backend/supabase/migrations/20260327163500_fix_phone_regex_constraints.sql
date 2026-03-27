-- Fix profiles phone/mpesa regex constraints to accept +254XXXXXXXXX

alter table public.profiles
  drop constraint if exists profiles_phone_check;

alter table public.profiles
  add constraint profiles_phone_check
  check (phone ~ '^\+254[0-9]{9}$');

alter table public.profiles
  drop constraint if exists profiles_mpesa_number_check;

alter table public.profiles
  add constraint profiles_mpesa_number_check
  check (mpesa_number is null or mpesa_number ~ '^\+254[0-9]{9}$');
