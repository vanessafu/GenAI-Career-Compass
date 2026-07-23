-- Provision the least-privilege Postgres login used by the Career Compass backend.
-- Run as the Supabase project owner. Re-running is safe. This file intentionally
-- contains no password; set the runtime password privately after applying it.

begin;

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'career_compass_reader') then
    create role career_compass_reader nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'career_compass_runtime') then
    create role career_compass_runtime login;
  end if;
end
$$;

alter role career_compass_reader
  nologin;
alter role career_compass_runtime
  login inherit;
alter role career_compass_runtime set default_transaction_read_only = on;

grant career_compass_reader to career_compass_runtime;

revoke all privileges on schema public
  from career_compass_reader, career_compass_runtime;
grant usage on schema public to career_compass_reader;

revoke all privileges on schema extensions
  from career_compass_reader, career_compass_runtime;
grant usage on schema extensions to career_compass_reader;
alter role career_compass_runtime set search_path = public, extensions;

revoke all privileges on all tables in schema public
  from career_compass_reader, career_compass_runtime;

revoke all privileges on table
  public.career_roles,
  public.role_salaries,
  public.esco_mappings,
  public.esco_occupations,
  public.skill_aliases,
  public.role_skills,
  public.certifications_mapping,
  public.certifications,
  public.esco_skills
from public, anon, authenticated;

grant select on table
  public.career_roles,
  public.role_salaries,
  public.esco_mappings,
  public.esco_occupations,
  public.skill_aliases,
  public.role_skills,
  public.certifications_mapping,
  public.certifications,
  public.esco_skills
to career_compass_reader;

do $$
begin
  execute format(
    'grant connect on database %I to career_compass_reader',
    current_database()
  );
end
$$;

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'career_roles',
    'role_salaries',
    'esco_mappings',
    'esco_occupations',
    'skill_aliases',
    'role_skills',
    'certifications_mapping',
    'certifications',
    'esco_skills'
  ]
  loop
    execute format('alter table public.%I enable row level security', table_name);
    execute format(
      'drop policy if exists career_compass_reader_select on public.%I',
      table_name
    );
    execute format(
      'create policy career_compass_reader_select on public.%I for select to career_compass_reader using (true)',
      table_name
    );
  end loop;
end
$$;

commit;
