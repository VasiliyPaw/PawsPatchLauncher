-- Accounts foundation. No email addresses or credentials in public profiles.
create schema if not exists paw_private;
revoke all on schema paw_private from public, anon, authenticated;

create function paw_private.nickname_key(value text) returns text
language sql immutable strict set search_path = ''
as $$
 select translate(value,
 'ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ',
 'abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя');
$$;

create function paw_private.nickname_valid(value text) returns boolean
language sql immutable set search_path = ''
as $$
 select value is not null and char_length(value) between 3 and 24
 and value ~ '^[A-Za-zА-Яа-яЁё0-9]'
 and value !~ '[^A-Za-zА-Яа-яЁё0-9_.-]';
$$;

create table public.paw_profiles (
 id uuid primary key references auth.users(id) on delete cascade,
 nickname text not null check (paw_private.nickname_valid(nickname)),
 nickname_key text collate "C" generated always as (paw_private.nickname_key(nickname)) stored,
 created_at timestamptz not null default now(),
 constraint paw_profiles_nickname_unique unique (nickname_key)
);
alter table public.paw_profiles enable row level security;
revoke all on table public.paw_profiles from public, anon, authenticated;
grant select (id, nickname) on public.paw_profiles to authenticated;
create policy paw_profile_self on public.paw_profiles for select to authenticated using ((select auth.uid()) = id);

create function paw_private.create_profile() returns trigger
language plpgsql security definer set search_path = ''
as $$
begin
 if not paw_private.nickname_valid(new.raw_user_meta_data ->> 'nickname') then
   raise exception 'Invalid nickname' using errcode = '23514';
 end if;
 insert into public.paw_profiles(id, nickname) values (new.id, new.raw_user_meta_data ->> 'nickname');
 return new;
end;
$$;
revoke all on all functions in schema paw_private from public, anon, authenticated;

create trigger paw_create_profile after insert on auth.users
for each row execute function paw_private.create_profile();

-- Public registration can ask if an exact nickname is free, never enumerate profiles.
create function public.paw_nickname_available(candidate text) returns boolean
language sql stable security definer set search_path = ''
as $$
 select paw_private.nickname_valid(candidate)
 and not exists (select 1 from public.paw_profiles where nickname_key = paw_private.nickname_key(candidate) collate "C");
$$;
revoke all on function public.paw_nickname_available(text) from public, anon, authenticated;
grant execute on function public.paw_nickname_available(text) to anon, authenticated;

-- Exact nickname lookup for the upcoming friends flow; never return email or arbitrary metadata.
create function public.paw_find_player(candidate text) returns table (id uuid, nickname text)
language sql stable security definer set search_path = ''
as $$
 select p.id, p.nickname from public.paw_profiles p
 where (select auth.uid()) is not null
 and paw_private.nickname_valid(candidate)
 and p.nickname_key = paw_private.nickname_key(candidate) collate "C"
 and exists (select 1 from auth.users u where u.id = p.id and u.email_confirmed_at is not null and u.deleted_at is null)
 limit 1;
$$;
revoke all on function public.paw_find_player(text) from public, anon, authenticated;
grant execute on function public.paw_find_player(text) to authenticated;
