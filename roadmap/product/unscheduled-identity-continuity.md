# Unscheduled — Identity continuity and optional account linking

**Status:** Unscheduled concept; no stage number and no implementation commitment

## Зачем это может понадобиться

Текущая telemetry-модель считает анонимные установки, а не людей. Случайный `installation_id` подходит для opt-in telemetry и должен переживать обычные обновления add-on, но он не обязан автоматически восстанавливаться после полного удаления, смены профиля, переноса на другой компьютер или переустановки ОС.

В будущем отдельная identity-continuity модель может потребоваться только при подтверждённом пользовательском сценарии, например:

- добровольный перенос состояния между устройствами;
- восстановление локального профиля после переустановки;
- долговременная continuity для будущей синхронизации, достижений или entitlement;
- корректное различение `active installations` и добровольно связанных пользователей.

Это не является prerequisite для текущей telemetry и не должно ретроспективно расширять Stage 9.

## Базовая модель

Нужно сохранять разделение двух идентичностей:

```text
installation_id — конкретная установка/профиль на конкретном устройстве
person_id       — опциональная добровольно связанная identity между установками
```

### `installation_id`

- генерируется криптографически случайно;
- хранится локально вне generated assets;
- переживает обычное обновление add-on;
- может быть удалён пользователем вместе с telemetry state;
- не считается уникальным человеком: один человек может иметь несколько установок, а одна установка может использоваться несколькими людьми.

### `person_id`

- отсутствует по умолчанию;
- создаётся только после отдельного явного opt-in workflow;
- связывает несколько `installation_id`, но не заменяет их;
- не выводится из hardware/network fingerprint;
- должен поддерживать unlink, credential rotation/revocation и полное удаление связанных данных.

## Предпочтительные варианты continuity

При реальной необходимости сравнить и спроектировать один или несколько явных пользовательских механизмов:

1. **Recovery code / recovery secret** — сервер выдаёт случайный секрет, пользователь сохраняет его и вводит после переустановки; сервер хранит только безопасный verifier/HMAC.
2. **Экспортируемый локальный recovery file** — переносится пользователем вручную и не содержит открытых серверных credentials без дополнительной защиты.
3. **Добровольный аккаунт** — email/passkey/OAuth только как отдельный продуктовый этап с собственной threat model, deletion/export workflow и privacy contract.
4. **OS credential store** — может помочь пережить переустановку add-on на том же устройстве, но не должен считаться универсальным cross-device identity.

Автоматически и без пользовательского действия гарантировать восстановление после полного удаления нельзя без скрытого fingerprinting; такой fingerprinting не принимается.

## Явно запрещённый подход

Не строить стабильный user ID из:

- реального IP-адреса;
- MAC-адресов сетевых интерфейсов;
- machine GUID, serial numbers или набора hardware characteristics;
- хеша/HMAC от перечисленных значений;
- скрытого browser/device fingerprint.

Причины:

- IP меняется, разделяется через NAT/CGNAT и не соответствует одному человеку;
- MAC не виден удалённому Worker, может быть несколько и часто рандомизируется;
- hardware identifiers ломаются при замене компонентов и создают устойчивое скрытое профилирование;
- хеширование не превращает стабильный fingerprint в анонимные данные;
- подход противоречит текущей privacy-first архитектуре и потребует существенно более тяжёлого legal/security contract.

IP допускается только как краткоживущий антиабьюз-сигнал с rotating HMAC и ограниченным retention. Он не должен попадать в product analytics, `person_id` или долговременную linkage-модель.

## Privacy и security constraints

До реализации обязательны:

- отдельная threat model для account/recovery flow;
- новая Privacy Notice и новое согласие при материальном расширении purpose/data/recipient/retention;
- обновление consent schema, если меняется форма или семантика выбора;
- разделение telemetry, identity, entitlement и sync data;
- минимизация данных и отсутствие raw IP/MAC/hardware identifiers;
- безопасное хранение verifier вместо recovery secret в открытом виде;
- rate limits, replay protection, credential rotation и bounded recovery attempts;
- явные unlink, revoke, export и delete workflows;
- backend/frontend contracts, migrations, tests и recovery verification;
- отсутствие identity/token данных в logs, screenshots, reports и GitHub artifacts.

## Out of scope текущего наброска

- немедленное создание аккаунтов;
- remote profile/cloud sync;
- push notifications или social features;
- monetization/entitlement design;
- миграция текущих installations в `person_id` без явного пользовательского действия;
- попытка определить конкретного человека по telemetry.

## Условия возвращения к концепту

Концепт получает отдельный номер Stage только после подтверждения хотя бы одного сценария, который нельзя корректно решить локальным `installation_id` и явным экспортом/импортом. До этого запрещены placeholder route, settings, account button, hidden identifier collection и backend schema expansion.

При активации этап должен отдельно зафиксировать:

- выбранный identity/recovery UX;
- lifecycle `installation_id` и `person_id`;
- multi-device/link/unlink semantics;
- privacy notice/consent migration;
- threat model и abuse controls;
- retention/deletion/export contract;
- staged migration, rollback и verification policy.
