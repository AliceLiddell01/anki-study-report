# Docker E2E

Снимок документации: 2026-07-05.

Подробный технический README уже есть в `docker/anki-e2e/README.md`. Эта
страница фиксирует, как Docker E2E вписывается в общий проект и какие решения
нельзя случайно откатить.

Для диагностики падений см. `docs/troubleshooting.md`.

## Назначение

Docker E2E запускает add-on внутри реального Anki Desktop в изолированном Linux
профиле. Это тяжелая проверка для случаев, когда обычных pytest/Vitest
недостаточно:

- startup hooks Anki;
- dashboard server readiness;
- card preview rendering;
- Shadow DOM / Anki-like preview modes;
- media loading;
- package install layout;
- взаимодействие с реальным Anki profile manager.

## Основные команды

Полный прогон с очисткой Docker volume:

```powershell
.\scripts\run_full_check.ps1 -CleanDocker
```

Только Docker E2E:

```powershell
.\scripts\run_full_check.ps1 -DockerOnly
```

Прямой runner:

```powershell
.\scripts\run_anki_e2e_docker.ps1
```

## Ключевые пути внутри контейнера

```text
/workspace                                      bind-mounted source checkout
/e2e/workspace-build                            writable copied build tree
/e2e/anki-data                                  Anki base profile directory
/e2e/anki-data/prefs21.db                       base profile metadata DB
/e2e/anki-data/E2E                              E2E profile folder
/e2e/anki-data/addons21/anki_study_report_e2e   installed add-on
/e2e/artifacts                                  E2E artifacts
```

Важно: add-on устанавливается на base-level path:

```text
/e2e/anki-data/addons21/anki_study_report_e2e
```

Не переносить его в:

```text
/e2e/anki-data/E2E/addons21/...
```

Для Anki 26.05 также важен base-level `prefs21.db` с `_global` и `E2E` rows в
таблице `profiles`.

## E2E env vars add-on

Add-on включает E2E shortcuts только при:

```text
ANKI_STUDY_REPORT_E2E=1
```

Важные переменные:

```text
ANKI_STUDY_REPORT_E2E
ANKI_STUDY_REPORT_E2E_ARTIFACTS
ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR
ANKI_STUDY_REPORT_E2E_READY_FILE
```

## Readiness artifacts

Успешный E2E пишет:

```text
e2e-artifacts/dashboard-ready.json
e2e-artifacts/addon-e2e-events.jsonl
```

На timeout/failure полезны:

```text
e2e-artifacts/anki-data-tree.txt
e2e-artifacts/addons-tree.txt
e2e-artifacts/anki-startup-tail.txt
e2e-artifacts/browser-smoke-first.json
e2e-artifacts/*.png
e2e-artifacts/*.html
```

Эти файлы помогают диагностировать, дошел ли Anki до import, hook, report build,
server start, publish и readiness write.

## Startup markers

`addon-e2e-events.jsonl` должен показывать цепочку вроде:

```text
import_start
addon_folder_present
e2e_env_detected
hook_registered
import_done
hook_fired
bootstrap_scheduled
collection_available
report_build_start
report_build_done
server_start_start
server_start_done
report_publish_start
report_publish_done
readiness_write_start
readiness_write_done
```

Если есть `addon_folder_present`, но нет `import_start`, Anki не импортировал
add-on. Если есть import/hook, но нет server/readiness, смотреть report build
или dashboard server. Если нет профиля, сначала проверять `prefs21.db` и layout.

## Browser smoke modes

Cards preview smoke mode-specific:

- `table` и `tiles` проверяют Shadow DOM host
  `data-testid="anki-card-shadow-preview"`.
- `ankiPreview` проверяет `.asr-front-preview-html`.

Если smoke падает на Cards page, сначала проверить активный mode и текущую DOM
форму. Не менять production component, пока не доказано, что проблема не в
ожиданиях smoke script.

## Runtime artifacts не коммитить

`e2e-artifacts/`, screenshots, DOM dumps, logs, local APKG input и token-bearing
outputs нужны для диагностики, но должны оставаться вне git.
