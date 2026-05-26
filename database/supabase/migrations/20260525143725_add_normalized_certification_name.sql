create or replace function pg_temp.normalize_certification_name_for_migration(value text)
returns text
language sql
immutable
as $$
  select lower(
    btrim(
      regexp_replace(
        regexp_replace(
          regexp_replace(
            regexp_replace(
              replace(
                replace(
                  replace(
                    replace(
                      regexp_replace(btrim(coalesce(value, '')), '\s+', ' ', 'g'),
                      U&'\00e2\20ac\201c',
                      '-'
                    ),
                    U&'\00e2\20ac\0093',
                    '-'
                  ),
                  U&'\00e2\20ac\201d',
                  '-'
                ),
                U&'\00e2\20ac\0094',
                '-'
              ),
              U&'[\2010-\2015\2212]',
              '-',
              'g'
            ),
            '\s*-\s*',
            ' - ',
            'g'
          ),
          '\s*:\s*',
          ': ',
          'g'
        ),
        '\s+',
        ' ',
        'g'
      )
    )
  );
$$;

alter table if exists public.role_certifications
  add column if not exists normalized_certification_name text;

update public.role_certifications
set normalized_certification_name = pg_temp.normalize_certification_name_for_migration(certification_name)
where normalized_certification_name is null;

with duplicate_certifications as (
  select
    ctid,
    row_number() over (
      partition by role_id, normalized_certification_name
      order by certification_name
    ) as duplicate_rank
  from public.role_certifications
)
delete from public.role_certifications as role_certification
using duplicate_certifications
where role_certification.ctid = duplicate_certifications.ctid
  and duplicate_certifications.duplicate_rank > 1;

alter table if exists public.role_certifications
  alter column normalized_certification_name set not null;

create unique index if not exists role_certifications_role_normalized_certification_name_key
  on public.role_certifications (role_id, normalized_certification_name);

create index if not exists role_certifications_normalized_certification_name_idx
  on public.role_certifications (normalized_certification_name);
