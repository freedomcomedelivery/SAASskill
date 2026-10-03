# Existing project audit workflow

This workflow is for a product that already exists: live SaaS, app, service, bot,
landing, marketplace listing or partially launched product.

It is not a generic SWOT. It reconstructs the project as a commercial system and
tests it against the course methodology.

## Stages

`audit_intake → audit_snapshot → audit_market_positioning → audit_offer_landing →
audit_acquisition → audit_funnel_sales → audit_economics → audit_growth_plan →
audit_execution → audit_iteration → audit_growth_loop`

## Audit order

1. **Snapshot** — what actually exists now: product, geo, price, claims, channels,
   assets, analytics, funnel, leads, payments.
2. **Market/positioning** — close references, avatar, pain, solution, benefit,
   searchability and market norms.
3. **Offer/landing** — one avatar, one pain, one benefit, one CTA, visible
   mechanism/value delivery, price/offer coherence.
4. **Acquisition** — whether the chosen channel matches how the market buys;
   actual campaign/traffic evidence where connected.
5. **Funnel/sales** — reach → clicks/visits → leads → qualified leads → payments,
   plus qualification → need discovery → demo/value delivery → close.
6. **Economics** — price/LTV, target CAC, actual CAC, test budget and constraints.
7. **Growth plan** — blocking errors first; then smallest measurable growth
   experiments.
8. **Execution** — prepare and, after explicit approval, perform the first action.
9. **Iteration** — measure the post-change funnel and repeat.

## Course-derived error taxonomy

The audit explicitly checks the course's launch failure classes:
- wrong channel / switching channels before one is debugged;
- rushing;
- all-for-everyone / weak segmentation;
- “funnel of fate” instead of a controlled funnel;
- premature evaluation;
- no decomposition/debugging.

It also checks the early sales chain described in the course:
`qualification → need discovery → demo/value delivery → close/payment ask`.

## Commercial readiness

No numeric score is used.

- `not_ready`: blocking commercial/funnel errors remain.
- `ready_for_controlled_sales`: system is coherent enough for a controlled funnel,
  but payment signal is not yet established.
- `sales_validated`: verified payments exist; economics/repeatability are not yet
  strong enough to call the system scalable.
- `ready_to_scale`: payment signal + viable economics + measured finished
  iteration(s).

This is deliberately stricter than “site looks good”.


## Operating commands / MCP tools

After evidence is collected for a section, mark it explicitly with
`audit_mark_section`. Do not mark a section from ungrounded model inference.

Then:
1. `audit_refresh` reconciles current findings and automatically resolves errors
   that are no longer present.
2. `audit_build_growth_plan` converts open findings into repair/growth actions.
3. `audit_select_growth_action` chooses the next action.
4. External side effects still require `approval_create → approval_decide`.
5. `audit_update_growth_action` records prepared/running/executed/measured state.
6. Run `project_tick` again to continue into measurement.

When no open repair findings remain, the generated plan automatically changes from
“fix the system” to a controlled sales test, repeatability work, or gradual scaling
according to `commercial_readiness`.
