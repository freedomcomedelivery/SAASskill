# Claude Code instructions

Read `SKILL.md` before operating a project.

When the SAASskill MCP server is configured:
1. Call `project_status`.
2. Call `project_plan` with the providers actually connected in this Claude session.
3. Execute only the returned routed research/metrics requests with available tools.
4. Return results through `project_apply_result`, preserving source URLs/refs and whether a fallback was degraded.
5. Call `project_advance` only after the current gate passes.
6. Never execute spend/publish/message/write actions without an `approved` approval.

Preferred research providers are capability-based, not mandatory:
- web for current public facts and reviews;
- Semrush or Ahrefs for SEO/keyword/domain/competitor metrics;
- Ads for actual account/campaign/performance data and approved campaign writes.

Do not invent provider data when a requested capability is unresolved.
