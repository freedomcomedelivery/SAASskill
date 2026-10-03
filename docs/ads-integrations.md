# Ads normalization and execution

## Normalized providers
- `google_ads`: GAQL/Google Ads API metrics; converts `cost_micros`.
- `meta_ads`: Marketing API Insights; interprets lead/purchase action arrays.
- `yandex_direct`: Direct Reports TSV/JSON.
- `apple_ads`: Apple Ads Platform API report-like payloads.
- `pipeboard`/generic `ads`: supported as transports, but platform raw payloads
  should still be normalized with the concrete platform normalizer when possible.

Normalized fields:
`impressions, reach, clicks, spend, conversions, leads, purchases, revenue`.
Derived fields:
`CTR, CPC, CPM, conversion_rate, CPA, ROAS`.

## Writes
Writes are two-step:

1. `ads_prepare_execution` stores an exact execution plan.
2. Create an approval bound to that `plan_id`.
3. `ads_dispatch_execution(... apply=false)` is a dry run.
4. `ads_dispatch_execution(... apply=true)` returns the exact provider dispatch
   only when approval is approved, plan-bound, currency-compatible and within cap.
5. Host/provider performs the real call.
6. `ads_complete_execution` stores the provider result.

This keeps credentials in provider transports and spend authority in SAASskill.
