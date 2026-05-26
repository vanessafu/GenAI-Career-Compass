do $$
begin
  if exists (
    select 1
    from public.esco_mappings
    group by role_id
    having count(*) > 1
  ) then
    raise exception
      'Cannot simplify esco_mappings while duplicate role_id rows exist.';
  end if;
end $$;

alter table public.esco_mappings
  drop constraint if exists esco_mappings_pkey;

drop index if exists public.esco_mappings_role_id_key;
drop index if exists public.esco_mappings_mapping_status_idx;
drop index if exists public.esco_mappings_match_score_idx;

alter table public.esco_mappings
  add constraint esco_mappings_pkey primary key (role_id);

alter table public.esco_mappings
  drop column if exists id,
  drop column if exists semantic_score,
  drop column if exists skill_overlap_score,
  drop column if exists domain_hint_score,
  drop column if exists mapping_method,
  drop column if exists mapping_status,
  drop column if exists top_candidates,
  drop column if exists manual_override,
  drop column if exists notes,
  drop column if exists created_at,
  drop column if exists updated_at;
