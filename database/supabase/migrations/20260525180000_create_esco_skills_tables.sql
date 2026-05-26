create extension if not exists pgcrypto with schema extensions;

create table if not exists public.esco_skills (
  esco_skill_uri text primary key,
  skill_type text,
  reuse_level text,
  preferred_label text not null,
  alt_labels text,
  hidden_labels text,
  description text,
  scope_note text
);

create table if not exists public.esco_occupation_skills (
  id uuid primary key default gen_random_uuid(),
  esco_uri text not null references public.esco_occupations(esco_uri) on delete cascade,
  esco_skill_uri text not null references public.esco_skills(esco_skill_uri) on delete cascade,
  relation_type text not null default '',
  skill_type text
);

create unique index if not exists esco_occupation_skills_unique_relation_key
  on public.esco_occupation_skills (esco_uri, esco_skill_uri, relation_type);

create index if not exists esco_occupation_skills_esco_uri_idx
  on public.esco_occupation_skills (esco_uri);

create index if not exists esco_occupation_skills_esco_skill_uri_idx
  on public.esco_occupation_skills (esco_skill_uri);

create index if not exists esco_occupation_skills_relation_type_idx
  on public.esco_occupation_skills (relation_type);

create index if not exists esco_skills_preferred_label_idx
  on public.esco_skills (preferred_label);

alter table public.esco_skills enable row level security;
alter table public.esco_occupation_skills enable row level security;

revoke all on table public.esco_skills from anon, authenticated;
revoke all on table public.esco_occupation_skills from anon, authenticated;

grant select, insert, update, delete on table public.esco_skills to service_role;
grant select, insert, update, delete on table public.esco_occupation_skills to service_role;

alter table public.esco_occupation_skills
  drop column if exists raw_data,
  drop column if exists created_at;

alter table public.esco_skills
  drop column if exists concept_type,
  drop column if exists status,
  drop column if exists definition,
  drop column if exists in_scheme,
  drop column if exists raw_data,
  drop column if exists created_at,
  drop column if exists updated_at;
