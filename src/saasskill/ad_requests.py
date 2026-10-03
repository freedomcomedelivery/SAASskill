from __future__ import annotations

from typing import Any


def build_ads_read_request(
    *,
    provider: str,
    capability: str,
    account_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
    level: str = "campaign",
) -> dict[str, Any]:
    """Build a credential-free provider call specification for host execution."""
    if capability not in {"ads.accounts.read", "ads.campaigns.read", "ads.performance.read"}:
        raise ValueError(f"Unsupported read capability: {capability}")

    if provider == "google_ads":
        if capability == "ads.accounts.read":
            return {"provider": provider, "tool": "list_accessible_customers", "arguments": {}}
        if capability == "ads.campaigns.read":
            query = (
                "SELECT campaign.id, campaign.name, campaign.status, "
                "campaign.advertising_channel_type, campaign_budget.amount_micros "
                "FROM campaign ORDER BY campaign.id"
            )
        else:
            if not date_from or not date_to:
                raise ValueError("Google Ads performance request requires date_from/date_to")
            query = (
                "SELECT campaign.id, campaign.name, campaign.status, metrics.impressions, "
                "metrics.clicks, metrics.cost_micros, metrics.conversions, metrics.conversions_value "
                f"FROM campaign WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'"
            )
        return {
            "provider": provider,
            "tool": "search",
            "arguments": {"customer_id": account_id, "query": query},
        }

    if provider == "meta_ads":
        if capability == "ads.accounts.read":
            return {"provider": provider, "sdk": "facebook-business", "operation": "User.get_ad_accounts", "arguments": {}}
        if capability == "ads.campaigns.read":
            return {
                "provider": provider,
                "sdk": "facebook-business",
                "operation": "AdAccount.get_campaigns",
                "arguments": {
                    "account_id": account_id,
                    "fields": ["id", "name", "status", "effective_status", "objective", "daily_budget", "lifetime_budget"],
                },
            }
        if not date_from or not date_to:
            raise ValueError("Meta Ads performance request requires date_from/date_to")
        return {
            "provider": provider,
            "sdk": "facebook-business",
            "operation": "AdAccount.get_insights",
            "arguments": {
                "account_id": account_id,
                "level": level,
                "time_range": {"since": date_from, "until": date_to},
                "fields": [
                    "campaign_id", "campaign_name", "impressions", "reach", "clicks",
                    "inline_link_clicks", "spend", "actions", "action_values",
                ],
            },
        }

    if provider == "yandex_direct":
        if capability == "ads.accounts.read":
            return {
                "provider": provider,
                "api": "Yandex Direct v5",
                "service": "Clients",
                "method": "get",
                "arguments": {"FieldNames": ["Login", "ClientInfo", "Currency"]},
            }
        if capability == "ads.campaigns.read":
            return {
                "provider": provider,
                "api": "Yandex Direct v5",
                "service": "Campaigns",
                "method": "get",
                "arguments": {
                    "SelectionCriteria": {},
                    "FieldNames": ["Id", "Name", "Status", "State", "Type", "DailyBudget"],
                },
            }
        if not date_from or not date_to:
            raise ValueError("Yandex Direct performance request requires date_from/date_to")
        return {
            "provider": provider,
            "api": "Yandex Direct Reports v501",
            "endpoint": "https://api.direct.yandex.com/json/v501/reports",
            "arguments": {
                "params": {
                    "SelectionCriteria": {"DateFrom": date_from, "DateTo": date_to},
                    "FieldNames": ["CampaignId", "CampaignName", "Impressions", "Clicks", "Cost", "Conversions"],
                    "ReportName": "saasskill-performance",
                    "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
                    "DateRangeType": "CUSTOM_DATE",
                    "Format": "TSV",
                    "IncludeVAT": "NO",
                    "IncludeDiscount": "NO",
                }
            },
        }

    if provider == "apple_ads":
        if capability == "ads.accounts.read":
            return {
                "provider": provider,
                "api": "Apple Ads Platform API v1",
                "method": "GET",
                "endpoint": "https://api.ads.apple.com/v1/acls",
                "headers": {},
            }
        if capability == "ads.campaigns.read":
            return {
                "provider": provider,
                "api": "Apple Ads Platform API v1",
                "method": "POST",
                "endpoint": "https://api.ads.apple.com/v1/campaigns/query",
                "headers": {"X-AP-Context": f"adAccountId={account_id}"},
                "body": {},
            }
        if not date_from or not date_to:
            raise ValueError("Apple Ads performance request requires date_from/date_to")
        return {
            "provider": provider,
            "api": "Apple Ads Platform API v1",
            "method": "POST",
            "endpoint": "https://api.ads.apple.com/v1/reports/apps/campaigns/query",
            "headers": {"X-AP-Context": f"adAccountId={account_id}"},
            "body": {
                "timeRange": {"startTime": date_from, "endTime": date_to},
                "granularity": "DAILY",
            },
        }

    if provider == "pipeboard":
        return {
            "provider": provider,
            "transport": "Pipeboard MCP",
            "capability": capability,
            "account_id": account_id,
            "date_from": date_from,
            "date_to": date_to,
            "level": level,
            "note": "Resolve the concrete Pipeboard platform tool from tools/list before execution.",
        }

    if provider == "ads":
        return {
            "provider": provider,
            "transport": "host ads connector",
            "capability": capability,
            "account_id": account_id,
            "date_from": date_from,
            "date_to": date_to,
            "level": level,
        }

    raise ValueError(f"Unsupported ads provider: {provider}")
