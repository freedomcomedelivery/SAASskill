# Runtime v1.2

The runtime is deliberately small and deterministic. It does not replace the
research/LLM layer. Its job is to make project state, stage transitions, approvals
and audit history explicit.

## Local start

```bash
python -m pip install -e .
saasskill init "Podcast → Shorts" --project-id podcast-shorts
saasskill status podcast-shorts
saasskill advance podcast-shorts
```

State is stored at `.saasskill/projects/<project_id>/state.json`.

## Fill artifacts

```bash
saasskill set podcast-shorts personal_concept '{"experience":["backend"],"budget":500,"goal":"first revenue"}'
saasskill set podcast-shorts markets '[{"name":"AI video repurposing","definition":"...","players":["A","B","C"],"green_signals":{"many_small_players":true},"evidence_ids":["ev_123"]}]'
```

Add source-backed evidence separately:

```bash
saasskill add-evidence podcast-shorts \
  --kind fact \
  --claim "Three close products sell paid plans" \
  --source-ref "https://example.com"
```

## Gates and work plan

`saasskill gate <project>` evaluates the current stage.
`saasskill plan <project>` turns the current stage/gaps into host work items:
research, artifact creation, metrics reads, approval requests or external actions.

`advance` moves only on `pass`. An override requires both `--force` and
`--reason`; the override is persisted in `stage_history` and `action_log`.

## External side effects

Adapters are interfaces, not implicit permissions. Research and metrics can be read
autonomously. `ActionAdapter.execute()` requires an approval whose status is
`approved`.

```bash
saasskill approval podcast-shorts create \
  --action-type launch_campaign \
  --target "Google Ads / campaign draft 7" \
  --summary "Launch search test" \
  --max-spend 350 --currency USD --duration "14 days" \
  --rollback "Pause if spend reaches cap or tracking breaks"

saasskill approval podcast-shorts approve --id apr_xxxxx
```

## Adapter boundary

`src/saasskill/adapters.py` defines:

- `ResearchAdapter`: source-backed public/connected research.
- `MetricsAdapter`: observed funnel data.
- `ActionAdapter`: prepare and execute side effects.
- `AdapterRegistry`: host-supplied adapter bundle.

Provider-specific connectors should live behind these contracts rather than inside
the stage controller.

## Important

The runtime treats course thresholds as methodology, not current platform facts.
Platform-specific execution must still apply
`policies/current-platform-verification.md` before a real launch.
