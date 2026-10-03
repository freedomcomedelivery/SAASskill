# Architecture v1.0

## 1. System shape
Система состоит из восьми слоев:

1. **Knowledge** — методика, channel playbooks, эвристики, source trace.
2. **State** — структурированный `project_state`.
3. **Evidence** — facts/estimates/hypotheses/heuristics/constraints.
4. **Research** — рынки, конкуренты, цены, отзывы, ads, traffic, demand.
5. **Decision** — gates + validators, без «оценок 7.8/10».
6. **Artifact** — idea card, marketing contract, landing brief, GTM card, experiment log.
7. **Action** — внешние integrations с approve boundary.
8. **Tracking** — funnel diagnosis и next iteration.

## 2. Invariants
- один ранний эксперимент = один geo + один avatar + одна pain + одна primary benefit + один GTM;
- research может иметь много конкурентов, но один `primary_reference` должен объяснять основной контракт;
- estimate никогда не повышается до fact без нового evidence;
- недостаток данных → добыть данные/охват, а не «сделать вывод»;
- simplify gate имеет приоритет над launch;
- platform-specific instructions проверяются на актуальность перед исполнением;
- менять в итерации минимальное число причинных переменных, иначе теряется обучающий сигнал.

## 3. State transitions
Переходы задаются не временем и не пожеланием пользователя, а gate results. Gate может вернуть:
- `pass`;
- `needs_evidence`;
- `needs_user_input`;
- `needs_simplification`;
- `blocked_by_economics`;
- `blocked_by_platform`.

## 4. Human-readable layer
У каждой процедуры два режима:
- `operator`: кратко что сделано/что дальше;
- `explain`: теория и причина решения по запросу пользователя.

## 5. Integration philosophy
Skill не должен зависеть от одного провайдера. Tool router ищет capability: web research, Drive, repository, SEO/keyword data, ads read/write, analytics, CRM. Конкретные adapters могут меняться.
