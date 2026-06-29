# CareerCompass Metrics

Run each metric separately from the repo root:

```powershell
uv run python -m metrics.run_cv_metrics
uv run python -m metrics.run_matching_metrics
```

Both commands write timestamped Markdown reports to `metrics/outputs/`, for example:

```text
metrics/outputs/cv_metrics_summary_20260629_143000.md
metrics/outputs/cv_metrics_detail_gpt-4o-mini_20260629_143000.md
metrics/outputs/matching_metrics_20260629_143012.md
```

## CV Parsing Accuracy

`run_cv_metrics` parses every CV fresh with three OpenAI models, compares each parsed result against hand-reviewed expected fields in `metrics/fixtures/cv_expected.json`, and writes one comparison report.

Use this metric to compare parser changes, prompt changes, and model choices against the same CV set. The headline score is the average field score across all labeled fields. List fields use set-based F1, so extra invented items and missed expected items both lower the score. Scalar fields score as matched or not matched after normalization.

The expected fields intentionally mirror the `CVData` schema used by the app:

- Contact/profile fields: name, email, phone, location, current role, links, years of experience.
- Experience fields: roles, organisations, locations, dates, responsibilities, and contextual skills.
- Education fields: entry types, degree/qualification text, institutions, dates, grades, thesis titles, and courses.
- Skills fields: technical skills, soft skills, languages, and interests.
- Project/certification fields: project titles, descriptions, dates, technologies, true outcomes, links, certifications, issue dates, thesis titles, and thesis technologies.

The metric does not score raw source text, parser confidence, `unmapped_information`, or fields that are not present in a fixture. Project descriptions and project outcomes are scored separately because the parser schema and downstream matching code use them as separate signals.

For slides, show the model comparison table from the summary report. Use one sentence for interpretation: the best parser is the model with the highest average score on the fixed CV fixtures. If space allows, add the weakest field groups because they explain what still needs work better than a single average.

Set the three model levels in `metrics/settings.json`:

```json
{
  "cv_models": [
    "gpt-4o-mini",
    "gpt-5.4-mini",
    "gpt-5.5"
  ]
}
```

Then run:

```powershell
uv run python -m metrics.run_cv_metrics
```

Each run writes:

- a short comparison summary: `metrics/outputs/cv_metrics_summary_<timestamp>.md`
- one detailed report per model: `metrics/outputs/cv_metrics_detail_<model>_<timestamp>.md`
- fresh parsed JSON for every model/CV pair: `metrics/outputs/cv_parses_<timestamp>/<model>/<cv>.json`

Edit `metrics/settings.json` whenever you want to change the model ladder.

## Role Matching Quality

`run_matching_metrics` runs the existing local matcher for the fixed profiles in `metrics/fixtures/matching_profiles.json` and scores the top 9 returned roles against hand-labeled judged roles.

Use this metric to compare matching-code changes against the same profile set and role catalog. The fixture labels each judged role with relevance `0` to `3`: `0` means wrong, `1` means adjacent, `2` means good, and `3` means ideal. Duplicate normalized titles get no extra relevance after the first occurrence, so repeated role families do not inflate the score.

The matching fixtures should stay grounded in the Supabase `career_roles` catalog. The current set covers frontend, data, support, backend, design/front-end, cloud security, QA automation, product analytics, and UX research profiles.

The main metrics are:

`@k` means the metric only looks at the top `k` returned roles. For this project, `@9` covers the full default result set: 3 `ready_now`, 3 `next_step`, and 3 `aspirational` roles. `@3` covers the first three roles users see first.

- `nDCG@9`: the headline ranking score. It rewards ideal roles near the top of the nine returned roles.
- `Precision@3`: whether the first three roles are at least adjacent.
- `MRR@9`: whether the first relevant role appears early.
- `Bucket accuracy`: whether relevant judged roles are placed in the expected `ready_now`, `next_step`, or `aspirational` bucket.
- `Duplicate titles@9`: average repeated normalized titles in the top nine roles.
- `Unjudged roles@9`: average returned roles that are not covered by the fixture labels.

For slides, show `nDCG@9` and `Bucket accuracy` as the two decision metrics. `Precision@3` and `MRR@9` are smoke checks once they reach 100%. Use `Duplicate titles@9` as a quality guardrail. Include one example profile when explaining the score, such as backend matching if architect roles rank above Java developer roles.

## Checked-In Outputs

Current output reports are kept in `metrics/outputs/` so teammates can inspect the latest metric run without rerunning model calls or the live matcher. Generate new outputs only when the fixture, model settings, prompts, parser, matcher, or role catalog changes.
