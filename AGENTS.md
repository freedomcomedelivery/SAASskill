# Agent instructions

This repository is host-neutral. Read `SKILL.md` and use SAASskill's state machine
instead of inventing your own project stages.

If MCP tools are available, use `project_status → project_plan → provider tools →
project_apply_result → project_advance`.

Provider selection is capability-based:
- web: public/current research;
- Semrush/Ahrefs: SEO/keywords/domain/competitor metrics;
- Ads: real advertising account/performance/write actions;
- analytics/CRM: observed funnel and leads.

A fallback from an SEO provider to web is degraded evidence and must be marked as such.
Never treat a web estimate as an authoritative keyword/traffic metric.

External writes require explicit approval.
