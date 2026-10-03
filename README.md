# Pet Project Launch Operator v1.0

Это не конспект курса. Это repo-ready база для агента, который выполняет продуктовый запуск по методике «Практикума по пет-проектам».

## Что изменилось относительно v0.1
- полная карта всех блоков и уроков транскрипта;
- state machine и orchestrator loop;
- отдельные schemas для market/research/landing/economics/lead/approval;
- channel playbooks: Search, Meta, Telegram, Google Display/PMax, РСЯ, marketplaces, outreach, Product Hunt, content, Avito, App Store/ASA;
- validators вместо субъективных «оценок идеи»;
- current-platform verification layer;
- eval-набор для проверки поведения агента;
- integration map для web/Drive/GitHub/SEO/Ads/analytics/CRM.

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
