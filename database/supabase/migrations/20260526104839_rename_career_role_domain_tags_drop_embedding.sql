do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'career_roles'
      and column_name = 'domain_tag'
  ) and not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'career_roles'
      and column_name = 'domain_tags'
  ) then
    alter table public.career_roles rename column domain_tag to domain_tags;
  elsif exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'career_roles'
      and column_name = 'domain_tag'
  ) and exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'career_roles'
      and column_name = 'domain_tags'
  ) then
    execute 'update public.career_roles set domain_tags = coalesce(domain_tags, domain_tag) where domain_tags is null and domain_tag is not null';
    alter table public.career_roles drop column domain_tag;
  end if;
end $$;

drop index if exists public.career_roles_domain_tag_idx;

create index if not exists career_roles_domain_tags_idx
  on public.career_roles (domain_tags);

alter table public.career_roles
  drop column if exists embedding;
