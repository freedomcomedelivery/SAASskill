# Contributing

## Rule of change
Every methodological rule must be classified as one of:
- `course_heuristic`
- `current_platform_fact`
- `evidence_based_project_fact`
- `user_constraint`

Do not silently promote a heuristic into a fact.

## Before merge
Run:

```bash
python scripts/validate_repo.py
python scripts/run_evals.py
```

When changing a gate, validator, action boundary, or channel playbook, add or update an eval case.

## Platform-specific procedures
UI paths, ad-platform settings, moderation rules, targeting options and API behavior age quickly. Mark them as requiring current verification instead of baking them into durable methodology.
