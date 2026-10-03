# Pre-key integration checklist

Everything in this file can be reviewed before any real provider credentials are
added.

## Works without secrets

- repository/schema/link validation;
- Python compile/unit tests;
- provider capability routing;
- construction of Ahrefs/Semrush/GA4/PostHog/Metrica/HubSpot/Stripe request specs;
- direct-provider **dry runs**;
- Google/Meta/Yandex/Apple Ads read-request dry runs;
- execution-plan digest/approval/spend-cap tests;
- ads write-dispatch dry runs;
- Ahrefs/Semrush/Ads/analytics/CRM/payment normalizer fixtures;
- static public HTML parser fixtures;
- camofox-browser REST adapter tests with a mocked server;
- existing-project audit/growth-plan tests.

## Needs a local service, but no SaaS API secret

### camofox-browser

Run the reviewed `jo-inc/camofox-browser` backend locally and point:

```bash
export CAMOFOX_BASE_URL=http://127.0.0.1:9377
```

For a locally ungated server, public read/snapshot testing needs no SaaS key.
If `CAMOFOX_ACCESS_KEY` is enabled on the browser server, expose the same value
to SAASskill.

SAASskill's adapter intentionally uses only create-tab/snapshot/close-tab. It does
not expose cookie import, login automation, click/type workflows, challenge solving
or proxy rotation.

## Needs credentials/OAuth for live read tests

- Ahrefs: OAuth MCP or `AHREFS_API_KEY`;
- Semrush: OAuth MCP or `SEMRUSH_API_KEY`;
- Google Ads: developer token + OAuth/ADC configuration;
- Meta Ads: app id/secret + access token;
- Yandex Direct/Metrica: OAuth token (+ counter id for Metrica);
- Apple Ads: Platform API OAuth access token / client material;
- GA4: Application Default Credentials + property id;
- PostHog: personal API key + project id;
- HubSpot: OAuth/MCP or private-app access token;
- Stripe: MCP/OAuth or restricted/test API key.

Use test/read-only credentials first where the provider supports them.

## Needs explicit approval plus credentials

Live advertising mutations. The built-in direct write transport intentionally
supports only a small pre-debug set:
- Google Ads campaign status;
- Meta Ads campaign ACTIVE/PAUSED status;
- Yandex Direct campaign suspend/resume.

All complex campaign creation/budget/targeting mutations remain execution-plan
payloads for host/MCP execution until provider test-account fixtures have been
validated.

## Debug order

1. `integration_check` — confirm the adapter sees dependencies/credential groups.
2. Build the request/dry-run.
3. Execute a read against a test or low-risk account.
4. Compare raw provider payload to normalizer fixtures.
5. Run one full `project_tick → pending request → execute/ingest → gate` loop.
6. Only then test a plan-bound advertising write.
