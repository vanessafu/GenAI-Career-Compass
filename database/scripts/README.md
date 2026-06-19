# Scripts

These scripts were created for the one-time Career Compass database population
and review pipeline. They are kept for auditability and controlled reruns while
rebuilding or repairing the seeded Supabase database; they are not application
runtime code.

Always prefer `--dry-run` first. Write modes require trusted local/server
credentials, usually `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, and must not
be run from frontend/client code.

## One-Time Database Population And Enrichment

- `import_kaggle_roles.py`: imports the Kaggle role catalog into `career_roles`,
  `role_skills`, `certifications`, and `certifications_mapping`.
- `tag_career_roles.py`: writes deterministic domain tags to
  `career_roles.domain_tags`.
- `import_esco_occupations.py`: imports filtered ICT ESCO occupations into
  `esco_occupations`.
- `import_esco_skills.py`: imports ESCO skills and occupation-skill relations
  linked to the imported occupations.
- `normalize_role_skills.py`: writes canonical skill names and the
  `skill_aliases` lookup table.
- `map_roles_to_esco.py`: writes one primary ESCO mapping per role to
  `esco_mappings`.
- `import_german_salary_seed.py`: imports the reviewed salary seed into
  `role_salaries`.

## Local Preparation And Review Helpers

- `generate_german_salary_seed.py`: reads role/mapping data and local BA/KldB
  sources to generate reviewable salary seed CSVs; it does not write salary rows
  to Supabase.
- `review_german_salary_seed.py`: classifies generated salary rows and writes
  proposed local review/override CSVs; it never touches Supabase.

## Generated Artifacts

- `data/*_review.csv`, `data/*.generated.csv`, and `data/*.proposed.csv` are
  review/audit outputs from this pipeline.
- `data/embedding_cache/` and `data/entgeltatlas_cache/` are local caches and
  should stay ignored.
- Python bytecode directories such as `scripts/__pycache__/` and
  `tests/__pycache__/` are disposable.
