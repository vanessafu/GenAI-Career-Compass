do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'esco_occupations'
      and column_name = 'concept_pt'
  ) and not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'esco_occupations'
      and column_name = 'name'
  ) then
    alter table public.esco_occupations rename column concept_pt to name;
  elsif exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'esco_occupations'
      and column_name = 'concept_pt'
  ) and exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'esco_occupations'
      and column_name = 'name'
  ) then
    update public.esco_occupations
    set name = coalesce(name, concept_pt)
    where name is null
      and concept_pt is not null;

    alter table public.esco_occupations
      drop column concept_pt;
  end if;
end $$;

drop index if exists public.esco_occupations_parent_concept_uri_idx;

alter table public.esco_occupations
  drop column if exists concept_type,
  drop column if exists parent_concept_uri,
  drop column if exists parent_isco_code,
  drop column if exists embedding;
