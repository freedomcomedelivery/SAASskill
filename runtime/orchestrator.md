# Orchestrator loop

## Per-turn algorithm
1. **Load state**: project id, stage, artifacts, blockers, open approvals.
2. **Resolve intent**: новый проект / продолжение / вопрос «почему» / side action.
3. **Run stage validator**.
4. **Autonomous work first**: web/connected-source research, calculations, drafts.
5. **Write evidence** with source + confidence + observed_at.
6. **Update artifacts**; never update a downstream artifact from an ungrounded upstream field.
7. **Re-run validators**.
8. **Select one next action** with highest unblock value.
9. Ask user only for missing private constraint or approval.
10. After external actions, read back result and append to action log.

## Question budget
Default: at most one compact user question at a time. Batch only tightly related personal constraints. Do not ask questions that tools/research can answer.

## Stage behavior
### intake
Identify whether user has an idea, a market, only a goal, or an existing launched product.

### personal_concept
Collect only constraints that materially shape project choice. This stage is not a blocker if the user already has a concrete project and enough constraints.

### market_discovery / idea_generation / idea_selection
Research first. Create candidates. Apply idea and market gates. Do not praise uniqueness.

### research_marketing
Build evidence-backed `marketing_contract`. If avatar/pain/solution/benefit do not line up, stop downstream generation.

### offer_landing
Generate one-channel landing brief and CTA. Mirror market norms when source evidence shows a simpler pattern.

### gtm_planning
Route to one channel. Calculate test economics. Build channel card.

### launch
Prepare exact action. Check current platform rules. Ask approval if side effect/spend. Execute only after approval.

### lead_onboarding
Prioritize qualified leads. Work first cases manually. Capture objections, qualification and payment outcomes.

### iteration_tracking
Use observed funnel. Diagnose earliest meaningful break. Change the smallest useful set of variables.

### scale_or_pivot
Only after repeated finished iterations or strong contradictory evidence. Separate channel failure, offer failure and idea failure.
