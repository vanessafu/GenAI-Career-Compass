# Aggregate evaluation results

This is the only checked-in metric output. Timestamped detailed reports and fresh parse JSON are generated under the ignored `metrics/outputs/` directory.

## Role matching

Final local run: 2026-07-20. Fixture: `metrics/fixtures/matching_profiles.json`. Embedding model: `BAAI/bge-base-en-v1.5`. Evaluated catalog: 268 roles with capability and intent embeddings.

| Metric | Result |
| --- | ---: |
| nDCG@9 | 69.0% |
| Precision@3 | 100.0% |
| MRR@9 | 100.0% |
| Bucket accuracy | 63.0% |
| Duplicate normalized titles@9 | 0.00 |
| Unjudged roles@9 | 0.00 |
| Successful profiles | 9/9 |

| Profile | nDCG@9 | P@3 | MRR@9 | Bucket accuracy |
| --- | ---: | ---: | ---: | ---: |
| frontend_student | 55.4% | 100.0% | 100.0% | 50.0% |
| python_data_student | 77.3% | 100.0% | 100.0% | 44.4% |
| it_support_beginner | 56.2% | 100.0% | 100.0% | 55.6% |
| backend_developer | 92.8% | 100.0% | 100.0% | 66.7% |
| design_frontend | 80.1% | 100.0% | 100.0% | 75.0% |
| cloud_security_analyst | 84.1% | 100.0% | 100.0% | 66.7% |
| qa_automation_engineer | 58.1% | 100.0% | 100.0% | 87.5% |
| product_analytics_pm | 68.8% | 100.0% | 100.0% | 83.3% |
| ux_researcher | 48.5% | 100.0% | 100.0% | 42.9% |

The judgment fixture was reviewed against the current 268-role catalog because the former fixture referenced an older 486-role snapshot. It now covers every role returned by the nine fixed profiles, including explicit relevance-0 judgments for wrong roles. This prevents unjudged results from being treated as hidden successes. Bucket accuracy remains the weakest aggregate and is reported rather than disguised.

Reproduce the deterministic run with a populated read-only database:

```powershell
$env:HF_HUB_OFFLINE="1"  # optional after the model is cached
uv run python -m metrics.run_matching_metrics
```

## CV parsing baseline

The last completed controlled parser comparison was recorded on 2026-06-29 against five hand-reviewed CV fixtures. It predates the final configured 5.6 model ladder and is retained only as a historical baseline; it is not presented as a fresh result for the current models.

| Model used in baseline | Overall field score | Successful parses |
| --- | ---: | ---: |
| `gpt-4o-mini` | 77.0% | 5/5 |
| `gpt-5.4-mini` | 88.7% | 5/5 |
| `gpt-5.5` | 89.7% | 5/5 |

The current comparison ladder in `metrics/settings.json` is `gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6`. A fresh comparison intentionally writes detailed outputs only to the ignored output directory and consumes OpenAI budget:

```powershell
uv run python -m metrics.run_cv_metrics
```

The CV metric uses exact/scalar matching and set-based F1 over labeled contact, experience, education, skills, interests, project, certification, and thesis fields. Raw source text and unlabeled fields are not scored.

## Interpretation limits

- Metrics describe this fixed catalog and these hand-reviewed profiles, not all careers or CV formats.
- Relevance and expected-bucket labels contain human judgment.
- Parser results vary with model versions and service behavior.
- A metric improvement is accepted only with passing tests and qualitative review of returned roles.
