drop index if exists public.skill_aliases_source_idx;

alter table public.skill_aliases
  drop column if exists source,
  drop column if exists confidence,
  drop column if exists notes,
  drop column if exists created_at,
  drop column if exists updated_at;
