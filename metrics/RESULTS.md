# Aggregate evaluation results

This is the only checked-in metric output. Timestamped detailed reports and fresh parse JSON are generated under the ignored `metrics/outputs/` directory.

## Role matching

Final local run: 2026-07-24. Fixture: `metrics/fixtures/matching_profiles.json`. Embedding model: `BAAI/bge-base-en-v1.5`. Evaluated catalog: 268 roles with capability and intent embeddings.

| Metric | Result |
| --- | ---: |
| nDCG@9 | 69.8% |
| Precision@3 | 92.6% |
| MRR@9 | 100.0% |
| Bucket accuracy | 51.7% |
| Duplicate normalized titles@9 | 0.00 |
| Unjudged roles@9 | 2.33 |
| Successful profiles | 9/9 |

| Profile | nDCG@9 | P@3 | MRR@9 | Bucket accuracy |
| --- | ---: | ---: | ---: | ---: |
| frontend_student | 60.8% | 100.0% | 100.0% | 33.3% |
| python_data_student | 77.4% | 66.7% | 100.0% | 42.9% |
| it_support_beginner | 52.4% | 100.0% | 100.0% | 50.0% |
| backend_developer | 85.0% | 100.0% | 100.0% | 57.1% |
| design_frontend | 81.4% | 100.0% | 100.0% | 50.0% |
| cloud_security_analyst | 82.0% | 100.0% | 100.0% | 66.7% |
| qa_automation_engineer | 49.6% | 66.7% | 100.0% | 42.9% |
| product_analytics_pm | 64.9% | 100.0% | 100.0% | 85.7% |
| ux_researcher | 74.6% | 100.0% | 100.0% | 37.5% |

The fixed judgment set predates the final three-lens/MMR selector, so newly returned roles remain explicitly unjudged rather than being counted as hidden successes. Bucket accuracy is also reported without artificial score bands or post-hoc relabeling. Extending the labels requires a fresh human review of those roles.

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
