# Career Compass metrics

Two reproducible metric runners live here. Both write detailed, timestamped artifacts to the ignored `metrics/outputs/` directory. The checked-in aggregate is [RESULTS.md](RESULTS.md).

## Role matching

`run_matching_metrics` evaluates the local deterministic matcher against nine fixed profiles in `fixtures/matching_profiles.json`.

```powershell
$env:HF_HUB_OFFLINE="1"  # optional after BAAI/bge-base-en-v1.5 is cached
uv run python -m metrics.run_matching_metrics
```

The run requires the populated read-only PostgreSQL database but makes no OpenAI calls. Metrics are:

- `nDCG@9`: graded ranking quality over the total default result set.
- `Precision@3`: relevant roles among the first three displayed results.
- `MRR@9`: rank of the first relevant result.
- Bucket accuracy: agreement with reviewed Ready now, Next step, or Aspirational labels.
- Duplicate titles and unjudged roles: quality guardrails.

`top_k=9` is a total limit allocated as three unique roles per normalized lens when eligibility permits: current fit (Ready now), growth fit (Next step), and direction fit (Aspirational). Severe seniority constraints can shift the counts without reducing the total. Scores are comparable within a lens.

## CV parsing

`run_cv_metrics` sends each labeled PDF fixture through every model listed in `settings.json` and scores the structured result against `fixtures/cv_expected.json`.

```powershell
uv run python -m metrics.run_cv_metrics
```

This command consumes OpenAI budget. List fields use set-based F1 so both omissions and inventions reduce the score. Scalar fields are normalized and compared exactly. The current model ladder is:

```json
{
  "cv_models": ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6"]
}
```

Generated summaries, per-model details, and parsed JSON remain ignored. Copy only reviewed aggregate numbers into `RESULTS.md`; never check in absolute paths or raw parsed CV content.

## Tests

```powershell
uv run pytest metrics -q
```
