alter table public.esco_skills
  drop column if exists concept_type,
  drop column if exists status,
  drop column if exists definition,
  drop column if exists in_scheme,
  drop column if exists raw_data,
  drop column if exists created_at,
  drop column if exists updated_at;
