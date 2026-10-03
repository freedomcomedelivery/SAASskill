# Evidence policy

## Types
- `fact`: directly observed in a source/current system.
- `estimate`: computed from facts + assumptions.
- `hypothesis`: proposed causal/market claim not yet validated.
- `course_heuristic`: rule/threshold from source methodology.
- `user_constraint`: user's preference/resource/limit.

## Required fields
claim; kind; source/source_ref; observed_at; confidence; stage; supports[]. Estimates additionally store formula + assumptions.

## Discipline
- source title alone is not evidence; retain URL/ref/snippet/metric where possible;
- stale platform data gets freshness warning;
- one competitor does not prove a market;
- search volume proves search demand, not willingness to pay;
- ad presence proves acquisition activity, not profitability;
- traffic × assumed conversion × price must remain estimate;
- payment/prepayment is strongest demand signal but does not by itself prove scalability.
