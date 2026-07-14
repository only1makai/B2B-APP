-- Mirror — initial schema, RLS, and private photo storage.
--
-- Design rules (from PRD):
--   * default-deny, owner-only on every table
--   * face photos live in a PRIVATE storage bucket, reachable only via
--     short-TTL signed URLs, RLS-locked to the owner
--   * delete = actually delete (storage objects included; handled app-side)
--
-- All timestamps are stored as timestamptz (UTC). "date" columns are the
-- user's local calendar day for a log entry.

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
create type public.photo_angle as enum ('front', 'left', 'right');
create type public.stack_schedule as enum ('am', 'pm', 'both');

-- ---------------------------------------------------------------------------
-- sessions — one guided three-angle capture session
-- ---------------------------------------------------------------------------
create table public.sessions (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users (id) on delete cascade,
  captured_at   timestamptz not null default now(),
  -- mean luminance (0-255) of the front frame, used to warn about lighting
  -- drift between sessions. Nullable: older/imported sessions may lack it.
  lighting_score numeric,
  notes         text,
  created_at    timestamptz not null default now()
);

create index sessions_user_captured_idx
  on public.sessions (user_id, captured_at desc);

-- ---------------------------------------------------------------------------
-- photos — up to three per session (front / left / right)
-- ---------------------------------------------------------------------------
create table public.photos (
  id           uuid primary key default gen_random_uuid(),
  session_id   uuid not null references public.sessions (id) on delete cascade,
  user_id      uuid not null references auth.users (id) on delete cascade,
  angle        public.photo_angle not null,
  storage_path text not null,
  width        integer,
  height       integer,
  created_at   timestamptz not null default now(),
  unique (session_id, angle)
);

create index photos_user_angle_idx on public.photos (user_id, angle);

-- ---------------------------------------------------------------------------
-- logs — daily entry (target: 15 seconds to fill in)
-- ---------------------------------------------------------------------------
create table public.logs (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references auth.users (id) on delete cascade,
  date           date not null,
  sleep_hours    numeric,
  note           text,
  -- 0 = none, 3 = severe. Kept as small ints, validated app-side and here.
  shine_tzone    smallint check (shine_tzone between 0 and 3),
  shine_cheeks   smallint check (shine_cheeks between 0 and 3),
  breakout_count smallint check (breakout_count >= 0),
  breakout_zones jsonb not null default '[]'::jsonb,
  dryness        smallint check (dryness between 0 and 3),
  irritation     boolean not null default false,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (user_id, date)
);

create index logs_user_date_idx on public.logs (user_id, date desc);

-- ---------------------------------------------------------------------------
-- stack_items — active product list, with start/end dates
-- ---------------------------------------------------------------------------
create table public.stack_items (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users (id) on delete cascade,
  product_name text not null,
  category     text,
  started_at   date not null default (now() at time zone 'utc')::date,
  ended_at     date,
  schedule     public.stack_schedule not null default 'both',
  created_at   timestamptz not null default now()
);

create index stack_items_user_idx on public.stack_items (user_id, started_at desc);

-- ---------------------------------------------------------------------------
-- log_adherence — did you actually apply product X on day Y?
-- ---------------------------------------------------------------------------
create table public.log_adherence (
  log_id        uuid not null references public.logs (id) on delete cascade,
  stack_item_id uuid not null references public.stack_items (id) on delete cascade,
  user_id       uuid not null references auth.users (id) on delete cascade,
  taken         boolean not null default false,
  primary key (log_id, stack_item_id)
);

-- ---------------------------------------------------------------------------
-- updated_at trigger for logs
-- ---------------------------------------------------------------------------
create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger logs_touch_updated_at
  before update on public.logs
  for each row execute function public.touch_updated_at();

-- ===========================================================================
-- Row Level Security — default-deny, owner-only, on every table.
-- ===========================================================================
alter table public.sessions      enable row level security;
alter table public.photos        enable row level security;
alter table public.logs          enable row level security;
alter table public.stack_items   enable row level security;
alter table public.log_adherence enable row level security;

-- sessions
create policy "sessions_select_own" on public.sessions
  for select using (auth.uid() = user_id);
create policy "sessions_insert_own" on public.sessions
  for insert with check (auth.uid() = user_id);
create policy "sessions_update_own" on public.sessions
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "sessions_delete_own" on public.sessions
  for delete using (auth.uid() = user_id);

-- photos
create policy "photos_select_own" on public.photos
  for select using (auth.uid() = user_id);
create policy "photos_insert_own" on public.photos
  for insert with check (auth.uid() = user_id);
create policy "photos_update_own" on public.photos
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "photos_delete_own" on public.photos
  for delete using (auth.uid() = user_id);

-- logs
create policy "logs_select_own" on public.logs
  for select using (auth.uid() = user_id);
create policy "logs_insert_own" on public.logs
  for insert with check (auth.uid() = user_id);
create policy "logs_update_own" on public.logs
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "logs_delete_own" on public.logs
  for delete using (auth.uid() = user_id);

-- stack_items
create policy "stack_select_own" on public.stack_items
  for select using (auth.uid() = user_id);
create policy "stack_insert_own" on public.stack_items
  for insert with check (auth.uid() = user_id);
create policy "stack_update_own" on public.stack_items
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "stack_delete_own" on public.stack_items
  for delete using (auth.uid() = user_id);

-- log_adherence
create policy "adherence_select_own" on public.log_adherence
  for select using (auth.uid() = user_id);
create policy "adherence_insert_own" on public.log_adherence
  for insert with check (auth.uid() = user_id);
create policy "adherence_update_own" on public.log_adherence
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "adherence_delete_own" on public.log_adherence
  for delete using (auth.uid() = user_id);

-- ===========================================================================
-- Storage — private bucket for face photos.
-- Objects are keyed as:  {user_id}/{session_id}/{angle}.jpg
-- so the first path segment is the owner and RLS keys off it.
-- ===========================================================================
insert into storage.buckets (id, name, public)
values ('photos', 'photos', false)
on conflict (id) do nothing;

create policy "photos_bucket_select_own" on storage.objects
  for select using (
    bucket_id = 'photos'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

create policy "photos_bucket_insert_own" on storage.objects
  for insert with check (
    bucket_id = 'photos'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

create policy "photos_bucket_update_own" on storage.objects
  for update using (
    bucket_id = 'photos'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

create policy "photos_bucket_delete_own" on storage.objects
  for delete using (
    bucket_id = 'photos'
    and auth.uid()::text = (storage.foldername(name))[1]
  );
