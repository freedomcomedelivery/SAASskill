# Pet Project Launch Operator v1.5

Это не конспект курса. Это repo-ready база для агента, который выполняет продуктовый запуск по методике «Практикума по пет-проектам».

## Что входит в v1.5
- полная карта всех блоков и уроков транскрипта;
- state machine и orchestrator loop;
- отдельные schemas для market/research/landing/economics/lead/approval;
- channel playbooks: Search, Meta, Telegram, Google Display/PMax, РСЯ, marketplaces, outreach, Product Hunt, content, Avito, App Store/ASA;
- validators вместо субъективных «оценок идеи»;
- current-platform verification layer;
- eval-набор для проверки поведения агента;
- integration map для web/Drive/GitHub/SEO/Ads/analytics/CRM;
- GitHub Actions CI;
- статический repo validator и eval contract runner.

## Что skill делает
1. Собирает минимум личного контекста.
2. Ищет зеленые рынки и ниши.
3. Генерирует/фильтрует идеи.
4. Делает глубокий competitor/avatar/pain research.
5. Собирает единый marketing contract.
6. Проектирует landing/offer.
7. Выбирает один GTM и считает тест.
8. Готовит кампанию/креативы/семантику.
9. После approve запускает внешние действия через доступные инструменты.
10. Забирает фактическую воронку и ведет последовательные итерации.

## Принцип дизайна
LLM не хранит «в голове», почему когда-то было принято решение. Каждое решение оставляет след в `project_state` и evidence store.

## Источники
Skill собран из пользовательских транскриптов, Excel/презентаций/допматериалов курса в Google Drive. Он сохраняет методологию источника, но не копирует курс целиком.

## Ограничение
Specific UI steps и platform rules быстро устаревают. Поэтому playbooks разделяют `course_heuristic` и текущие platform facts. Перед внешним действием требуется current check.


## Executable runtime

v1.5 добавляет детерминированный Python runtime: project state на диске, gate engine,
audit trail, explicit approvals, CLI и host work planner.

```bash
PYTHONPATH=src python -m saasskill init "My project" --project-id my-project
PYTHONPATH=src python -m saasskill status my-project
PYTHONPATH=src python -m saasskill plan my-project
PYTHONPATH=src python -m saasskill advance my-project
```

Подробности: [docs/runtime.md](docs/runtime.md).


## Multi-host + providers

v1.5 separates **host** from **data/action provider**. Claude, ChatGPT/OpenAI API or
another MCP client can drive the same project state.

Research routing:
`web → public/current facts`,
`Semrush/Ahrefs → SEO/keyword/domain/competitor metrics`,
`Ads → real account/campaign/performance data and approved writes`.

Semrush and Ahrefs are optional and complementary. See
[provider routing](docs/provider-routing.md) and [MCP setup](docs/mcp.md).

Claude Code can use the project-local [`.mcp.json.example`](.mcp.json.example).


## Existing project audit

For an already-built project:

```bash
PYTHONPATH=src python -m saasskill init "Existing SaaS" \
  --project-id existing-saas \
  --workflow existing_project_audit

PYTHONPATH=src python -m saasskill tick existing-saas \
  --provider web --provider ahrefs --provider ads --provider analytics --provider crm
```

The audit does not stop at recommendations. It reconstructs the market/offer/channel/
funnel/sales/economics system, produces evidence-backed findings, creates a growth
plan, executes the selected action after approval, then measures the next iteration.

Commercial readiness is a state rather than a numeric score:
`not_ready → ready_for_controlled_sales → sales_validated → ready_to_scale`.

See [existing-project audit](docs/existing-project-audit.md).


## Ahrefs

Connect Ahrefs to the host through its official remote MCP/OAuth flow; no Ahrefs
secret belongs in this repository. SAASskill includes an Ahrefs normalizer for
keyword, domain, competitor, backlink and paid-search responses.

See [docs/ahrefs.md](docs/ahrefs.md).


## Integration layer v1.5

v1.5 adds:
- Semrush normalizer;
- Google Ads / Meta Ads / Yandex Direct / Apple Ads performance normalizers;
- platform-aware ad routing;
- dry-run-first, exact-plan-bound execution plans;
- Camoufox public-page parser;
- reviewed GitHub reuse candidates.

See [integration layer](docs/integrations.md), [ads](docs/ads-integrations.md),
[Semrush](docs/semrush.md), and [Camoufox](docs/camoufox-parser.md).


## Before credentials

All request builders, dry runs, normalizers, approval/execution contracts and mocked browser transports can be tested before adding secrets. See [pre-key checklist](docs/pre-key-checklist.md).
