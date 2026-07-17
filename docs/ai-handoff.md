# Передача контекста новому чату/нейронке

Снимок документации: **2026-07-17**.

Этот файл — короткий briefing. Начинать следует с:

1. `README.md` — назначение, команды и главные ссылки.
2. `../roadmap/README.md` — завершённые, следующие и будущие этапы.
3. `project-overview.md` и `architecture.md` — runtime/source-of-truth boundaries.
4. Профильный current-contract файл из `docs/`.
5. `../reports/README.md` — только когда нужна историческая приёмка или audit evidence.

## Текущее состояние продукта

Anki Study Report — локальный add-on для Anki 26.05+ с Python runtime,
React/TypeScript dashboard и token-protected HTTP server на `127.0.0.1`.
Frontend не получает прямой доступ к Anki collection.

Продуктовый roadmap завершён до **Stage 9.5**:

```text
Stage 0–5.5  foundation, IA, Settings, Profile, Activity, Decks, UI controls
Stage 6–7    Statistics, FSRS analytics, RU/EN localization
Stage 8      native Search and undoable Safe Actions
Stage 9      notices, consent, telemetry, Signals, Notification Center, toasts
```

Следующий рекомендуемый продуктовый этап:

```text
Stage 10 — Cards v2 / Problem Triage
```

Stage 10 должен переиспользовать Search, Safe Actions, Signals и Notification
Center, а не создавать второй query/action/signal workflow. Stage 10.5 затем
harden-ит уже существующий core и CI/CD; новую delivery pipeline он не строит.

Платформенная линия завершена до **CI Stage 6B**. Cloud real-Anki E2E использует
только exact digest-pinned GHCR environment. Manual/reusable path принимает
exact Fast CI artifact, release caller — exact release artifact. Cloud
BuildKit/Buildx/containerd build-load и `type=gha` cache удалены; local Docker
build остаётся development/diagnostic fallback.

## Документационные области

```text
docs/       актуальные architecture/API/UX/security/operations contracts
roadmap/    completed/next/planned stages и зависимости
reports/    historical handoff, audits, measurements и inventories
```

При конфликте использовать приоритет:

```text
production code/tests
→ current docs
→ roadmap
→ reports
→ старые планы и предположения
```

Новые отчёты не добавляются в `docs/`.

## Что читать по типу задачи

- Dashboard payload/API: `dashboard-api.md`.
- Frontend routes/components: `frontend-map.md`, `navigation-ia.md`.
- Settings: `settings-hub.md`, `config-reference.md`.
- Search/actions: `search-query-foundation.md`, `search-v1-and-safe-actions.md`.
- Statistics/FSRS: `statistics-v1.md`, `fsrs-analytics.md`, metric definitions.
- Signals/notifications: `signals-foundation.md`, `notification-center.md`,
  `notification-preferences-and-toasts.md`.
- Notices/privacy/telemetry: `product-notices-and-consent.md`,
  `privacy-telemetry.md`, `telemetry-client.md`.
- Security: `security-and-safety.md`.
- CI/E2E/release: `ci-cd.md`, `verification-run-policy.md`, `test-matrix.md`,
  `docker-e2e.md`, `release-automation.md`.
- GHCR environment producer: `ci-optimization-stage-5-ghcr-environment-foundation.md`.
- Current GHCR-only cloud consumer: `ghcr-e2e-consumer.md`.
- Stage 6A/6B evidence: `../reports/ci/ci-optimization-stage-6a-ghcr-consumer-validation.md`
  и `../reports/ci/ci-optimization-stage-6b-ghcr-cloud-cutover.md`.
- Historical evidence: `../reports/README.md`.

## Главные технические инварианты

1. Payload/public behavior меняются синхронно в backend, frontend validators/types,
   tests и docs.
2. Frontend не читает Anki collection напрямую.
3. Dashboard server остаётся loopback-only и token-protected.
4. Нельзя ослаблять sanitizer, media validation, action allowlists или preview
   isolation. Cards preview не использует iframe и не исполняет template JS.
5. Generated assets не редактируются вручную и не коммитятся вместе с runtime
   files, logs, screenshots, profile DB, tokens или `.ankiaddon`.
6. Production-код не меняется ради устаревшего теста, если текущий contract
   доказан правильным.
7. Signals, evidence, entity references и notification preferences остаются
   локальными и не входят в remote telemetry taxonomy.
8. Read/unread, active/resolved и toast-delivered — разные состояния.
9. Telemetry event objects содержат только Worker-accepted common/event fields;
   schema/consent/privacy versions принадлежат enrollment/batch envelopes.
10. Environment image, checkout, tested package и E2E artifacts остаются
    раздельными identities.
11. Release остаётся manual/approval-gated; merge или push не публикуют add-on.

## Текущая IA

Primary navigation:

```text
Сегодня → Активность → Статистика → Колоды → Поиск → Карточки
```

Notification bell живёт в App Shell, ведёт в `#/notifications` и не является
primary tab. Notification preferences находятся в `#/settings/notifications`.
FSRS живёт только внутри Statistics (`#/stats/fsrs/...`); `#/fsrs` и `#/browse`
не возвращаются как aliases/placeholders.

## Verification policy

Каноническая non-Docker проверка:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

Cloud-primary порядок:

```text
focused tests
→ Fast CI exact package
→ required targeted real-Anki scope
→ one final standard/full only when matrix/risk requires it
```

Не повторять успешный same-SHA scope без изменения релевантного contract.
Локальный Docker используется только по прямому разрешению владельца или когда
GitHub Actions действительно недоступен и без локального воспроизведения нельзя
диагностировать конкретный сбой.

Cloud E2E не имеет BuildKit fallback: exact GHCR identity проверяется до запуска
Anki. Local Docker build и cloud GHCR consumer — разные operational contours.

## Перед завершением задачи

- проверить actual branch/base/head и несвязанные изменения;
- выполнить `git diff --check`;
- запустить релевантные tests согласно `test-matrix.md` и
  `verification-run-policy.md`;
- не заявлять PASS, merge, deployment или release без просмотренного evidence;
- обновить current docs и roadmap, если фактический scope этапа изменился;
- historical run/report сохранять в `reports/`, а не в `docs/`.
