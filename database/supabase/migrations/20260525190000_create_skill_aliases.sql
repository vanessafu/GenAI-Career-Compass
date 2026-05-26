create table if not exists public.skill_aliases (
  alias_key text primary key,
  alias_display text,
  canonical_key text not null,
  canonical_display text not null,
  esco_skill_uri text references public.esco_skills(esco_skill_uri) on delete set null
);

create index if not exists skill_aliases_canonical_key_idx
  on public.skill_aliases (canonical_key);

create index if not exists skill_aliases_esco_skill_uri_idx
  on public.skill_aliases (esco_skill_uri);

do $$
declare
  role_skills_pk_columns text[];
begin
  select array_agg(attribute.attname order by key_order.ordinality)
  into role_skills_pk_columns
  from pg_constraint constraint_info
  join pg_class table_info
    on table_info.oid = constraint_info.conrelid
  join pg_namespace namespace_info
    on namespace_info.oid = table_info.relnamespace
  join unnest(constraint_info.conkey) with ordinality as key_order(attnum, ordinality)
    on true
  join pg_attribute attribute
    on attribute.attrelid = table_info.oid
   and attribute.attnum = key_order.attnum
  where namespace_info.nspname = 'public'
    and table_info.relname = 'role_skills'
    and constraint_info.contype = 'p';

  if role_skills_pk_columns = array['role_id', 'normalized_skill_name'] then
    alter table public.role_skills drop constraint role_skills_pkey;
    alter table public.role_skills
      add constraint role_skills_pkey primary key (role_id, skill_name);
  elsif role_skills_pk_columns is null then
    alter table public.role_skills
      add constraint role_skills_pkey primary key (role_id, skill_name);
  elsif role_skills_pk_columns <> array['role_id', 'skill_name'] then
    raise exception
      'Unexpected role_skills primary key columns: %',
      role_skills_pk_columns;
  end if;
end $$;

alter table public.skill_aliases enable row level security;

revoke all on table public.skill_aliases from anon, authenticated;

grant select, insert, update, delete on table public.skill_aliases to service_role;

drop index if exists public.skill_aliases_source_idx;

alter table public.skill_aliases
  drop column if exists source,
  drop column if exists confidence,
  drop column if exists notes,
  drop column if exists created_at,
  drop column if exists updated_at;
