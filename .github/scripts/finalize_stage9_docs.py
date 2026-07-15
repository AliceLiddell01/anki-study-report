from __future__ import annotations

from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

decision = root / "docs/decision-log.md"
text = decision.read_text(encoding="utf-8")
start = text.index("## ADR-029:")
replacement = """## ADR-029: Cloud telemetry принимается через staging-first EU D1 gates без R2

### Статус

Принято.

### Контекст

Telemetry service реализован, но production endpoint нельзя включать по одному
факту готовности кода. D1 jurisdiction задаётся при создании, секреты и реальные
URL нельзя подменять placeholders или предположениями. На текущем аккаунте R2
не активирован и требует billing setup, которого у владельца нет.

### Решение

- Cloudflare inventory выполняется read-only до любых изменений.
- Staging и production получают разные EU D1, Worker и секреты.
- Deploy остаётся manual-only; workflows используют pinned action SHA,
  Environment secrets, повторные migrations и synthetic lifecycle gates.
- Production принимается только после staging, deletion residue check и
  временного D1 export/import drill в GitHub runner. SQL удаляется в том же job
  и не публикуется как artifact.
- Текущий recovery contract использует provider-managed D1 Time Travel за 7
  дней. R2 и независимые 30-дневные бэкапы удалены из активного контракта и
  перенесены в future infrastructure work.
- Add-on получает фактический Worker URL отдельным PR только после cloud
  acceptance и финализации RU/EN уведомления.

### Последствия

Кодовая готовность Stage 9.2 и эксплуатационная готовность Cloudflare — разные
статусы. Production endpoint включается только после доказанной cloud
приёмки; изменение не создаёт release дополнения. Будущее независимое backup
storage потребует отдельного инфраструктурного решения и обновления notice.

### Где смотреть

`docs/stage-9-telemetry-foundation-handoff.md`, `docs/privacy-telemetry.md`,
private repository `anki-study-report-telemetry`.
"""
decision.write_text(text[:start] + replacement, encoding="utf-8", newline="\n")

handoff = root / "docs/stage-9-telemetry-foundation-handoff.md"
value = handoff.read_text(encoding="utf-8")
old = """## Стабилизационные PR

Корректирующие PR этого прохода будут перечислены отдельно после merge с их
собственными base/head SHA и GitHub PR statistics. Их значения нельзя
прибавлять к foundation PR без явного определения агрегата.
"""
new = """## Стабилизационные PR

### Add-on PR #21

`AliceLiddell01/anki-study-report#21` — 20 changed files, 424 additions,
52 deletions.

- base SHA: `9cdce8f0475ef0fe81016c35e9d026c89249b832`;
- tested head SHA: `e964249d7ec870103f5fff0c8835757943cf0e1f`;
- final master SHA after rebase merge: `7e02badd94872c47d1e72d2b3ffe9bca530494f0`;
- method: GitHub REST PR metadata fields `changed_files`, `additions`,
  `deletions` and base/head/merge SHA;
- scope: consent/What’s New polish, localized timestamps, screenshot contract
  and reproducible telemetry handoff.

### Add-on PR #23

`AliceLiddell01/anki-study-report#23` — 17 changed files, 276 additions,
52 deletions.

- base SHA: `7e02badd94872c47d1e72d2b3ffe9bca530494f0`;
- tested head SHA: `811baaf0f9e00f055d2d7018690cce57f98a4194`;
- final master SHA after rebase merge: `694d16c0ff0dc6a02d177e97ba147de000fbd575`;
- method: GitHub REST PR metadata fields `changed_files`, `additions`,
  `deletions` and base/head/merge SHA;
- scope: accepted production endpoint, fresh production re-consent, full RU/EN
  notice, lazy notice chunk, tests and cloud-acceptance documentation.

Эти PR statistics остаются отдельными compare ranges и не прибавляются к
foundation PR без заранее определённого агрегата.
"""
if value.count(old) != 1:
    raise SystemExit("Stage 9 stabilization placeholder mismatch")
handoff.write_text(value.replace(old, new), encoding="utf-8", newline="\n")
