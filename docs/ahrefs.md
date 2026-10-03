# Ahrefs provider setup

SAASskill does **not** require the user's Ahrefs secret. The preferred setup is to
connect Ahrefs' official hosted MCP server directly to each AI host and let
SAASskill receive normalized results.

Official Ahrefs MCP endpoint:

`https://api.ahrefs.com/mcp/mcp`

Ahrefs currently supports MCP/API on Lite and higher plans. API units are shared
between direct API v3, Ahrefs MCP and Ahrefs Connect.

## Claude Code

```bash
claude mcp add ahrefs https://api.ahrefs.com/mcp/mcp -t http
```

Then launch Claude Code, run `/mcp`, authenticate in Ahrefs, select the workspace,
and allow access.

Do **not** commit an Ahrefs MCP/API key to this repository.

## ChatGPT / Claude Web

Prefer the host's OAuth connector flow to the same remote MCP endpoint. Do not paste
credentials into prompts.

## Direct API v3

Use direct API access only for a custom worker/service that really needs
programmatic requests outside an MCP host. API keys are created in Ahrefs Account
settings → API keys and are sent as an Authorization Bearer header.

Only workspace owners/admins can create/manage API keys. Set a per-key monthly unit
limit during development.

## What SAASskill normalizes

`src/saasskill/ahrefs.py` currently normalizes:

- Keywords Explorer matching terms / overview → `seo.keyword_metrics`
- Site Explorer domain rating / metrics → `seo.domain_metrics`
- Organic competitors / pages by traffic / organic keywords →
  `seo.competitor_traffic`
- Paid pages → `seo.competitor_ads`
- All backlinks / referring domains → `seo.backlinks`

The host calls Ahrefs, passes the official response to
`provider_normalize_ahrefs`, and submits the returned ToolResult to
`project_apply_result`.

## Unit discipline

Ahrefs calls consume integration units except endpoints explicitly marked free.
Keep row limits small while a decision is exploratory. Expand only when additional
rows can change a project decision. Aggregates produced by the normalizer are scoped
to the returned row set and request filters.
