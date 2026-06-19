# Data Sources and Processing Summary

For Career Compass, our goal was to combine practical IT role data with more official occupation and salary sources. The user-facing roles mainly come from an IT job-role dataset, but we ground those roles in ESCO, KldB, and German salary statistics so the system is not just based on a random list of job titles.

## 1. Role, skill, and certification data

The fine-grained roles shown to the user come from the Kaggle IT Job Roles Skills Dataset. This dataset contains 493 IT job roles with job descriptions, required skills, and recommended certifications. This is not an official government or EU source, but it is useful because it includes modern IT roles that are more specific than broad taxonomies like ESCO.

We imported the Kaggle data into our own tables:

```
Job Title        -> career_roles.job_title
Job Description  -> career_roles.job_description
Skills           -> role_skills
Certifications   -> certifications
Role/cert links  -> certifications_mapping
```

We then cleaned the skills and certifications deterministically. For example, we split comma-separated skill lists into individual rows, trimmed whitespace, removed duplicates, and normalized obvious aliases like:

```
JS -> JavaScript
K8s -> Kubernetes
React.js -> React
Amazon Web Services -> AWS
CI CD -> CI/CD
```

This means the Kaggle dataset gives us the practical role/skill/certification layer, but we do not treat it as an official source.

## 2. Domain tags for interest matching

We also added our own `domain_tags` layer to make the recommendation system better at handling user interests. The Kaggle dataset gives us role titles, descriptions, skills, and certifications, but it does not give each role a clean product-facing category like `cloud`, `frontend`, `cybersecurity`, or `data_analytics`. Since the frontend needs to show “interest matches,” we needed a simple way to connect user interests to groups of roles.

These domain tags are derived metadata, not original source data. The role text still comes from the Kaggle/custom role data, while the tags are added by our own pipeline.

We generated the tags mostly through deterministic keyword and rule-based matching. For example, roles mentioning React, Vue, HTML, CSS, or frontend development can be tagged as `frontend`, while roles mentioning AWS, Azure, Docker, Kubernetes, CI/CD, or Terraform can be tagged as `cloud`, `devops`, or `infrastructure`. We started with a controlled list of tags, then allowed the script to propose additional tags when it found repeated role clusters that were not covered well by the original list.

This is not an official classification like ESCO. ESCO is still the official occupation and skill taxonomy layer, and it is used for standardized occupation grounding and skill matching. The domain tags are more practical and product-oriented: they help group roles in a way that feels natural in the app.

For transparency, the domain tags should be treated as a deterministic enrichment step. They were generated from the imported role titles, descriptions, and skills, then stored in `career_roles.domain_tags`. This makes it possible to match a user interest like “AI,” “cloud,” “security,” or “design” to relevant roles, even if the user’s current skill overlap with those roles is not the highest. So this layer supports the app’s “Interest Matches” section, while the actual role details still come from the Kaggle/custom role data and the official grounding still comes from ESCO.

## 3. ESCO data

We use ESCO as the official European grounding layer. ESCO is maintained by the European Commission and is meant to classify occupations, skills, competences, and qualifications relevant to the European labor market and education/training systems. It is also designed so software systems can use the relationships between occupations and skills for matching and career guidance.

From ESCO, we imported:

```
occupations_en.csv
skills_en.csv
occupationSkillRelations_en.csv
```

These files became:

```
esco_occupations
esco_skills
esco_occupation_skills
```

ESCO itself does not drive the main role recommendations. The frontend still shows our fine-grained Kaggle/custom roles. ESCO is used to connect those roles to official occupation categories and official skill context. This helps make the system more defensible than only using the Kaggle dataset.

## 4. Mapping our roles to ESCO

Each Kaggle/custom role is mapped to one primary ESCO occupation. To do this, we build a text profile for both sides.

For a Kaggle/custom role, we use:

```
job title
job description
domain tags
normalized skills
certifications
```

For an ESCO occupation, we use:

```
ESCO occupation title
ESCO definition
linked ESCO essential/optional skills
```

Then we use OpenAI embeddings to compare the role profile with the ESCO occupation profile. Embeddings are used here for semantic similarity, not as a source of facts. OpenAI describes embeddings as numerical text representations that can be used for tasks like search, recommendation, classification, and measuring relatedness between text.

So the mapping is best understood as:

```
Fine-grained role: DevOps Engineer
Official grounding: closest ESCO ICT occupation
```

This does not mean ESCO officially confirms every Kaggle role title. It means we connect each modern role to the closest official ESCO occupation category and store the mapping score/review status.

## 5. German occupation mapping with KldB

For German salary data, we use the KldB 2010, revised 2020 classification from the Bundesagentur für Arbeit. The revised KldB 2010 has been used in labor-market statistics from the 2021 reporting year onward.

The KldB workbook is used to map role titles to German occupation codes. This is necessary because German salary statistics are organized by German occupational classifications, not by arbitrary English job titles like “MLOps Engineer” or “Cloud Security Specialist.”

The pipeline is roughly:

```
Career role
-> likely German KldB occupation
-> KldB code
-> salary group / requirement level
```

This step is partly automated through deterministic matching and fuzzy matching, but the results are still reviewable.

## 6. German salary data

Salary values come from official German Bundesagentur für Arbeit salary statistics, not from Kaggle and not from an LLM. In the current pipeline, the practical salary source is the official BA table **"Entgelte nach Berufen im Vergleich"**. We did not depend on live Entgeltatlas API access for the final seed. The optional Entgeltatlas API lookup was implemented as a best-effort enrichment path, but the imported salaries were filled from the BA salary table.

The BA table reports median gross monthly salaries for full-time employees subject to social security contributions, grouped by German occupational category and requirement level. The table provides salary values by:

```
Berufsgruppe
Insgesamt
Helfer
Fachkräfte
Spezialisten
Experten
```

To connect our modern English IT roles to those salary values, we first map each role to a likely KldB occupation code. Then we derive:

```
salary group        -> first 3 digits of the KldB code
requirement level   -> 5th digit of the KldB code
```

The requirement-level mapping is:

```
1 -> Helfer
2 -> Fachkräfte
3 -> Spezialisten
4 -> Experten
```

For example, a role mapped to a KldB code beginning with `434` uses the BA salary group for software development/programming. If the fifth digit indicates `3`, the script uses the `Spezialisten` salary column for that group.

This is important because our salary estimates are not exact salaries for every modern IT role. They are better described as:

German salary estimates based on related BA/KldB occupation groups and requirement levels

The generated salary seed CSV includes review metadata such as:

```
salary_median_monthly_gross_eur
salary_band
salary_score
salary_group_code
salary_source_group_title
salary_selected_column
match_confidence
source_status
needs_review
notes
```

However, the current database table `role_salaries` is narrower. It stores only:

```
role_id
kldb_code
salary_band
salary_score
salary_median_monthly_gross_eur
region
entgeltatlas_match_title
needs_review
```

This means the richer review metadata, such as `source_status`, KldB group details, `match_confidence`, numeric fuzzy-match scores, and notes, remains in the local review CSVs rather than in the current `role_salaries` table.

For Phase 8, we imported all generated salary rows into `role_salaries` with:

```
region = Deutschland
```

We also store a simple `needs_review` flag in `role_salaries`. This flag comes from the sanity-review pass: rows marked `acceptable_for_class_project` are imported as `needs_review = false`, while rows that need manual review, manual overrides, or extra research remain `needs_review = true`.

The `salary_score` is a simple band score derived from the monthly gross salary value:

```
unknown   -> 0
low       -> 1
medium    -> 2
high      -> 3
very_high -> 4
capped    -> 5
```

This score is useful for displaying or sorting broad salary bands, but it should not be presented as an exact salary prediction or as a fully implemented recommendation/high-earning-path model.

## 7. What was cleaned deterministically

Most of the data processing was deterministic and reproducible. This includes:

- importing CSV files
- splitting skill and certification strings
- trimming whitespace
- removing duplicates
- normalizing obvious skill aliases
- assigning domain tags with keyword/rule-based logic
- mapping roles to KldB candidates
- deriving salary group and requirement level from KldB codes
- parsing the official BA salary table columns
- computing salary bands from numeric salary values

We intentionally kept these steps script-based so that the pipeline can be rerun and explained.

## 8. Where LLMs or AI models were used

LLMs were used as tooling, not as the source of truth.

We used AI/Codex to help write scripts and structure the pipeline. We also use embeddings for semantic matching between our custom role profiles and ESCO occupation profiles. Later, an LLM may parse uploaded CVs into structured skills and generate natural-language explanations for the user.

However, we do not use an LLM to invent:

- job roles
- required skills
- certifications
- salary values
- official occupation categories

The actual job-role facts come from the Kaggle dataset, the official occupation grounding comes from ESCO/KldB, and the salary values come from official German salary statistics.

## 9. Trust and limitations

The most trustworthy parts of the database are the official sources:

```
ESCO      -> official European occupation/skill taxonomy
KldB      -> official German occupation classification
BA salary -> official German salary statistics
```

The Kaggle dataset is useful but unofficial. We use it because it gives us modern IT role granularity, but we ground it in ESCO and KldB to make it more defensible. The domain tags are also unofficial, but they are deterministic derived metadata rather than a separate factual source.

The biggest limitation is salary precision. German salary data is based on occupation groups/aggregates, not exact modern job titles. In addition, the current `role_salaries` table stores the compact salary fields but not the full review metadata from the generated CSVs. So the salary values should be shown as estimates or bands, not as exact role-specific salaries.

## Short version

Our database combines an unofficial but useful IT role dataset with official European and German labor-market classifications. Kaggle provides the concrete roles, skills, and certifications. We added our own deterministic domain tags so the app can group roles for interest-based matching. ESCO provides official European occupation and skill grounding. KldB connects roles to German occupation codes. The official BA salary table provides German salary estimates at occupational-group and requirement-level granularity. Most cleaning is deterministic, while AI is only used for scripting support, semantic mapping, CV parsing, and explanation generation.
