from __future__ import annotations

from typing import Any

from .capabilities import (
    ADS_CAMPAIGNS_READ,
    ADS_CAMPAIGNS_WRITE,
    ADS_PERFORMANCE_READ,
    ANALYTICS_FUNNEL_READ,
    CRM_LEADS_READ,
    SEO_BACKLINKS,
    SEO_COMPETITOR_ADS,
    SEO_COMPETITOR_TRAFFIC,
    SEO_DOMAIN_METRICS,
    SEO_KEYWORD_METRICS,
    WEB_FETCH,
    WEB_SEARCH,
)


def _item(kind: str, key: str, description: str, *, capability: str | None = None, autonomous: bool = True, side_effect: bool = False) -> dict[str, Any]:
    return {
        "kind": kind,
        "key": key,
        "description": description,
        "autonomous": autonomous,
        "capability": capability,
        "side_effect": side_effect,
    }


def build_audit_work_queue(state: dict[str, Any]) -> list[dict[str, Any]]:
    stage = state.get("stage")
    snap = state.get("audit_snapshot") or {}
    q: list[dict[str, Any]] = []

    if stage == "audit_intake":
        return [_item("state", "audit_minimum_input", "Collect the product URL/assets and business goal; public facts should be researched instead of asked.", autonomous=False)]

    if stage == "audit_snapshot":
        if snap.get("product_url"):
            q.append(_item("research", "product_surface", "Fetch the live product/landing and extract offer, pricing, CTA, target claims and product mechanism.", capability=WEB_FETCH))
        q.extend([
            _item("metrics", "current_ads", "Read current campaign setup/performance if an ads account is connected.", capability=ADS_CAMPAIGNS_READ),
            _item("metrics", "current_funnel", "Read the observed analytics funnel if analytics is connected.", capability=ANALYTICS_FUNNEL_READ),
            _item("metrics", "current_leads", "Read current lead/qualification/payment statuses if CRM is connected.", capability=CRM_LEADS_READ),
        ])
        return q

    if stage == "audit_market_positioning":
        q.extend([
            _item("research", "close_competitors", "Find close reference products in the same geo/avatar/pain/solution space.", capability=WEB_SEARCH),
            _item("research", "competitor_domains", "Compare competitor domain/traffic signals.", capability=SEO_DOMAIN_METRICS),
            _item("research", "search_demand", "Measure how the problem/product is searched and separate demand from willingness to pay.", capability=SEO_KEYWORD_METRICS),
            _item("research", "backlink_context", "Inspect backlink/referral context when useful for competitor distribution.", capability=SEO_BACKLINKS),
        ])
        return q

    if stage == "audit_offer_landing":
        q.append(_item("research", "landing_audit", "Fetch the current landing and audit first screen, one-avatar/one-pain/one-benefit coherence, mechanism, price, CTA and friction.", capability=WEB_FETCH))
        return q

    if stage == "audit_acquisition":
        q.extend([
            _item("metrics", "ads_performance", "Read actual ad spend, impressions/reach, clicks and conversion performance.", capability=ADS_PERFORMANCE_READ),
            _item("research", "competitor_acquisition", "Inspect competitor traffic sources and relative demand signals.", capability=SEO_COMPETITOR_TRAFFIC),
            _item("research", "competitor_ads", "Inspect competitor paid-search/ad evidence where available.", capability=SEO_COMPETITOR_ADS),
        ])
        return q

    if stage == "audit_funnel_sales":
        q.extend([
            _item("metrics", "analytics_funnel", "Recover factual reach/visit → lead → qualified → payment funnel.", capability=ANALYTICS_FUNNEL_READ),
            _item("metrics", "crm_sales", "Recover qualification, need discovery, value/demo and close/payment outcomes.", capability=CRM_LEADS_READ),
        ])
        return q

    if stage == "audit_economics":
        q.extend([
            _item("metrics", "paid_costs", "Read actual paid acquisition spend/CAC components.", capability=ADS_PERFORMANCE_READ),
            _item("calculation", "commercial_economics", "Calculate price/LTV assumptions, target CAC, current CAC, payback constraints and a controlled-test budget."),
        ])
        return q

    if stage == "audit_growth_plan":
        return [_item("artifact", "growth_plan", "Refresh findings, prioritize blocking errors first, then create the smallest testable growth actions.")]

    if stage == "audit_execution":
        action_id = state.get("selected_growth_action_id")
        action = next((x for x in (state.get("growth_plan") or {}).get("actions", []) if x.get("id") == action_id), None)
        if not action:
            return [_item("decision", "select_growth_action", "Select the first executable growth action.", autonomous=False)]
        if action.get("capability") == ADS_CAMPAIGNS_WRITE:
            return [_item("action", "execute_growth_action", action.get("description", "Execute selected paid growth action."), capability=ADS_CAMPAIGNS_WRITE, side_effect=True)]
        return [_item("action", "execute_growth_action", action.get("description", "Execute selected growth action through an appropriate host tool."), autonomous=False, side_effect=bool(action.get("side_effect")))]

    if stage == "audit_iteration":
        q.extend([
            _item("metrics", "post_change_ads", "Read post-change campaign exposure and spend.", capability=ADS_PERFORMANCE_READ),
            _item("metrics", "post_change_funnel", "Read post-change funnel including qualified leads and payments.", capability=ANALYTICS_FUNNEL_READ),
            _item("analysis", "iteration_diagnosis", "Diagnose the earliest meaningful funnel break and compare to the pre-change baseline."),
        ])
        return q

    if stage == "audit_growth_loop":
        return [_item("artifact", "refresh_audit", "Refresh findings/readiness from the latest funnel and choose the next smallest useful change.")]

    return q
