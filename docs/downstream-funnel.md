# Analytics, CRM and verified payments

SAASskill keeps downstream evidence separate:

1. **Analytics** — visits/events and funnel behavior.
2. **CRM** — leads, qualification and deal/customer lifecycle.
3. **Payments** — successful payment-processor records.

An ad-platform conversion or CRM lifecycle value is never silently promoted to a
verified payment.

## Preferred integrations

- PostHog: official hosted MCP at `https://mcp.posthog.com/mcp`.
- GA4: official Google Analytics Data API.
- Yandex Metrica: official API or the reviewed Direct+Metrica MCP.
- HubSpot: official remote MCP at `https://mcp.hubspot.com`.
- Stripe: official remote MCP at `https://mcp.stripe.com` or official
  `stripe-python` SDK.

## Runtime normalizers

- `analytics.py`: PostHog, GA4, Yandex Metrica and generic funnel rows.
- `crm.py`: HubSpot/generic lead and deal-stage records.
- `payments.py`: Stripe/generic successful transaction records.

In an existing-project audit, verified payment count takes precedence over weaker
ad-platform/CRM payment proxies when commercial readiness is calculated.
