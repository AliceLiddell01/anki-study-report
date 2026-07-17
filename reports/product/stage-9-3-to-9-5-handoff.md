# Stage 9.3–9.5 handoff

Состояние checkout: 2026-07-17. Этапы 9.3–9.5 реализуют локальные study
signals, Notification Center и управляемые in-app toasts. Remote telemetry
taxonomy, Worker/D1 contract и release pipeline не менялись.

## Реализовано

- update-safe per-profile `notifications.sqlite3`, schema v1, quarantine,
  bounded history/evidence и независимые signal/read states;
- четыре detector families с revision-gated reconciliation и failure isolation;
- bell, compact accessible panel, `#/notifications`, filters/pagination/read;
- bounded deck/card session handoff без ID в URL;
- `#/settings/notifications`, критический default threshold, category controls;
- single-toast delivery, queue cap, summary, polite warning и persistent critical;
- focused `standard/notifications` real-Anki fixture с lifecycle и restart proof.

## Контракты, которые нельзя размывать

1. Все данные остаются в текущем Anki profile; remote telemetry не получает
   signal code, evidence, entity ID или notification preferences.
2. Detector failure не считается отсутствием кандидата; resolution требует две
   успешные missing evaluations.
3. Read/unread и active/resolved независимы.
4. Release notifications переиспользуют What’s New source.
5. Toast — presentation, Center — durable history; отключение toast не выключает
   detectors.
6. E2E fixture/proofs санитизированы и не публикуют SQLite или tokens.

## Локальная приёмка этого checkout

Targeted `standard/notifications` с workers=2 и restart: PASS на Anki 26.05.
Proof: 6 deterministic fixture notifications (3 active, 3 resolved), browser
lifecycle, 11 state screenshots, read/resolution independence, no focus steal,
no duplicate toast, saved warning threshold и restart persistence.

Облачные Fast CI, CodeQL, staging/production telemetry smoke, PR/merge и release
не выполнялись в локальном режиме. Финальный `standard/full` и итоговый
`-SkipDocker` должны быть записаны в отчёт только после фактического запуска.

## Следующий scope

Custom signal rules, editable thresholds, snooze, OS/sound/email/push,
cross-device sync, remote Notification Center и Stage 10 Cards v2 остаются вне
scope. Новая signal family требует отдельного evidence contract, detector test,
local API parity, RU/EN copy и targeted real-Anki state.
