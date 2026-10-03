from __future__ import annotations

WEB_SEARCH = "web.search"
WEB_FETCH = "web.fetch"
WEB_BROWSER_PARSE = "web.browser_parse"

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
    WEB_SEARCH, WEB_FETCH, WEB_BROWSER_PARSE,
    SEO_KEYWORD_METRICS, SEO_DOMAIN_METRICS, SEO_COMPETITOR_TRAFFIC,
    SEO_BACKLINKS, SEO_COMPETITOR_ADS,
    ADS_ACCOUNTS_READ, ADS_CAMPAIGNS_READ, ADS_PERFORMANCE_READ, ADS_CAMPAIGNS_WRITE,
    ANALYTICS_FUNNEL_READ, CRM_LEADS_READ, CRM_LEADS_WRITE,
}

ADS_PROVIDER_CAPS = {
    ADS_ACCOUNTS_READ,
    ADS_CAMPAIGNS_READ,
    ADS_PERFORMANCE_READ,
    ADS_CAMPAIGNS_WRITE,
}

PROVIDER_CAPABILITIES: dict[str, set[str]] = {
    "web": {WEB_SEARCH, WEB_FETCH},
    "camoufox": {WEB_FETCH, WEB_BROWSER_PARSE},
    "semrush": {
        SEO_KEYWORD_METRICS,
        SEO_DOMAIN_METRICS,
        SEO_COMPETITOR_TRAFFIC,
        SEO_BACKLINKS,
        SEO_COMPETITOR_ADS,
    },
    "ahrefs": {
        SEO_KEYWORD_METRICS,
        SEO_DOMAIN_METRICS,
        SEO_COMPETITOR_TRAFFIC,
        SEO_BACKLINKS,
        SEO_COMPETITOR_ADS,
    },
    "ads": ADS_PROVIDER_CAPS,
    "google_ads": ADS_PROVIDER_CAPS,
    "meta_ads": ADS_PROVIDER_CAPS,
    "yandex_direct": ADS_PROVIDER_CAPS,
    "apple_ads": ADS_PROVIDER_CAPS,
    "pipeboard": ADS_PROVIDER_CAPS,
    "analytics": {ANALYTICS_FUNNEL_READ},
    "crm": {CRM_LEADS_READ, CRM_LEADS_WRITE},
}

DEFAULT_PROVIDER_ORDER: dict[str, list[str]] = {
    WEB_SEARCH: ["web"],
    WEB_FETCH: ["web", "camoufox"],
    WEB_BROWSER_PARSE: ["camoufox"],
    SEO_KEYWORD_METRICS: ["semrush", "ahrefs"],
    SEO_DOMAIN_METRICS: ["ahrefs", "semrush"],
    SEO_COMPETITOR_TRAFFIC: ["semrush", "ahrefs"],
    SEO_BACKLINKS: ["ahrefs", "semrush"],
    SEO_COMPETITOR_ADS: ["semrush", "ahrefs"],
    ADS_ACCOUNTS_READ: ["ads", "pipeboard", "google_ads", "meta_ads", "yandex_direct", "apple_ads"],
    ADS_CAMPAIGNS_READ: ["ads", "pipeboard", "google_ads", "meta_ads", "yandex_direct", "apple_ads"],
    ADS_PERFORMANCE_READ: ["ads", "pipeboard", "google_ads", "meta_ads", "yandex_direct", "apple_ads"],
    ADS_CAMPAIGNS_WRITE: ["ads", "pipeboard", "google_ads", "meta_ads", "yandex_direct", "apple_ads"],
    ANALYTICS_FUNNEL_READ: ["analytics"],
    CRM_LEADS_READ: ["crm"],
    CRM_LEADS_WRITE: ["crm"],
}

CAPABILITY_FALLBACKS: dict[str, list[str]] = {
    WEB_BROWSER_PARSE: [WEB_FETCH],
    SEO_KEYWORD_METRICS: [WEB_SEARCH],
    SEO_DOMAIN_METRICS: [WEB_SEARCH],
    SEO_COMPETITOR_TRAFFIC: [WEB_SEARCH],
    SEO_BACKLINKS: [WEB_SEARCH],
    SEO_COMPETITOR_ADS: [WEB_SEARCH],
    ANALYTICS_FUNNEL_READ: [ADS_PERFORMANCE_READ],
    CRM_LEADS_READ: [ANALYTICS_FUNNEL_READ],
}

CHANNEL_AD_PROVIDERS: dict[str, list[str]] = {
    "search": ["google_ads", "pipeboard", "ads"],
    "google_display": ["google_ads", "pipeboard", "ads"],
    "meta": ["meta_ads", "pipeboard", "ads"],
    "rsya": ["yandex_direct", "ads"],
    "app_store_asa": ["apple_ads", "ads"],
}
