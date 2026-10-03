# MCP / multi-host setup

SAASskill v1.3 exposes its control plane as an MCP server. The same project state and
gates can therefore be driven by Claude Code, Claude Platform, OpenAI API/agents, or
another MCP host.

The repository targets the stable MCP Python SDK v2 line (MCP 2026-07-28). Install:

```bash
pip install -e ".[mcp]"
```

## Claude Code — local stdio

Copy `.mcp.json.example` to `.mcp.json`, then restart Claude Code and verify with
`/mcp`. The equivalent CLI approach is to register a project-scoped stdio server.

Claude Code can launch local MCP subprocesses directly, so no network deployment is
required for this mode.

## Remote MCP — Claude Platform / OpenAI

Run the same server over Streamable HTTP:

```bash
SAASSKILL_MCP_TRANSPORT=streamable-http \
SAASSKILL_MCP_HOST=127.0.0.1 \
SAASSKILL_MCP_PORT=8000 \
saasskill-mcp
```

The endpoint is `/mcp`. Put authentication and TLS in front of it before exposing it.
For private/local infrastructure, use the tunnel/private-network mechanism supported by
your host rather than publishing an unauthenticated endpoint.

Both OpenAI and Anthropic support remote MCP connections. ChatGPT UI availability and
write permissions depend on the user's product/plan, so the architecture must not rely
on ChatGPT-only UI features.

## MCP tools exposed by SAASskill

- `provider_matrix`
- `project_init`
- `project_status`
- `project_show`
- `project_plan`
- `project_apply_result`
- `project_advance`
- `project_add_evidence`
- `approval_create`
- `approval_decide`

External Semrush/Ahrefs/Ads tools remain host-side. SAASskill routes to them and stores
their normalized results; it does not require their credentials inside the core runtime.


## Ahrefs external provider

Connect Ahrefs separately from SAASskill. For Claude Code use its official hosted
MCP via OAuth:

```bash
claude mcp add ahrefs https://api.ahrefs.com/mcp/mcp -t http
```

After authentication advertise `ahrefs` in the SAASskill provider list.
