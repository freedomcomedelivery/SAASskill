# Provider routing

SAASskill does not depend on a vendor-specific tool name. Work items request a
logical capability and the host selects an available provider.

## Default routing

| Capability | First choice | Fallback |
|---|---|---|
| `web.search` | web | none |
| `web.fetch` | web | none |
| `seo.keyword_metrics` | Semrush → Ahrefs | web search (degraded) |
| `seo.domain_metrics` | Ahrefs → Semrush | web search (degraded) |
| `seo.competitor_traffic` | Semrush → Ahrefs | web search (degraded) |
| `seo.backlinks` | Ahrefs | web search (degraded) |
| `seo.competitor_ads` | Semrush | web search (degraded) |
| `ads.performance.read` | Ads | no inferred fallback |
| `ads.campaigns.write` | Ads | no fallback; approval required |
| `analytics.funnel.read` | analytics | Ads performance when appropriate |
| `crm.leads.read` | CRM | analytics funnel when appropriate |

Semrush and Ahrefs are therefore complementary, not hard dependencies. A project can
run with either one; when both are connected the router picks the provider best suited
to the requested capability. Preferences can override the defaults per host/project.

## Result quality

A degraded route is never silently promoted to authoritative data. For example, public
web pages can show that a market has demand or active advertisers, but they do not
replace provider-reported search volume, traffic or backlink metrics.

## Host execution

`project_plan` returns concrete tool requests with:
- requested capability;
- effective capability;
- provider;
- degraded flag;
- side-effect / approval flag;
- stage context.

The host (Claude, ChatGPT, another MCP client, or a custom worker) executes the external
tool and submits a normalized result through `project_apply_result`.
