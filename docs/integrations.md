# Integration layer v1.5

SAASskill prefers official provider surfaces when they exist. Community projects are
used as implementation references or optional transports, not as implicit trust
anchors.

## Semrush
Preferred: official Semrush MCP at `https://mcp.semrush.com/v2/mcp`.
SAASskill normalizes official MCP/API data; it does not need a private Semrush MCP.
Version 4 is preferred for new direct API work. Keep API-unit usage explicit.

## Google Ads
Preferred read path: Google's official `googleads/google-ads-mcp` for GAQL/search.
Preferred custom write path: Google's official `google-ads` Python SDK.
All writes still pass through SAASskill execution plans and exact plan-bound approval.

## Meta Ads
Preferred custom transport: Meta's official `facebook/facebook-python-business-sdk`.
A third-party remote MCP such as Pipeboard can be used when convenient, but is an
optional transport and should not replace SAASskill's approval boundary.

## Yandex Direct
The official API v5/v501 remains the source of truth for reports and campaign
operations. `georgy-agaev/yandex-direct-metrica-mcp` is a useful optional MCP
because it combines Direct, Metrica and Wordstat and exposes a read-only mode plus
two-phase write patterns.

## Apple Ads
New work targets the official Apple Ads Platform API v1 at `api.ads.apple.com/v1`.
Do not build new integration code around legacy Campaign Management API v5.
`SamPetherbridge/asa-api-client` is a useful community Python client because it
already supports Platform API v1; audit/pin before production use.

## Camoufox
Use the official `daijro/camoufox` package for JS-heavy public pages. The
`apify/actor-camoufox-scraper` project is a useful reference for crawling queues
and page-function architecture.

SAASskill's Camoufox layer intentionally excludes login automation, CAPTCHA solving,
challenge bypass, proxy rotation and authenticated session import.


## One-call result ingestion

Hosts should prefer `project_ingest_ahrefs`, `project_ingest_semrush`,
`project_ingest_ads` and `project_ingest_public_page` over manually chaining
normalizer + `project_apply_result`. These tools resolve the pending request first,
derive expected provider/capability/context, normalize the payload and apply evidence
in one call.

Tool results may also use `state_merge_patch` for deterministic nested facts such
as parsed landing surface or observed ad metrics; protected roots remain enforced.


## Downstream funnel

See [analytics, CRM and payments](downstream-funnel.md). Payment processor evidence
is kept distinct from ad conversions and CRM lifecycle labels.
