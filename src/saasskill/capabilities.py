from __future__ import annotations

WEB_SEARCH = "web.search"
WEB_FETCH = "web.fetch"
SEO_KEYWORD_METRICS = "seo.keyword_metrics"
SEO_DOMAIN_METRICS = "seo.domain_metrics"
SEO_COMPETITOR_TRAFFIC = "seo.competitor_traffic"
SEO_BACKLINKS = "seo.backlinks"
SEO_COMPETITOR_ADS = "seo.competitor_ads"
ADS_ACCOUNTS_READ = "ads.accounts.read"
ADS_CAMPAIGNS_READ = "ads.campaigns.read"
ADS_PERFORMANCE_READ = "ads.performance.read"
ADS_CAMPAIGNS_WRITE = "ads.campaigns.write"
ANALYTICS_FUNNEL_READ = "analytics.funnel.read"
CRM_LEADS_READ = "crm.leads.read"
CRM_LEADS_WRITE = "crm.leads.write"

ALL_CAPABILITIES = {
    WEB_SEARCH, WEB_FETCH,
    SEO_KEYWORD_METRICS, SEO_DOMAIN_METRICS, SEO_COMPETITOR_TRAFFIC,
    SEO_BACKLINKS, SEO_COMPETITOR_ADS,
    ADS_ACCOUNTS_READ, ADS_CAMPAIGNS_READ, ADS_PERFORMANCE_READ, ADS_CAMPAIGNS_WRITE,
    ANALYTICS_FUNNEL_READ, CRM_LEADS_READ, CRM_LEADS_WRITE,
}

PROVIDER_CAPABILITIES: dict[str, set[str]] = {
    "web": {WEB_SEARCH, WEB_FETCH},
    "semrush": {
        SEO_KEYWORD_METRICS,
        SEO_DOMAIN_METRICS,
        SEO_COMPETITOR_TRAFFIC,
        SEO_COMPETITOR_ADS,
    },
    "ahrefs": {
        SEO_KEYWORD_METRICS,
        SEO_DOMAIN_METRICS,
        SEO_COMPETITOR_TRAFFIC,
        SEO_BACKLINKS,
    },
    "ads": {
        ADS_ACCOUNTS_READ,
        ADS_CAMPAIGNS_READ,
        ADS_PERFORMANCE_READ,
        ADS_CAMPAIGNS_WRITE,
    },
    "analytics": {ANALYTICS_FUNNEL_READ},
    "crm": {CRM_LEADS_READ, CRM_LEADS_WRITE},
}

DEFAULT_PROVIDER_ORDER: dict[str, list[str]] = {
    WEB_SEARCH: ["web"],
    WEB_FETCH: ["web"],
    SEO_KEYWORD_METRICS: ["semrush", "ahrefs"],
    SEO_DOMAIN_METRICS: ["ahrefs", "semrush"],
    SEO_COMPETITOR_TRAFFIC: ["semrush", "ahrefs"],
    SEO_BACKLINKS: ["ahrefs"],
    SEO_COMPETITOR_ADS: ["semrush"],
    ADS_ACCOUNTS_READ: ["ads"],
    ADS_CAMPAIGNS_READ: ["ads"],
    ADS_PERFORMANCE_READ: ["ads"],
    ADS_CAMPAIGNS_WRITE: ["ads"],
    ANALYTICS_FUNNEL_READ: ["analytics"],
    CRM_LEADS_READ: ["crm"],
    CRM_LEADS_WRITE: ["crm"],
}

CAPABILITY_FALLBACKS: dict[str, list[str]] = {
    SEO_KEYWORD_METRICS: [WEB_SEARCH],
    SEO_DOMAIN_METRICS: [WEB_SEARCH],
    SEO_COMPETITOR_TRAFFIC: [WEB_SEARCH],
    SEO_BACKLINKS: [WEB_SEARCH],
    SEO_COMPETITOR_ADS: [WEB_SEARCH],
    ANALYTICS_FUNNEL_READ: [ADS_PERFORMANCE_READ],
    CRM_LEADS_READ: [ANALYTICS_FUNNEL_READ],
}
