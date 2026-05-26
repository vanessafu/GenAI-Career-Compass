alter table if exists public.career_roles
  add column if not exists source_row_hash text;

create unique index if not exists career_roles_source_row_hash_key
  on public.career_roles (source_row_hash)
  where source_row_hash is not null;
