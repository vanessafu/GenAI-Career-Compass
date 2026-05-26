create table if not exists public.esco_mappings (
  role_id bigint primary key references public.career_roles(role_id) on delete cascade,
  esco_uri text not null references public.esco_occupations(esco_uri) on delete cascade,
  esco_title text,
  match_score numeric
);

alter table public.esco_mappings
  add column if not exists esco_uri text,
  add column if not exists esco_title text,
  add column if not exists match_score numeric;

do $$
begin
  if exists (
    select 1
    from public.esco_mappings
    group by role_id
    having count(*) > 1
  ) then
    raise exception
      'Cannot create primary key on esco_mappings.role_id while duplicate role_id rows exist.';
  end if;
end $$;

alter table public.esco_mappings
  alter column role_id set not null,
  alter column esco_uri set not null,
  alter column match_score type numeric using match_score::numeric;

alter table public.esco_mappings
  drop constraint if exists esco_mappings_pkey;

drop index if exists public.esco_mappings_role_id_key;
drop index if exists public.esco_mappings_mapping_status_idx;
drop index if exists public.esco_mappings_match_score_idx;

alter table public.esco_mappings
  add constraint esco_mappings_pkey primary key (role_id);

alter table public.esco_mappings
  drop column if exists id,
  drop column if exists semantic_score,
  drop column if exists skill_overlap_score,
  drop column if exists domain_hint_score,
  drop column if exists mapping_method,
  drop column if exists mapping_status,
  drop column if exists top_candidates,
  drop column if exists manual_override,
  drop column if exists notes,
  drop column if exists created_at,
  drop column if exists updated_at;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'esco_mappings_role_id_fkey'
      and conrelid = 'public.esco_mappings'::regclass
  ) then
    alter table public.esco_mappings
      add constraint esco_mappings_role_id_fkey
      foreign key (role_id) references public.career_roles(role_id) on delete cascade;
  end if;

  if not exists (
    select 1
    from pg_constraint
    where conname = 'esco_mappings_esco_uri_fkey'
      and conrelid = 'public.esco_mappings'::regclass
  ) then
    alter table public.esco_mappings
      add constraint esco_mappings_esco_uri_fkey
      foreign key (esco_uri) references public.esco_occupations(esco_uri) on delete cascade;
  end if;
end $$;

create index if not exists esco_mappings_esco_uri_idx
  on public.esco_mappings (esco_uri);

alter table public.esco_mappings enable row level security;

revoke all on table public.esco_mappings from anon, authenticated;

grant select, insert, update, delete on table public.esco_mappings to service_role;
