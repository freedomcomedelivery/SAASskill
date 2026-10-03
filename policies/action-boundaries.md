# Action boundaries

## Autonomous
Read/search; competitor research; calculations; drafts; repository artifacts; local files; campaign drafts; keyword lists; creative briefs; analysis of connected read-only data.

## Explicit approval required
- launch/pause/enable/delete campaign;
- set/change budget or bid;
- send email/DM/outreach;
- publish listing/post/site change;
- charge/refund/purchase/subscription;
- production deployment or destructive repository change;
- CRM mutations that contact or materially affect a person.

Approval request states: exact action, target account/channel, max spend, duration, assets, expected measurement and rollback/pause condition.

## Never infer approval
A user saying “готовь кампанию” is not the same as “запускай и потрать $500”.

## Exact-plan approval
Advertising writes should use `execution_plans`. An approval for one plan does not
authorize another plan. Spend caps and currency are validated at dispatch time.
Generic “approved somewhere in the project” is not sufficient authorization for a
new execution plan.


Execution approvals also store the plan digest. Any mutation to provider, operation,
target, payload, spend cap, currency or related growth action invalidates the approval.
Prepare a new plan instead of reusing the old approval.
