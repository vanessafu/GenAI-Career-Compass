alter table public.role_salaries
  add column if not exists needs_review boolean not null default false,
  add column if not exists match_confidence text,
  add column if not exists kldb_code text;

do $$
begin
  if exists (
    select 1
    from pg_constraint
    where conrelid = 'public.role_salaries'::regclass
      and conname = 'role_salaries_pkey'
      and pg_get_constraintdef(oid) = 'PRIMARY KEY (role_id, region, source)'
  ) then
    alter table public.role_salaries
      drop constraint role_salaries_pkey;

    alter table public.role_salaries
      add constraint role_salaries_pkey primary key (role_id, region);
  end if;
end $$;

alter table public.role_salaries
  drop column if exists salary_low_monthly_gross_eur,
  drop column if exists salary_high_monthly_gross_eur,
  drop column if exists source;
