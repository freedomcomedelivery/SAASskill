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
