-- Étape 1 de la refonte (ticket #10) : première table + règle "chacun ne voit que ses lignes".
-- NON APPLIQUÉE par le dev automatique. À appliquer par le propriétaire (Supabase > SQL Editor),
-- après création du projet Supabase. Migration non destructive (uniquement des créations).
--
-- Annulation (si besoin) :
--   begin; drop table public.profiles; commit;

begin;

create table public.profiles (
  user_id      uuid primary key default auth.uid() references auth.users (id) on delete cascade,
  display_name text,
  created_at   timestamptz not null default now()
);

-- Sécurité par ligne : sans règle explicite, personne ne voit rien.
alter table public.profiles enable row level security;
alter table public.profiles force row level security;

-- Aucun droit pour les visiteurs non connectés ; les connectés passent par les règles ci-dessous.
revoke all on public.profiles from anon;
revoke all on public.profiles from authenticated;
grant select, insert, update on public.profiles to authenticated;

create policy "profiles_select_own" on public.profiles
  for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "profiles_insert_own" on public.profiles
  for insert to authenticated
  with check ((select auth.uid()) = user_id);

create policy "profiles_update_own" on public.profiles
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

commit;
