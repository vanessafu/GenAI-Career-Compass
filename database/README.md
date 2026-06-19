# Career Compass

## Repository Hygiene Notes

This repository is a data-preparation snapshot for the Career Compass database.
The scripts under `scripts/` were used to populate and enrich Supabase during the
class-project build. Mutating scripts are marked as one-time database
population/enrichment scripts in their module docstrings, command help, and
`scripts/README.md`.

Use `--dry-run` when rechecking a script. Run the write mode only when rebuilding
or repairing the seeded database, because these scripts use the Supabase service
role key and are not app runtime code.

Generated local artifacts are intentionally not part of the durable repo state:
`__pycache__/`, `.pytest_cache/`, `.idea/`, `data/embedding_cache/`, and
`data/entgeltatlas_cache/` are ignored. Review CSVs and generated seed CSVs under
`data/` are audit artifacts from the import pipeline; keep them only when you
want the review trail for the seeded data.

## Phase 2: Kaggle IT Roles Import

This project contains a local importer for the Kaggle IT job roles CSV and Supabase migrations for the career data schema. The importer validates these table/column names at runtime before a real import:

- `career_roles`: `role_id`, `job_title`, `job_description`, `raw_skills`, `raw_certifications`, `source_row_hash`, `domain_tags`
- `role_skills`: `role_id`, `skill_name`, `normalized_skill_name`
- `certifications`: `certification_id`, `certification_name`, `normalized_certification_name`, `embedding`
- `certifications_mapping`: `role_id`, `certification_id`
- `esco_occupations`: `esco_uri`, `isco_code`, `name`, `definition`
- `esco_mappings`: `role_id`, `esco_uri`, `esco_title`, `match_score`
- `esco_skills`: `esco_skill_uri`, `skill_type`, `reuse_level`, `preferred_label`, `alt_labels`, `hidden_labels`, `description`, `scope_note`
- `role_salaries`: `role_id`, `salary_band`, `salary_score`, `salary_median_monthly_gross_eur`, `region`, `entgeltatlas_match_title`, `needs_review`, `kldb_code`
- `skill_aliases`: `alias_key`, `alias_display`, `canonical_key`, `canonical_display`, `esco_skill_uri`

Schema migrations are stored in `supabase/migrations/`:

- `20260525125658_create_career_compass_core_tables.sql`: base career schema.
- `20260525141422_add_source_row_hash_to_career_roles.sql`: adds importer idempotency for existing databases.
- `20260525143725_add_normalized_certification_name.sql`: adds searchable, dedupable certification names.
- `20260525190000_create_skill_aliases.sql`: adds deterministic skill aliases for Phase 5 and lets `role_skills` preserve duplicate raw skills that collapse to the same normalized skill.
- `20260525200000_create_phase6_esco_mappings.sql`: keeps one primary ESCO mapping per Career Compass role.
- `20260526105827_simplify_esco_mappings_for_static_catalog.sql`: removes review/debug metadata from `esco_mappings` for the static class-project catalog.
- `20260526110516_remove_esco_occupation_skills_metadata.sql`: removes source/audit metadata from `esco_occupation_skills`.
- `20260526111142_simplify_esco_occupations.sql`: renames ESCO occupation titles to `name` and removes static or empty columns from `esco_occupations`.
- `20260526112454_simplify_esco_skills.sql`: removes source/audit metadata from `esco_skills`.
- `20260526113459_simplify_role_salaries_review_fields.sql`: removes low/high salary range and source fields from `role_salaries`, changes the key to `(role_id, region)`, and stores reviewed salary metadata.
- `20260526114217_simplify_skill_aliases.sql`: removes source/audit/review metadata from `skill_aliases`.
- `20260526115000_drop_role_salary_confidence_columns.sql`: removes the unused `match_confidence` and numeric `confidence` columns from `role_salaries`.
- `20260619105941_split_role_certifications.sql`: moves certification names into `certifications` and maps roles through `certifications_mapping`.

The script does not create tables and currently only imports roles, skills, and certifications.

The migration does not add a unique constraint on `career_roles.job_title`, because different roles can share the same display title. The importer keeps idempotency with `career_roles.source_row_hash`, a SHA-256 hash of normalized title, description, raw skills, and raw certifications. Exact duplicate source rows collapse before writing, while same-title variants with different content stay separate.

With the checked-in `IT_Job_Roles_Skills.csv`, a dry run currently reads 493 CSV rows, collapses 7 exact duplicate source rows, and imports 486 source-distinct roles.

Put the Kaggle CSV somewhere local, such as the project root as `IT_Job_Roles_Skills.csv`.

Required environment variables for a real import:

```powershell
$env:SUPABASE_URL="https://your-project-ref.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
```

You can also put those values in a local `.env` file in the project root. `.env` is gitignored. Modern Supabase `sb_secret_...` keys and legacy `service_role` JWT keys are both supported. If you accidentally paste a Supabase dashboard project URL, the importer will convert it to the matching `https://<project-ref>.supabase.co` API URL.

Dry run:

```powershell
python scripts/import_kaggle_roles.py --csv IT_Job_Roles_Skills.csv --dry-run
```

Clean existing role title casing without reimporting:

```powershell
python scripts/import_kaggle_roles.py --normalize-existing-titles
```

Real import:

```powershell
python scripts/import_kaggle_roles.py --csv IT_Job_Roles_Skills.csv
```

Verify in the Supabase SQL editor:

```sql
select count(*) as roles from career_roles;
select count(*) as skills from role_skills;
select count(*) as certifications from certifications;
select count(*) as certification_mappings from certifications_mapping;

select
  count(*) as roles,
  count(source_row_hash) as roles_with_source_row_hash,
  count(distinct source_row_hash) as distinct_source_row_hashes
from career_roles;

select job_title, raw_skills, raw_certifications
from career_roles
order by job_title
limit 10;
```

If the script reports that a table or column cannot be found, confirm that all migrations have been applied, the tables use the expected names, and the tables are exposed through Supabase's Data REST API.

## Phase 3: Deterministic Domain Tags

Phase 3 assigns interest-domain tags to `career_roles.domain_tags` so the frontend can later build Interest Matches. It does not add recommendation scoring, ESCO mapping, salary data, embeddings, or any LLM/API-based tagging.

The local tagger is stored at `scripts/tag_career_roles.py`. It reads `career_roles`, `role_skills`, `certifications`, and `certifications_mapping`, combines each role's title, description, raw skills, raw certifications, normalized skills, and normalized certifications into searchable text, scores tags with deterministic weighted keyword matching, writes review artifacts, and patches only `career_roles.domain_tags` by `role_id`.

Because `career_roles.domain_tags` is a `text` column, roles with multiple tags store them as comma-separated slugs, such as `devops,cloud,infrastructure`. The script assigns up to three tags per role. If no tag reaches the normal score threshold, the script assigns a deterministic fallback tag and marks the row as low confidence for review, so every role gets at least one tag.

Seed taxonomy:

```text
software_engineering, frontend, backend, fullstack, mobile, ux_ui, qa_testing,
devops, cloud, cybersecurity, data_analytics, data_engineering, ai_ml,
database, infrastructure, networking, support, automation_scripting,
architecture, product_management, project_management, management, embedded_iot,
blockchain_web3, game_development
```

New-tag discovery is deterministic and conservative. The script scans current roles for repeated unsupported clusters such as ERP/CRM, technical writing, compliance/risk, observability, GIS/geospatial, animation/graphics, healthcare IT, fintech, AR/VR, robotics, and sales engineering. A discovered tag is applied automatically when at least three roles provide repeated evidence. A small allowlist of major or human-approved domains can apply with single-role evidence; the generated taxonomy records that reason. Weaker evidence is written to the generated taxonomy with `status=needs_review` and is not applied automatically.

Dry run:

```powershell
python scripts/tag_career_roles.py --dry-run
```

Disable new-tag discovery:

```powershell
python scripts/tag_career_roles.py --dry-run --no-discover-new-tags
```

Tag only currently untagged roles:

```powershell
python scripts/tag_career_roles.py --only-untagged --review-output data/domain_tags_review.csv
```

Real update, overwriting existing `domain_tags` values only when explicitly forced:

```powershell
python scripts/tag_career_roles.py --force
```

Manual overrides are optional. Create `data/domain_tags_overrides.csv` with:

```csv
role_id,job_title,domain_tags,notes
123,,cloud,Reviewed manually
,Exact Job Title,erp_crm,business systems role
```

If `role_id` is present it wins; otherwise `job_title` must match exactly. Override tags must be lowercase snake_case. Unknown override tags are added to the generated taxonomy with `source=manual_override`.

Inspect these outputs after every dry run or update:

- `data/domain_tags_review.csv`: role-level assigned tags, confidence, top scores, matched keywords, new tags used, and human-review flags.
- `data/domain_tags_taxonomy.generated.csv`: seed and discovered tags, status, matched role counts, example titles, matched keywords, and reasons.

Refresh these generated CSVs after changing imported role data or normalizing titles:

```powershell
python scripts/tag_career_roles.py --dry-run
```

## Phase 4: Filtered ESCO Occupations Import

Phase 4 imports ICT-related ESCO occupation rows into `esco_occupations` from the raw official English ESCO occupations CSV. It does not add Kaggle-to-ESCO mapping, ESCO skills, ISCO group imports, salaries, embeddings, or recommendation scoring.

Place the raw ESCO occupations file somewhere local, such as `data/raw/esco/occupations_en.csv`. The CSV does not need to be manually filtered first; `scripts/import_esco_occupations.py` filters it internally.

Supported source headers:

- Human-readable ESCO headers: `Concept URI`, `Concept type`, `ISCO code`, `Concept PT`, `Definition`
- Downloaded camelCase headers: `conceptUri`, `conceptType`, `iscoGroup`, `preferredLabel`, `definition`, `description`, `scopeNote`

The importer requires an ESCO URI, name/preferred label, and ISCO code. It keeps only the compact fields the app needs: `esco_uri`, `isco_code`, `name`, and `definition`.

Default ICT filter:

```text
133, 25, 35
```

That includes rows where `ISCO code` or `iscoGroup` starts with one of those prefixes. If a concept type column is present, only `OC` / `Occupation` rows are imported; occupation groups such as `OG` are skipped. If no concept type column exists, the script assumes the file contains occupations and still applies the ISCO filter.

Optional adjacent ICT rows can be included with `--include-adjacent-ict`, which also allows:

```text
2152, 2153, 2166, 2356, 2434, 3114, 742
```

Dry run:

```powershell
python scripts/import_esco_occupations.py --dry-run --csv data/raw/esco/occupations_en.csv
```

With the checked-in raw `occupations_en.csv`, the default dry run reads 3,043 rows and includes 110 ICT occupations.

Write the review CSV to a custom path:

```powershell
python scripts/import_esco_occupations.py --dry-run --review-output data/esco_occupations_import_review.csv --csv data/raw/esco/occupations_en.csv
```

Inspect `data/esco_occupations_import_review.csv` for `source_row_number`, `esco_uri`, `concept_type`, `isco_code`, `name`, `included`, and `skip_reason`.

Real import:

```powershell
python scripts/import_esco_occupations.py --csv data/raw/esco/occupations_en.csv
```

Real import with adjacent ICT rows:

```powershell
python scripts/import_esco_occupations.py --include-adjacent-ict --csv data/raw/esco/occupations_en.csv
```

By default, existing `esco_occupations` rows are reused by `esco_uri`. To refresh fields for existing ESCO URIs, run:

```powershell
python scripts/import_esco_occupations.py --force --csv data/raw/esco/occupations_en.csv
```

Verify in the Supabase SQL editor:

```sql
select count(*) as esco_occupations from esco_occupations;

select isco_code, name, esco_uri
from esco_occupations
order by isco_code, name
limit 20;
```

## Phase 4b: ESCO Skills Linked to Imported Occupations

Phase 4b imports the official ESCO skills that are linked to the ESCO occupations already present in `esco_occupations`. It creates and populates only:

- `esco_skills`
- `esco_occupation_skills`

It does not add Kaggle-to-ESCO role mapping, salary data, embeddings, recommendation scoring, domain-tag changes, or frontend changes. This phase enriches each imported ESCO occupation with official ESCO skill links so a later mapping phase can compare Career Compass roles against ESCO occupation skills.
The `esco_skills` table stores only the compact fields needed for matching and display: URI, skill type, reuse level, preferred/alternate/hidden labels, description, and scope note.

Apply the migration:

- `supabase/migrations/20260525180000_create_esco_skills_tables.sql`

Place the official ESCO files somewhere local, such as:

```text
data/raw/esco/skills_en.csv
data/raw/esco/occupationSkillRelations_en.csv
```

The importer is stored at `scripts/import_esco_skills.py`. It reads existing `esco_occupations.esco_uri` values from Supabase, filters `occupationSkillRelations_en.csv` to those occupations, collects the linked skill URIs, then imports only matching rows from `skills_en.csv`. Relation types are normalized to lowercase and preserved, including `essential` and `optional`.

Dry run:

```powershell
python scripts/import_esco_skills.py `
  --skills-csv data/raw/esco/skills_en.csv `
  --relations-csv data/raw/esco/occupationSkillRelations_en.csv `
  --dry-run
```

Dry runs still require `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, because the script must read the existing `esco_occupations` filter set. Dry runs do not write to Supabase.

Real import:

```powershell
python scripts/import_esco_skills.py `
  --skills-csv data/raw/esco/skills_en.csv `
  --relations-csv data/raw/esco/occupationSkillRelations_en.csv
```

Refresh existing skill and relation metadata from the CSVs:

```powershell
python scripts/import_esco_skills.py `
  --skills-csv data/raw/esco/skills_en.csv `
  --relations-csv data/raw/esco/occupationSkillRelations_en.csv `
  --force
```

Inspect these review outputs after every dry run or import:

- `data/esco_skills_import_review.csv`: every skill row considered, whether it was included, and why skipped.
- `data/esco_missing_skills_review.csv`: linked skill URIs that could not be imported, with relation counts and reasons.
- `data/esco_occupation_skill_relations_review.csv`: relation rows considered, whether they were included, and why skipped.

Custom review paths are supported:

```powershell
python scripts/import_esco_skills.py `
  --skills-csv data/raw/esco/skills_en.csv `
  --relations-csv data/raw/esco/occupationSkillRelations_en.csv `
  --dry-run `
  --review-output data/esco_skills_import_review.csv `
  --missing-skills-output data/esco_missing_skills_review.csv `
  --relations-review-output data/esco_occupation_skill_relations_review.csv
```

Verify in the Supabase SQL editor:

```sql
select count(*) as esco_skills from esco_skills;
select count(*) as esco_occupation_skills from esco_occupation_skills;

select relation_type, count(*) as relation_count
from esco_occupation_skills
group by relation_type
order by relation_type;

select
  o.name,
  s.preferred_label,
  os.relation_type
from esco_occupation_skills os
join esco_occupations o on o.esco_uri = os.esco_uri
join esco_skills s on s.esco_skill_uri = os.esco_skill_uri
order by o.name, os.relation_type, s.preferred_label
limit 20;
```

## Phase 5: Deterministic Skill Normalization

Phase 5 normalizes obvious aliases in `role_skills.normalized_skill_name` so later skill matching, gap analysis, and roadmap generation compare canonical skill names instead of raw spelling variants. It creates and maintains `skill_aliases`, a reusable deterministic alias table for both imported role skills and later user or CV-extracted skills.

This phase does not implement recommendation scoring, interest matching, salary logic, high-earning path scoring, roadmap generation, embeddings, or Kaggle-to-ESCO occupation mapping. Phase 6 can build on the normalized skill keys for matching/gap logic, but Phase 5 only prepares the canonical skill layer.

Apply the migration:

- `supabase/migrations/20260525190000_create_skill_aliases.sql`

The migration creates `skill_aliases` with indexes on `canonical_key` and `esco_skill_uri`. It also changes the `role_skills` primary key to `(role_id, skill_name)` so multiple raw skills in the same role can safely collapse to one `normalized_skill_name` without deleting rows.

Seed aliases live in:

- `data/skill_aliases.seed.csv`

The normalizer is stored at `scripts/normalize_role_skills.py`. It reads `role_skills`, loads seed and existing aliases, applies conservative built-in normalization, optionally exact-matches canonical skill labels against `esco_skills`, upserts missing aliases, and patches only `role_skills.normalized_skill_name`.

ESCO is used only for exact label linking. The script builds a lookup from `esco_skills.preferred_label`, `alt_labels`, and `hidden_labels`. If one exact normalized label matches, `skill_aliases.esco_skill_uri` is stored. If multiple ESCO skills share the same label, the link stays null and the review CSV marks the match as ambiguous. Fuzzy ESCO matching is intentionally skipped here to avoid corrupting later scoring with guessed mappings.

Dry run:

```powershell
python scripts/normalize_role_skills.py --dry-run
```

Real update:

```powershell
python scripts/normalize_role_skills.py
```

Refresh existing `skill_aliases` rows from the current seed/generated aliases:

```powershell
python scripts/normalize_role_skills.py --force
```

Run without ESCO exact linking:

```powershell
python scripts/normalize_role_skills.py --dry-run --no-esco-linking
```

Custom output paths are supported:

```powershell
python scripts/normalize_role_skills.py `
  --dry-run `
  --review-output data/skill_normalization_review.csv `
  --duplicates-output data/skill_normalization_duplicates.csv `
  --seed-aliases data/skill_aliases.seed.csv
```

Inspect these outputs after every dry run or update:

- `data/skill_normalization_review.csv`: raw skill counts, old and new normalized names, alias source/confidence, ESCO exact-link status, generic skill candidates, and notes.
- `data/skill_normalization_duplicates.csv`: same-role raw skills that collapse to one canonical key. The script reports these but does not delete or merge rows.

Verify in the Supabase SQL editor:

```sql
select count(*) as skill_aliases from skill_aliases;
select count(*) as role_skills from role_skills;

select alias_key, canonical_key, esco_skill_uri
from skill_aliases
where alias_key in ('js', 'reactjs', 'gcp', 'ci cd', 'java', 'github actions')
order by alias_key;

select skill_name, normalized_skill_name, count(*) as rows
from role_skills
group by skill_name, normalized_skill_name
order by rows desc, skill_name
limit 20;
```

## Phase 6: ESCO Occupation Grounding

Phase 6 maps each Kaggle/custom `career_roles` row to one primary ESCO occupation in `esco_mappings`. The Career Compass roles remain the user-facing catalog; ESCO is only a background grounding layer for future skill-gap and taxonomy work. This phase does not implement salary logic, recommendations, interest matching, high-earning paths, roadmaps, or frontend UI.

Apply the migration:

- `supabase/migrations/20260525200000_create_phase6_esco_mappings.sql`

Required environment variables:

```powershell
$env:SUPABASE_URL="https://your-project-ref.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
$env:OPENAI_API_KEY="your-openai-api-key"
```

The mapper is stored at `scripts/map_roles_to_esco.py`. It builds role profile text from `career_roles`, `role_skills.normalized_skill_name`, and role certifications resolved through `certifications_mapping`; builds ESCO profile text from `esco_occupations`, `esco_occupation_skills`, and `esco_skills`; generates OpenAI `text-embedding-3-small` embeddings; caches embeddings locally under `data/embedding_cache`; scores semantic similarity plus exact skill overlap and a small domain hint; then writes one compact row per role to `esco_mappings`.

The database table stores only the durable catalog link: `role_id`, `esco_uri`, `esco_title`, and the final `match_score`. Diagnostic details such as semantic score, skill-overlap score, domain-hint score, top candidates, review status, manual override state, and notes stay in `data/esco_role_mapping_review.csv`.

Skill overlap remains exact matching only. It compares normalized role skill labels to ESCO linked skill labels, and also uses Phase 5 `skill_aliases.esco_skill_uri` links when a normalized role skill has an exact ESCO URI link. This improves confidence for skills whose ESCO preferred label is more specific than the class-project canonical skill name, such as `python` versus an ESCO programming-language label.

Dry run:

```powershell
python scripts/map_roles_to_esco.py --dry-run
```

Real mapping:

```powershell
python scripts/map_roles_to_esco.py
```

Useful focused runs:

```powershell
python scripts/map_roles_to_esco.py --limit 20
python scripts/map_roles_to_esco.py --role-id 123
python scripts/map_roles_to_esco.py --force
python scripts/map_roles_to_esco.py --top-k 5
python scripts/map_roles_to_esco.py --cache-dir data/embedding_cache
python scripts/map_roles_to_esco.py --model text-embedding-3-small
```

To verify cache completeness without calling OpenAI:

```powershell
python scripts/map_roles_to_esco.py --dry-run --no-openai-cache-refresh
```

Manual overrides are optional. Edit `data/esco_mapping_overrides.csv` with:

```csv
role_id,job_title,esco_uri,esco_title,notes
123,,http://data.europa.eu/esco/occupation/example,Reviewed ESCO title,Instructor reviewed
,Exact Job Title,http://data.europa.eu/esco/occupation/example,Reviewed ESCO title,Title-level override
```

If `role_id` is present it wins; otherwise `job_title` must match exactly. The script validates every override `esco_uri` against `esco_occupations`; manual override status and notes are recorded in the local review CSV rather than the database.

Inspect `data/esco_role_mapping_review.csv` after every dry run or real mapping. Review rows marked:

- `auto_accepted`: strong score and enough margin over the second candidate.
- `needs_review`: medium score or close competition with the second candidate.
- `low_confidence`: weak top score.
- `manual_override`: selected from `data/esco_mapping_overrides.csv`.

The current Phase 6 status bands are calibrated to this dataset and embedding profile shape:

- `auto_accepted`: top score is at least `0.55` and margin to second is at least `0.05`.
- `needs_review`: top score is at least `0.43`, or a higher-scoring candidate is too close to the second choice.
- `low_confidence`: top score is below `0.43`.

Verify in the Supabase SQL editor:

```sql
select
  r.job_title,
  m.esco_title,
  m.esco_uri,
  m.match_score
from esco_mappings m
join career_roles r on r.role_id = m.role_id
order by m.match_score desc nulls last
limit 20;
```

## Phase 7: German Salary Seed CSV Generation

Phase 7 generates a reviewable German salary seed spreadsheet at:

- `data/german_salary_seed.autogenerated.csv`
- `data/german_salary_seed_review.csv`

This phase reads `career_roles` and `esco_mappings` from Supabase, but it does
not write to Supabase and does not modify `role_salaries`, `career_roles`,
`role_skills`, or `esco_mappings`. Phase 8 should import only an approved,
reviewed CSV.

Entgeltatlas salaries are German occupation-aggregate estimates. They are not
exact salaries for modern individual job titles such as MLOps Engineer, Cloud
Security Specialist, or AI Product Manager. Every generated mapping includes a
`match_confidence` label and `needs_review` flag.

Run without Entgeltatlas API access:

```powershell
python scripts/generate_german_salary_seed.py --no-api
python scripts/generate_german_salary_seed.py --dry-run --no-api
python scripts/generate_german_salary_seed.py --limit 50 --no-api
```

Provide a BA/KldB occupation workbook when available:

```powershell
python scripts/generate_german_salary_seed.py `
  --kldb-xlsx data/raw/ba/berufs_und_taetigkeitsverzeichnis.xlsx `
  --no-api
```

The workbook header detection accepts common title/code headers such as
`Berufsbenennung`, `Bezeichnung`, `Beruf`, `Titel`, `KldB`,
`KldB-Schluessel`, `Systematiknummer`, and `Code`. If no workbook is provided,
the script still emits one row per role, leaves KldB/salary fields empty, and
marks rows for review.

The practical default salary source is the official BA table
`Entgelte nach Berufen im Vergleich`. It provides monthly gross median values by
3-digit KldB Berufsgruppe and Anforderungsniveau columns (`Insgesamt`,
`Helfer`, `Fachkräfte`, `Spezialisten`, `Experten`). The script derives the
salary group from the first three digits of the selected KldB code and derives
the level from the fifth digit when available. If the level-specific value is
missing, it falls back to `Insgesamt` and keeps `needs_review=true`.

Use a cached salary table HTML file:

```powershell
python scripts/generate_german_salary_seed.py `
  --kldb-xlsx data/raw/ba/berufs_und_taetigkeitsverzeichnis.xlsx `
  --salary-table-html data/raw/ba/entgelte_nach_berufen_im_vergleich.html `
  --no-api
```

Fetch and cache the official BA table for local CSV generation:

```powershell
python scripts/generate_german_salary_seed.py `
  --kldb-xlsx data/raw/ba/berufs_und_taetigkeitsverzeichnis.xlsx `
  --fetch-salary-table `
  --no-api
```

You can also pass a specific table URL with `--salary-table-url`. Fetched HTML
is cached under `data/raw/ba` by default. If the table is unavailable or cannot
be parsed, the script continues and marks rows with salary-table source statuses
such as `salary_table_parse_failed`, `salary_group_not_found`,
`salary_missing`, or `no_salary_table_configured`.

Optional Entgeltatlas API enrichment is local data generation only. Configure it
in local `.env` values, never checked-in keys:

```powershell
ENTGELTATLAS_BASE_URL=https://rest.arbeitsagentur.de/infosysbub/entgeltatlas/pc/v1
ENTGELTATLAS_X_API_KEY=your-api-key
ENTGELTATLAS_CLIENT_ID=optional-client-id
ENTGELTATLAS_CLIENT_SECRET=optional-client-secret
```

Then run:

```powershell
python scripts/generate_german_salary_seed.py `
  --kldb-xlsx data/raw/ba/berufs_und_taetigkeitsverzeichnis.xlsx
```

The optional Entgeltatlas config is intentionally read from `.env` only. Shell
environment values for these API fields are ignored to keep local secret usage
explicit and reviewable.

If API configuration is missing or `--no-api` is passed, the script continues in
`no_api_configured` mode. If API calls fail, it continues and marks
`source_status=api_failed`. Responses are cached under
`data/entgeltatlas_cache`.

The API lookup uses the selected KldB code from the KldB match. For 5-digit
codes, the fifth digit is used as the Anforderungsniveau:

```text
1 = Helfer
2 = Fachkraft
3 = Spezialist
4 = Experte
```

The script tries the full 5-digit code first, then a 4-digit fallback, then a
3-digit fallback. When a broader code returns the salary, the generated seed row
fills `salary_lookup_code_used`, `salary_lookup_level_used`, and
`source_status=fallback_group_used`, and keeps `needs_review=true`.

Entgeltatlas capped displays such as `>7.450 Euro` are stored as
`salary_median_monthly_gross_eur=7450`, preserve the original display string in
`salary_median_display`, set `salary_value_capped=true`,
`salary_band=capped`, and `salary_score=5`. Capped values always keep
`needs_review=true`; the source status remains the successful source, such as
`api_success` or `salary_table_success`.

Manual overrides are optional. Create `data/german_salary_overrides.csv` with:

```csv
role_id,job_title,kldb_code,entgeltatlas_match_title,salary_median_monthly_gross_eur,salary_median_display,salary_low_monthly_gross_eur,salary_high_monthly_gross_eur,salary_value_capped,salary_band,salary_score,match_confidence,notes
123,,43412,Softwareentwickler/in,6200,6200,5200,7100,false,high,3,exact_title,Instructor reviewed
```

Override rows match by `role_id` first, then exact `job_title`, and are marked
with `source=manual_override`.

Review `data/german_salary_seed.autogenerated.csv` together with
`data/german_salary_seed_review.csv`. After human review and any manual edits,
save the approved file as:

```text
data/german_salary_seed.csv
```

That approved file is the intended Phase 8 import input.

Optional automated review helper:

```powershell
python scripts/review_german_salary_seed.py
```

This reads `data/german_salary_seed.autogenerated.csv` and
`data/german_salary_seed_sanity_review.csv`, then writes:

- `data/german_salary_seed_review_decisions.csv`
- `data/german_salary_overrides.proposed.csv`

The helper does not modify the seed CSV and does not write to Supabase. It only
proposes deterministic salary-level overrides where the BA salary group is still
plausible, such as lowering junior/entry roles from `Spezialisten` to
`Fachkräfte`, raising senior/manager/architect roles from `Fachkräfte` to
`Experten`, or lowering security analyst/admin rows from `Experten` to
`Spezialisten`. Ambiguous title-to-KldB mappings, especially creative/game/UX
rows and low-confidence matches, are left as manual research decisions instead
of being auto-overridden.

If the proposed overrides are approved, copy or merge the reviewed rows into
`data/german_salary_overrides.csv`, rerun the salary seed generator with
`--manual-overrides data/german_salary_overrides.csv`, and review the generated
seed again before saving the final Phase 8 input as `data/german_salary_seed.csv`.

## Phase 8: Import German Salary Seed

Phase 8 imports the reviewed salary seed into `role_salaries`. The current
database table stores the compact salary fields:

```text
role_id, salary_band, salary_score, salary_median_monthly_gross_eur,
region, entgeltatlas_match_title, needs_review, kldb_code
```

The richer Phase 7 review fields such as `source_status`, KldB group details,
`match_confidence`, numeric match scores, and notes remain in the local review
CSVs.

Dry run:

```powershell
python scripts/import_german_salary_seed.py `
  --dry-run `
  --csv data/german_salary_seed.autogenerated.csv
```

Import/upsert:

```powershell
python scripts/import_german_salary_seed.py `
  --csv data/german_salary_seed.autogenerated.csv
```

The importer validates the live Supabase `role_salaries` schema, stores
`needs_review` and `kldb_code`, and upserts by the primary key
`(role_id, region)`. When `data/german_salary_seed_sanity_review.csv` is
present, `needs_review` is imported from the sanity-review status: only
`acceptable_for_class_project` rows become `false`; all other rows remain
`true`. Re-running the import updates the same rows instead of creating
duplicates.

## Local Verification

Run the automated tests:

```powershell
python -m unittest discover -s tests
```
