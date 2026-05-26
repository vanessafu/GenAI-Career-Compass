alter table public.role_salaries
  drop column if exists match_confidence,
  drop column if exists confidence;
