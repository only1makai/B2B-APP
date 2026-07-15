\set ON_ERROR_STOP off
\pset pager off
\set A '11111111-1111-1111-1111-111111111111'
\set B '22222222-2222-2222-2222-222222222222'
\set SESS 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
\set APATH '11111111-1111-1111-1111-111111111111/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/front.jpg'

-- Seed two auth users (done by the auth service, i.e. superuser).
insert into auth.users(id, email) values (:'A','a@test'), (:'B','b@test');

\echo '=================================================================='
\echo 'SEED: user A creates a session + photo + storage object (as A, RLS)'
\echo '=================================================================='
begin;
  set local role authenticated;
  select set_config('request.jwt.claims', '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}', true);
  insert into public.sessions(id, user_id, notes) values (:'SESS', :'A', 'A private note');
  insert into public.photos(session_id, user_id, angle, storage_path)
    values (:'SESS', :'A', 'front', :'APATH');
  insert into storage.objects(bucket_id, name, owner) values ('photos', :'APATH', :'A');
  select 'A inserted rows OK' as seed_result;
commit;

\echo ''
\echo '### CONTROL: user A can read its OWN session (RLS must NOT over-block)'
begin;
  set local role authenticated;
  select set_config('request.jwt.claims', '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}', true);
  select case when count(*)=1 then 'PASS: A sees its 1 own session' else 'FAIL: A sees '||count(*) end
  from public.sessions;
rollback;

\echo ''
\echo '=================================================================='
\echo 'ATTACK 5(a): user B queries user A''s rows directly'
\echo '=================================================================='
begin;
  set local role authenticated;
  select set_config('request.jwt.claims', '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);

  \echo '-- B: select ALL sessions'
  select case when count(*)=0 then 'PASS: B sees 0 sessions' else 'FAIL: B sees '||count(*) end from public.sessions;
  \echo '-- B: select A''s session by its exact id'
  select case when count(*)=0 then 'PASS: B cannot fetch A''s session by id' else 'FAIL' end
  from public.sessions where id = :'SESS';
  \echo '-- B: select A''s photos (incl. storage_path leak attempt)'
  select case when count(*)=0 then 'PASS: B sees 0 of A''s photos' else 'FAIL: leaked '||count(*) end from public.photos;
  \echo '-- B: UPDATE A''s session (RLS should match 0 rows)'
  with u as (update public.sessions set notes='HACKED' where user_id = :'A' returning 1)
  select case when count(*)=0 then 'PASS: B''s UPDATE hit 0 rows' else 'FAIL: B updated '||count(*) end from u;
  \echo '-- B: DELETE A''s session (RLS should match 0 rows)'
  with d as (delete from public.sessions where user_id = :'A' returning 1)
  select case when count(*)=0 then 'PASS: B''s DELETE hit 0 rows' else 'FAIL: B deleted '||count(*) end from d;
rollback;

\echo ''
\echo '-- B: INSERT a session OWNED BY A (forged user_id) -> expect RLS ERROR:'
begin;
  set local role authenticated;
  select set_config('request.jwt.claims', '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
  insert into public.sessions(user_id, notes) values (:'A', 'forged by B');
rollback;

\echo ''
\echo '=================================================================='
\echo 'ATTACK 5(c): user B targets A''s STORAGE object / path directly'
\echo '=================================================================='
begin;
  set local role authenticated;
  select set_config('request.jwt.claims', '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
  \echo '-- B: select ALL storage objects (this SELECT is what gates signed-URL issuance)'
  select case when count(*)=0 then 'PASS: B sees 0 storage objects' else 'FAIL: B sees '||count(*) end from storage.objects;
  \echo '-- B: fetch A''s object by its exact constructed path'
  select case when count(*)=0 then 'PASS: B cannot resolve A''s object by path' else 'FAIL' end
  from storage.objects where name = :'APATH' and bucket_id='photos';
rollback;

\echo ''
\echo '-- B: WRITE an object into A''s folder (construct path under A''s uid) -> expect RLS ERROR:'
begin;
  set local role authenticated;
  select set_config('request.jwt.claims', '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
  insert into storage.objects(bucket_id, name, owner)
    values ('photos', '11111111-1111-1111-1111-111111111111/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/evil.jpg', :'B');
rollback;

\echo ''
\echo '### CONTROL: user A CAN read its own storage object'
begin;
  set local role authenticated;
  select set_config('request.jwt.claims', '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}', true);
  select case when count(*)=1 then 'PASS: A sees its 1 own object' else 'FAIL: A sees '||count(*) end from storage.objects;
rollback;

\echo ''
\echo '### CONTROL: the anon role (unauthenticated, no JWT) sees nothing'
begin;
  set local role anon;
  select case when count(*)=0 then 'PASS: anon sees 0 sessions' else 'FAIL: anon sees '||count(*) end from public.sessions;
rollback;
