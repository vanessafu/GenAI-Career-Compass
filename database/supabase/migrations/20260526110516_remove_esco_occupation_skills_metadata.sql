alter table public.esco_occupation_skills
  drop column if exists raw_data,
  drop column if exists created_at;
