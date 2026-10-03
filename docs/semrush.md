# Semrush provider

Preferred connection is Semrush's official hosted MCP:

`https://mcp.semrush.com/v2/mcp`

For Claude Code:

```bash
claude mcp add semrush https://mcp.semrush.com/v2/mcp -t http
```

OAuth is preferred. Direct API v4 keys are also supported by Semrush for custom
workers. Do not put keys in prompts or commit them.

`src/saasskill/semrush.py` accepts either structured MCP/API data or legacy
semicolon-delimited v3 CSV and normalizes common keyword/domain/competitor/paid/
backlink reports into SAASskill evidence.

For new direct integrations prefer Semrush v4. v3 keyword reports are deprecated,
even though existing integrations still work temporarily.
