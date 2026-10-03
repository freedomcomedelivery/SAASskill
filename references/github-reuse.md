# GitHub reuse candidates

Reviewed for v1.5 architecture:

| Need | Repository | Decision |
|---|---|---|
| Google Ads MCP reads | `googleads/google-ads-mcp` | **Reuse/integrate** — first-party Google |
| Google Ads Python | `googleads/google-ads-python` | **Reuse/integrate** — first-party SDK |
| Meta Ads Python | `facebook/facebook-python-business-sdk` | **Reuse/integrate** — first-party SDK |
| Semrush workflows | `semrush/skills` | **Reference/reuse workflows** with official Semrush MCP |
| Semrush MCP self-host | `mrkooblu/semrush-mcp` | Optional fallback only; official Semrush MCP exists |
| Yandex Direct/Metrica MCP | `georgy-agaev/yandex-direct-metrica-mcp` | **Good optional integration target**; read-only public mode is useful |
| Apple Ads old v5 MCP | `AppVisionOS/apple-search-ads-mcp` | Reference only; v5 is legacy |
| Apple Ads Python v1/v5 | `SamPetherbridge/asa-api-client` | **Promising optional client**; community-maintained, pin/audit |
| Camoufox browser | `daijro/camoufox` | **Reuse**; official project warns it is still under development |
| Camoufox crawler pattern | `apify/actor-camoufox-scraper` | **Reference** for queues/extraction architecture |
| Cross-platform Ads MCP | `pipeboard-co/meta-ads-mcp` / Pipeboard family | Optional hosted transport; third-party |

Rule: repository popularity or an MCP badge is not a security audit. Prefer
first-party APIs/SDKs; pin third-party dependencies and keep all write paths behind
SAASskill approval plans.


| Need | Repository / service | Decision |
|---|---|---|
| Analytics / product funnel | PostHog hosted MCP (source in `PostHog/posthog/services/mcp`) | **Official integration target**; old standalone repo is archived |
| CRM | `HubSpot/mcp-server` / official HubSpot remote MCP | **Official integration target** |
| Payments | `stripe/ai` + `stripe/stripe-python` | **Official integration target**; hosted MCP + official Python SDK |
| GA4 | Google Analytics Data API | **Official integration target**; prefer official client |


## Browser backend decision

Two usable Camoufox agent servers were reviewed:
- `jo-inc/camofox-browser`: REST server + standalone MCP adapter, accessibility
  snapshots, stable refs, sessions, screenshots and structured extract.
- `redf0x1/camofox-mcp`: another MCP-oriented Camoufox wrapper with a broad
  automation surface.

SAASskill targets `jo-inc/camofox-browser` for the optional REST backend because
its persistent REST service lets Claude, ChatGPT and custom workers share the same
browser backend without coupling SAASskill to one host's MCP process lifecycle.
The direct `daijro/camoufox` Python integration remains available for simple local
public parsing.

## Ads decision

Google's first-party `googleads/google-ads-mcp` currently exposes account discovery,
metadata and GAQL/search reads. Therefore SAASskill reuses it for read paths and uses
the first-party `googleads/google-ads-python` SDK for custom approved writes.

Meta uses `facebook/facebook-python-business-sdk` for direct reads/writes.
Yandex Direct uses the official API; `georgy-agaev/yandex-direct-metrica-mcp`
remains an attractive optional read-only MCP because it combines Direct, Metrica,
Wordstat and safe two-phase write patterns.
