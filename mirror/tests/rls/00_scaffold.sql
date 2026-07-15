-- Faithful reconstruction of the Supabase-provided objects that
-- supabase/migrations/0001_init.sql depends on. Function bodies are copied
-- from Supabase's actual auth/storage schema so RLS evaluates identically to
-- production (PostgREST + Storage API delegate authz to exactly these policies).

-- Roles PostgREST uses. `authenticated`/`anon` are NON-owner, NON-superuser
-- roles, so RLS is enforced against them (superusers/owners bypass RLS).
create role anon nologin noinherit;
create role authenticated nologin noinherit;
create role service_role nologin noinherit bypassrls;

-- ---- auth schema ----------------------------------------------------------
create schema if not exists auth;

create table auth.users (
  id uuid primary key default gen_random_uuid(),
  email text unique
);

-- Supabase's real auth.uid(): reads the JWT `sub` claim that PostgREST sets
-- per-request via `set_config('request.jwt.claims', ...)`.
create or replace function auth.uid()
returns uuid
language sql stable
as $$
  select coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$$;

create or replace function auth.role()
returns text
language sql stable
as $$
  select coalesce(
    nullif(current_setting('request.jwt.claim.role', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role')
  )
$$;

-- ---- storage schema -------------------------------------------------------
create schema if not exists storage;

create table storage.buckets (
  id text primary key,
  name text not null,
  public boolean default false,
  created_at timestamptz default now()
);

create table storage.objects (
  id uuid primary key default gen_random_uuid(),
  bucket_id text references storage.buckets(id),
  name text,
  owner uuid,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  metadata jsonb
);

-- Supabase's real storage.foldername(): splits the object key on '/' and drops
-- the final segment (the filename). For 'uid/session/front.jpg' it returns
-- {uid, session}, so (storage.foldername(name))[1] is the owner id.
create or replace function storage.foldername(name text)
returns text[]
language plpgsql
as $$
declare
  _parts text[];
begin
  select string_to_array(name, '/') into _parts;
  return _parts[1 : array_length(_parts, 1) - 1];
end
$$;

-- In real Supabase, storage.objects ships with RLS ENABLED; the migration only
-- adds policies. Reflect that here so the policies actually gate access.
alter table storage.objects enable row level security;

-- Supabase grants base table privileges to anon/authenticated; RLS then filters
-- rows. Without these grants a denial would be a privilege error, masking
-- whether RLS itself works. Mirror the production grants.
grant usage on schema auth, storage, public to anon, authenticated, service_role;
grant select on auth.users to anon, authenticated, service_role;
grant all on storage.buckets, storage.objects to anon, authenticated, service_role;
alter default privileges in schema public
  grant all on tables to anon, authenticated, service_role;
