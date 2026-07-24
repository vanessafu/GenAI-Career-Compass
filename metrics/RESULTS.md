# Aggregate evaluation results

This is the only checked-in metric output. Timestamped detailed reports and fresh parse JSON are generated under the ignored `metrics/outputs/` directory.

## Role matching

Final local run: 2026-07-24. Fixture: `metrics/fixtures/matching_profiles.json`. Embedding model: `BAAI/bge-base-en-v1.5`. Evaluated catalog: 268 roles with capability and intent embeddings.

| Metric | Result |
| --- | ---: |
| nDCG@9 | 69.3% |
| Precision@3 | 81.5% |
| MRR@9 | 100.0% |
| Bucket accuracy | 42.1% |
| Duplicate normalized titles@9 | 0.00 |
| Unjudged roles@9 | 2.67 |
| Successful profiles | 9/9 |

| Profile | nDCG@9 | P@3 | MRR@9 | Bucket accuracy |
| --- | ---: | ---: | ---: | ---: |
| frontend_student | 67.3% | 66.7% | 100.0% | 16.7% |
| python_data_student | 71.9% | 66.7% | 100.0% | 16.7% |
| it_support_beginner | 47.5% | 100.0% | 100.0% | 80.0% |
| backend_developer | 83.1% | 100.0% | 100.0% | 66.7% |
| design_frontend | 72.5% | 66.7% | 100.0% | 40.0% |
| cloud_security_analyst | 77.5% | 100.0% | 100.0% | 50.0% |
| qa_automation_engineer | 50.7% | 66.7% | 100.0% | 57.1% |
| product_analytics_pm | 87.0% | 100.0% | 100.0% | 25.0% |
| ux_researcher | 66.4% | 66.7% | 100.0% | 37.5% |

The fixed judgment set predates the final three-lens allocator, so newly returned roles remain explicitly unjudged rather than being counted as hidden successes. Bucket accuracy is also reported without artificial score bands or post-hoc relabeling. Extending the labels requires a fresh human review of those roles.

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
