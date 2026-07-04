// ==UserScript==
// @name         Anki Study Report Dashboard Tester
// @namespace    local.anki-study-report
// @version      0.3.0
// @description  Manual smoke tests for the Anki Study Report dashboard opened from Anki.
// @match        http://127.0.0.1:*/*
// @match        http://localhost:*/*
// @run-at       document-idle
// @grant        GM_setClipboard
// @grant        GM_download
// ==/UserScript==

(function () {
  "use strict";

  const ROUTES = [
    { hash: "#/home", title: /Anki Study Report|Загрузка отчёта|Отчёт ещё не опубликован|Недействительная ссылка дашборда|Не удалось загрузить отчёт/i },
    { hash: "#/profile", title: /Профиль/i },
    { hash: "#/decks", title: /Колоды|Загрузка колод|Отчёт ещё не опубликован/i },
    { hash: "#/cards", title: /Карточки/i },
    { hash: "#/stats", title: /Статистика/i },
    { hash: "#/calendar", title: /Календарь/i },
    { hash: "#/fsrs", title: /FSRS/i },
    { hash: "#/browse", title: /Поиск/i },
    { hash: "#/actions", title: /Действия/i },
    { hash: "#/integrations", title: /Интеграции/i },
    { hash: "#/logs", title: /Логи/i },
    { hash: "#/settings\/server", title: /Настройки/i },
  ];

  const DANGEROUS_BUTTON_TEXT = /Остановить|Перезапустить|Очистить логи|Подтвердить очистку|Сохранить|Открыть Again|Открыть New|Открыть проблемные/i;
  const BAD_TEXT = /\b(undefined|null|NaN|Infinity|Invalid Date|Traceback)\b/i;
  const DEFAULT_TIMEOUT_MS = 7000;
  const TESTER_ID = "asr-tester-panel";
  const state = {
    running: false,
    failures: [],
    warnings: [],
    passes: [],
    entries: [],
    routeSnapshots: [],
    apiChecks: [],
    cardLevelChecks: [],
    consoleErrors: [],
    originalHash: window.location.hash || "#/home",
    report: null,
    startedAt: null,
    finishedAt: null,
    mode: null,
  };

  installErrorHooks();
  installPanel();

  window.AnkiStudyReportTester = {
    runSmoke: () => runSuite("smoke"),
    runFull: () => runSuite("full"),
    runApi: () => runSuite("api"),
    downloadLastReport,
    copyLastReport: downloadLastReport,
    state,
  };

  function installErrorHooks() {
    window.addEventListener("error", (event) => {
      state.consoleErrors.push(cleanLine(event.message || "window error"));
    });
    window.addEventListener("unhandledrejection", (event) => {
      state.consoleErrors.push(cleanLine(String(event.reason || "unhandled rejection")));
    });
    const originalError = console.error;
    console.error = function (...args) {
      state.consoleErrors.push(cleanLine(args.map(String).join(" ")));
      originalError.apply(console, args);
    };
  }

  function installPanel() {
    if (document.getElementById(TESTER_ID)) {
      return;
    }
    const panel = document.createElement("div");
    panel.id = TESTER_ID;
    panel.innerHTML = `
      <style>
        #${TESTER_ID} {
          position: fixed;
          right: 14px;
          bottom: 14px;
          z-index: 2147483647;
          width: min(440px, calc(100vw - 28px));
          max-height: min(620px, calc(100vh - 28px));
          display: grid;
          grid-template-rows: auto auto minmax(120px, 1fr);
          overflow: hidden;
          border: 1px solid rgba(125, 170, 220, 0.55);
          border-radius: 10px;
          background: rgba(15, 23, 34, 0.96);
          color: #eef6ff;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.38);
          font: 13px/1.45 Inter, Segoe UI, Arial, sans-serif;
        }
        #${TESTER_ID}.is-collapsed {
          width: auto;
          grid-template-rows: auto;
        }
        #${TESTER_ID}.is-collapsed .asr-body,
        #${TESTER_ID}.is-collapsed .asr-actions {
          display: none;
        }
        #${TESTER_ID} .asr-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          padding: 10px 12px;
          border-bottom: 1px solid rgba(125, 170, 220, 0.28);
        }
        #${TESTER_ID} .asr-title {
          font-weight: 700;
          white-space: nowrap;
        }
        #${TESTER_ID} .asr-status {
          color: #9fc7ef;
          font-size: 12px;
        }
        #${TESTER_ID} .asr-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          padding: 9px 12px;
          border-bottom: 1px solid rgba(125, 170, 220, 0.22);
        }
        #${TESTER_ID} button {
          border: 1px solid rgba(91, 177, 255, 0.52);
          border-radius: 7px;
          background: rgba(61, 180, 242, 0.14);
          color: #dff3ff;
          cursor: pointer;
          font: inherit;
          padding: 5px 8px;
        }
        #${TESTER_ID} button:hover {
          border-color: rgba(125, 211, 252, 0.95);
        }
        #${TESTER_ID} button:disabled {
          cursor: wait;
          opacity: 0.58;
        }
        #${TESTER_ID} .asr-body {
          overflow: auto;
          padding: 10px 12px 12px;
          color: #c7d7e8;
        }
        #${TESTER_ID} .asr-row {
          display: grid;
          grid-template-columns: 20px minmax(0, 1fr);
          gap: 6px;
          padding: 4px 0;
          border-bottom: 1px solid rgba(125, 170, 220, 0.1);
        }
        #${TESTER_ID} .pass { color: #70d99a; }
        #${TESTER_ID} .fail { color: #ff8a8a; }
        #${TESTER_ID} .warn { color: #ffd48a; }
        #${TESTER_ID} pre {
          white-space: pre-wrap;
          word-break: break-word;
          margin: 0;
          font: 12px/1.45 Consolas, Menlo, monospace;
        }
      </style>
      <div class="asr-head">
        <div>
          <div class="asr-title">ASR frontend tester</div>
          <div class="asr-status" data-role="status">ready</div>
        </div>
        <button type="button" data-action="toggle">hide</button>
      </div>
      <div class="asr-actions">
        <button type="button" data-action="smoke">Smoke</button>
        <button type="button" data-action="full">Full</button>
        <button type="button" data-action="api">API</button>
        <button type="button" data-action="download">Скачать отчёт</button>
        <button type="button" data-action="clear">Clear</button>
      </div>
      <div class="asr-body" data-role="body">
        <div class="asr-row"><span class="warn">!</span><pre>Открой dashboard из Anki и нажми Smoke или Full.</pre></div>
      </div>
    `;
    panel.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement) || target.tagName !== "BUTTON") {
        return;
      }
      const action = target.getAttribute("data-action");
      if (action === "smoke") runSuite("smoke");
      if (action === "full") runSuite("full");
      if (action === "api") runSuite("api");
      if (action === "download") downloadLastReport();
      if (action === "clear") resetResults();
      if (action === "toggle") {
        panel.classList.toggle("is-collapsed");
        target.textContent = panel.classList.contains("is-collapsed") ? "show" : "hide";
      }
    });
    document.documentElement.appendChild(panel);
  }

  async function runSuite(mode) {
    if (state.running) {
      warn("Тест уже выполняется.");
      return;
    }
    resetResults();
    state.running = true;
    state.startedAt = new Date().toISOString();
    state.finishedAt = null;
    state.mode = mode;
    setButtonsDisabled(true);
    setStatus(`running ${mode}`);
    try {
      info(`Mode: ${mode}`);
      await waitForApp();
      await runEnvironmentChecks();
      await runApiChecks();
      if (mode !== "api") {
        await runRouteChecks(mode);
        await runSafeInteractionChecks(mode);
        await runControlInventoryChecks(mode);
        assertNoConsoleErrors();
      }
      await restoreRoute();
      renderSummary(mode);
    } catch (error) {
      fail(`Fatal: ${cleanLine(error && error.message ? error.message : String(error))}`);
      renderSummary(mode);
    } finally {
      state.finishedAt = new Date().toISOString();
      state.running = false;
      setButtonsDisabled(false);
    }
  }

  async function runEnvironmentChecks() {
    section("Environment");
    pass(`URL: ${location.origin}${location.pathname}${location.search ? "?token=<hidden>" : ""}${location.hash}`);
    assert(location.hostname === "127.0.0.1" || location.hostname === "localhost", "Dashboard runs on localhost.");
    assert(Boolean(token()), "Token is present in URL.");
    assert(Boolean(document.getElementById("root") || document.getElementById("app")), "React root exists.");
  }

  async function runApiChecks() {
    section("API");
    const publicStatus = await apiGet("/api/status", { tokenRequired: false });
    rememberApi("/api/status", publicStatus);
    assert(publicStatus.ok, "/api/status responds.");
    assert(!JSON.stringify(publicStatus.data || {}).includes(token()), "/api/status does not expose raw token.");

    const tokenlessReport = await fetchJson("/api/report", { tokenValue: "" });
    rememberApi("/api/report without token", tokenlessReport);
    assert(tokenlessReport.status === 403, "/api/report rejects missing token.");

    const wrongTokenReport = await fetchJson("/api/report", { tokenValue: "__asr_wrong_token__" });
    rememberApi("/api/report wrong token", wrongTokenReport);
    assert(wrongTokenReport.status === 403, "/api/report rejects wrong token.");

    const report = await apiGet("/api/report");
    rememberApi("/api/report", report);
    if (report.status === 404) {
      warn("/api/report is empty: publish a report in Anki to test data pages.");
    } else {
      assert(report.ok, "/api/report responds with current report.");
      assertStudyReportShape(report.data);
      state.report = report.data;
    }

    const serverStatus = await apiGet("/api/server/status");
    rememberApi("/api/server/status", serverStatus);
    assert(serverStatus.ok, "/api/server/status responds.");
    assert(serverStatus.data && serverStatus.data.host === "127.0.0.1", "Server status host is local.");
    assert(!JSON.stringify(serverStatus.data || {}).includes(token()), "/api/server/status hides raw token.");

    const logs = await apiGet("/api/logs/recent?max_bytes=80000");
    rememberApi("/api/logs/recent", logs);
    assert(logs.ok, "/api/logs/recent responds.");
    assert(typeof (logs.data && logs.data.text) === "string", "Logs payload has text field.");

    const integrations = await apiGet("/api/integrations/status");
    rememberApi("/api/integrations/status", integrations);
    assert(integrations.ok, "/api/integrations/status responds.");
    assert(Array.isArray((integrations.data && integrations.data.items) || []), "Integrations payload has items array.");

    const settings = await apiGet("/api/dashboard/settings");
    rememberApi("/api/dashboard/settings", settings);
    assert(settings.ok, "/api/dashboard/settings responds.");
    assert(settings.data && typeof settings.data.settings === "object", "Dashboard settings payload has settings object.");

    await runStaticAssetChecks();
  }

  async function runRouteChecks(mode) {
    section("Routes");
    const routes = mode === "smoke"
      ? ROUTES.filter((route) => ["#/home", "#/profile", "#/decks", "#/actions", "#/logs", "#/settings/server"].includes(route.hash))
      : ROUTES;
    for (const route of routes) {
      await visitRoute(route);
      assertPageHealth(route);
    }
  }

  async function visitRoute(route) {
    window.location.hash = route.hash;
    await waitFor(() => route.title.test(headlineText()), `route ${route.hash}`, DEFAULT_TIMEOUT_MS);
    pass(`${route.hash} renders ${headlineText() || "page"}.`);
    await delay(120);
  }

  async function runSafeInteractionChecks(mode) {
    section("Safe interactions");
    await testTopNavigation(mode);
    await testSettingsPage();
    await testProfilePage();
    await testDecksPage();
    await testCardsPage(mode);
    await testCalendarPage(mode);
    await testLogsPage();
    await testIntegrationsPage();
    await testActionsPage(mode);
    await testPlaceholderNavigation();
  }

  async function testTopNavigation(mode) {
    section("Top navigation");
    await visitRoute({ hash: "#/home", title: /Anki Study Report|Загрузка отчёта|Отчёт ещё не опубликован|Недействительная ссылка дашборда|Не удалось загрузить отчёт/i });
    const links = Array.from(document.querySelectorAll("a[href^='#/']"))
      .filter((link) => !link.closest(`#${TESTER_ID}`));
    assert(links.length >= 8, "Top navigation exposes dashboard route links.");
    const targets = (mode === "smoke" ? ["#/decks", "#/cards", "#/settings/server"] : ROUTES.map((route) => route.hash))
      .filter((hash) => links.some((link) => link.getAttribute("href") === hash));
    for (const hash of targets) {
      const link = links.find((item) => item.getAttribute("href") === hash);
      if (!link) continue;
      link.click();
      await delay(160);
      assert(window.location.hash === hash, `Top navigation changes hash to ${hash}.`);
    }
  }

  async function testSettingsPage() {
    await visitRoute({ hash: "#/settings/server", title: /Настройки/i });
    const labels = Array.from(appRoot().querySelectorAll("label")).filter((label) => /Светлая|Тёмная|Авто/.test(label.textContent || ""));
    assert(labels.length >= 3, "Settings: theme switcher exposes three options.");
    for (const label of labels.slice(0, 3)) {
      label.click();
      await delay(80);
      pass(`Settings: theme option can be selected: ${cleanLine(label.textContent || "")}.`);
    }
    const refresh = buttonByText(/Обновить/i);
    if (refresh && !refresh.disabled) {
      refresh.click();
      await delay(250);
      pass("Settings: refresh button can be clicked.");
    }
    assert(buttonByText(/Остановить/i), "Settings: stop server button is visible for manual testing.");
    assert(buttonByText(/Перезапустить/i), "Settings: restart server button is visible for manual testing.");
  }

  async function testProfilePage() {
    await visitRoute({ hash: "#/profile", title: /Профиль/i });
    const periodButtons = visibleButtons().filter((button) => /Всё время|Неделя|Месяц|От \/ до/.test(button.textContent || ""));
    assert(periodButtons.length >= 4, "Profile: period selector exposes all expected options.");
    const custom = periodButtons.find((button) => /От \/ до/.test(button.textContent || ""));
    if (custom) {
      custom.click();
      await delay(180);
      assert(/Выбрать дату|От|До/.test(appText()), "Profile: custom date range controls render after selecting custom period.");
      pressEscape();
    }
    const childDecks = Array.from(appRoot().querySelectorAll("input[type='checkbox']")).find((input) => /Включать дочерние колоды/i.test(input.closest("label")?.textContent || ""));
    if (childDecks) {
      const before = childDecks.checked;
      childDecks.click();
      await delay(80);
      assert(childDecks.checked !== before, "Profile: include child decks checkbox toggles.");
      childDecks.click();
      await delay(80);
      assert(childDecks.checked === before, "Profile: include child decks checkbox can be restored.");
    } else {
      warn("Profile: include child decks checkbox was not visible.");
    }
    const deckSearch = inputByPlaceholder(/Найти колоду/i);
    if (deckSearch) {
      setInputValue(deckSearch, "__asr_deck_probe__");
      await delay(120);
      assert(deckSearch.value === "__asr_deck_probe__", "Profile: deck search accepts input.");
      setInputValue(deckSearch, "");
    } else {
      warn("Profile: deck search was not visible.");
    }
  }

  async function testDecksPage() {
    await visitRoute({ hash: "#/decks", title: /Колоды|Загрузка колод|Отчёт ещё не опубликован/i });
    const deckSearch = inputByPlaceholder(/Найти колоду/i);
    if (deckSearch) {
      setInputValue(deckSearch, "__asr_no_match__");
      await delay(150);
      assert(/Ничего не найдено|Нет колод|Отчёт ещё не опубликован|Загрузка/i.test(appText()), "Decks: search reacts to no-match input.");
      setInputValue(deckSearch, "");
      pass("Decks: search resets.");
    } else {
      warn("Decks: search was not visible in current load state.");
    }
    const statusSelect = selectWithOption(/Все статусы/i);
    if (statusSelect) {
      cycleSelect(statusSelect);
      pass("Decks: status filter select can change and restore.");
    }
    const sortable = visibleButtons().find((button) => /Повторения|Успешность|Ошибки|Средний ответ|Статус/.test(button.textContent || ""));
    if (sortable) {
      sortable.click();
      await delay(100);
      pass(`Decks: sortable header works: ${cleanLine(sortable.textContent || "")}.`);
    }
  }

  async function testCardsPage(mode) {
    await visitRoute({ hash: "#/cards", title: /Карточки/i });
    const search = inputByPlaceholder(/Поиск по тексту карточки/i);
    if (search) {
      setInputValue(search, "__asr_card_probe__");
      await delay(120);
      assert(search.value === "__asr_card_probe__", "Cards: text search accepts input.");
      setInputValue(search, "");
    }
    for (const pattern of [/Рискованные/i, /Пробелы/i, /Паттерны/i, /Проверка/i]) {
      const tab = buttonByText(pattern);
      if (tab) {
        tab.click();
        await delay(120);
        pass(`Cards: tab can be selected: ${cleanLine(tab.textContent || "")}.`);
      }
    }
    for (const select of Array.from(appRoot().querySelectorAll("select")).slice(0, mode === "smoke" ? 2 : 5)) {
      cycleSelect(select);
      pass(`Cards: select can change: ${selectLabel(select)}.`);
    }
    await delay(620);
    assert(
      /Период применён к уже собранному card-level payload/i.test(appText()),
      "Cards: period select explains frontend-filtered card-level payload semantics.",
    );
    assert(
      /Применение фильтров|Фильтры применены/i.test(document.body.textContent || ""),
      "Cards: floating apply indicator appears after filter/select changes.",
    );
    const floatingStatus = document.querySelector("[data-testid='cards-floating-status']");
    if (floatingStatus) {
      const rect = floatingStatus.getBoundingClientRect();
      assert(rect.top >= 60 && rect.left >= 0 && rect.left <= 32, "Cards: notification is placed top-left in the viewport below navigation.");
    }
    for (const pattern of [/Таблица/i, /Плитки/i, /Anki preview/i]) {
      const modeButton = buttonByText(pattern);
      assert(Boolean(modeButton), `Cards: display mode exists: ${pattern}.`);
      if (modeButton) {
        modeButton.click();
        await delay(160);
        pass(`Cards: display mode can be selected: ${cleanLine(modeButton.textContent || "")}.`);
        if (/Anki preview/i.test(modeButton.textContent || "")) {
          assert(!buttonByText(/^Front$/i) && !buttonByText(/^Back$/i) && !buttonByText(/^Both$/i), "Cards: Anki preview has no Front/Back/Both side toggle.");
          assert(/Front/i.test(appText()) && /Back/i.test(appText()), "Cards: Anki preview shows Front and Back sections together.");
          assert(!/ANKI-LIKE PREVIEW FALLBACK/i.test(appText()), "Cards: Anki preview does not show the old fallback banner.");
        }
      }
    }
    const tableMode = buttonByText(/Таблица/i);
    if (tableMode) {
      tableMode.click();
      await delay(120);
      pass("Cards: table display mode restored before table assertions.");
    }
    const resetFilters = buttonByText(/Сбросить фильтры/i);
    if (resetFilters) {
      resetFilters.click();
      await delay(150);
      pass("Cards: reset filters action is available and can be clicked.");
    }
    const diagnosticsToggle = buttonByText(/Показать диагностику|Скрыть диагностику/i);
    if (diagnosticsToggle) {
      diagnosticsToggle.click();
      await delay(160);
      assert(/Backend scope|UI filter|Card-level collector|Status|Source/i.test(appText()), "Cards: diagnostics toggle reveals useful diagnostics.");
    }
    const riskTab = buttonByText(/Рискованные/i);
    if (riskTab) {
      riskTab.click();
      await delay(120);
      pass("Cards: risk tab restored before card-level assertion.");
    }
    const cardsPeriod = Array.from(appRoot().querySelectorAll("select")).find((select) =>
      Array.from(select.options || []).some((option) => /Всё время/i.test(option.textContent || "")),
    );
    if (cardsPeriod) {
      setSelectByText(cardsPeriod, /Всё время/i);
      await delay(180);
      pass("Cards: period switched to all-time before payload table assertion.");
    }
    assert(Boolean(buttonByText(/Открыть проблемные колоды/i)), "Cards: Anki Browser action is present for manual use.");
    assert(Boolean(buttonByText(/Открыть все отфильтрованные/i)), "Cards: explicit bulk open action is present.");
    assert(Boolean(buttonByText(/Перейти в Действия/i)), "Cards: navigation to Actions is present.");
    const actionsNav = buttonByText(/Перейти в Действия/i);
    if (actionsNav) {
      assert(actionsNav.getAttribute("data-href") === "#/actions" || actionsNav.tagName === "A", "Cards: Actions navigation exposes a stable target.");
    }
    assertCardLevelUi();
  }

  async function testCalendarPage(mode) {
    await visitRoute({ hash: "#/calendar", title: /Календарь/i });
    const metrics = visibleButtons().filter((button) => /Повторения|Время|Новые|Успешность|Прогноз/.test(button.textContent || ""));
    assert(metrics.length >= 3, "Calendar: metric selector exposes multiple metrics.");
    for (const button of metrics.slice(0, mode === "smoke" ? 2 : metrics.length)) {
      button.click();
      await delay(100);
      pass(`Calendar: metric can be selected: ${cleanLine(button.textContent || "")}.`);
    }
    const period = selectWithOption(/Последние 30 дней|Последние 90 дней|Год/i);
    if (period) {
      cycleSelect(period);
      pass("Calendar: period select can change and restore.");
    }
    const dayButton = visibleButtons().find((button) => button.title && /\d{4}-\d{2}-\d{2}/.test(button.title));
    if (dayButton) {
      dayButton.click();
      await delay(100);
      pass("Calendar: day cell can be selected.");
    } else {
      warn("Calendar: no day cell was available to click.");
    }
  }

  async function testLogsPage() {
    await visitRoute({ hash: "#/logs", title: /Логи/i });
    const level = selectWithOption(/Все уровни|INFO|WARNING|ERROR|DEBUG/i);
    if (level) {
      cycleSelect(level);
      pass("Logs: level filter select can change and restore.");
    }
    const search = inputByPlaceholder(/Найти в логах/i);
    if (search) {
      setInputValue(search, "__asr_log_probe__");
      await delay(100);
      assert(search.value === "__asr_log_probe__", "Logs: search accepts input.");
      setInputValue(search, "");
    }
    const refresh = buttonByText(/Обновить/i);
    if (refresh && !refresh.disabled) {
      refresh.click();
      await delay(250);
      pass("Logs: refresh button can be clicked.");
    }
    const download = appRoot().querySelector("a[href*='/api/logs/download']");
    assert(Boolean(download), "Logs: download link is present.");
  }

  async function testIntegrationsPage() {
    await visitRoute({ hash: "#/integrations", title: /Интеграции/i });
    const refresh = buttonByText(/Обновить/i);
    if (refresh && !refresh.disabled) {
      refresh.click();
      await delay(250);
      pass("Integrations: refresh button can be clicked.");
    }
    assert(appRoot().querySelectorAll("details").length >= 1 || /Диагностика/i.test(appText()), "Integrations: diagnostics section is present.");
  }

  async function testActionsPage(mode) {
    await visitRoute({ hash: "#/actions", title: /Действия/i });
    const buttons = visibleButtons().filter((button) => !DANGEROUS_BUTTON_TEXT.test(button.textContent || ""));
    assert(buttons.length >= 1, "Actions: page exposes non-dangerous controls.");
    assert(Boolean(buttonByText(/Copy Markdown/i)), "Actions: Copy Markdown button is visible.");
    assert(Boolean(buttonByText(/Сохранить \.md/i)), "Actions: save Markdown button is visible.");
    assert(Boolean(buttonByText(/Открыть Again/i)), "Actions: Again browser action is visible for manual testing.");
    const copyMarkdown = visibleButtons().find((button) => /Copy Markdown/i.test(button.textContent || ""));
    if (mode === "full" && copyMarkdown && !copyMarkdown.disabled && window.confirm("Run Copy Markdown action from dashboard?")) {
      copyMarkdown.click();
      await delay(500);
      pass("Actions: Copy Markdown action was clicked after confirmation.");
    } else if (copyMarkdown) {
      warn("Actions: Copy Markdown action was detected but not clicked.");
    }
  }

  async function testPlaceholderNavigation() {
    for (const route of [
      { hash: "#/stats", title: /Статистика/i },
      { hash: "#/browse", title: /Поиск/i },
      { hash: "#/fsrs", title: /FSRS/i },
    ]) {
      await visitRoute(route);
      const links = Array.from(appRoot().querySelectorAll("a[href^='#/']"));
      assert(links.length >= 1, `${route.hash}: exposes internal navigation links.`);
    }
  }

  async function runControlInventoryChecks(mode) {
    section("Control inventory");
    const routes = mode === "smoke"
      ? ["#/home", "#/profile", "#/decks", "#/actions", "#/logs", "#/settings/server"]
      : ROUTES.map((route) => route.hash);
    for (const hash of routes) {
      const route = ROUTES.find((item) => item.hash === hash) || { hash, title: /./ };
      await visitRoute(route);
      const root = appRoot();
      const controls = Array.from(root.querySelectorAll("button, a, input, select, textarea"));
      assert(controls.length > 0, `${hash}: has interactive controls.`);
      const unlabeled = controls.filter((control) => !controlLabel(control));
      assert(unlabeled.length === 0, `${hash}: all visible controls have text, label, placeholder, title, or aria-label.`);
      const brokenInternalTargets = controls.filter((control) => {
        const href = control.getAttribute("href") || control.getAttribute("data-href") || "";
        return href.startsWith("#/") && !ROUTES.some((knownRoute) => knownRoute.hash === href);
      });
      assert(brokenInternalTargets.length === 0, `${hash}: all internal href/data-href targets are known routes.`);
      const disabled = controls.filter((control) => control.disabled).length;
      const details = Array.from(root.querySelectorAll("details"));
      if (details.length > 0) {
        details[0].open = true;
        await delay(80);
        pass(`${hash}: details element can be opened.`);
      }
      pass(`${hash}: controls=${controls.length}, disabled=${disabled}, details=${details.length}.`);
    }
  }

  function assertPageHealth(route) {
    const main = document.querySelector("main") || document.body;
    const snapshot = {
      hash: route.hash,
      headline: headlineText(),
      textLength: cleanLine(main.textContent || "").length,
      buttons: visibleButtons().length,
      links: appRoot().querySelectorAll("a[href]").length,
      inputs: appRoot().querySelectorAll("input").length,
      selects: appRoot().querySelectorAll("select").length,
      details: appRoot().querySelectorAll("details").length,
      svgs: appRoot().querySelectorAll("svg").length,
      scrollWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
    };
    state.routeSnapshots.push(snapshot);
    assert(Boolean(main && main.textContent && main.textContent.trim().length > 20), `${route.hash} has visible content.`);
    assert(!BAD_TEXT.test(main.textContent || ""), `${route.hash} has no obvious raw bad text.`);
    assert(document.documentElement.scrollWidth <= window.innerWidth + 8, `${route.hash} does not overflow viewport horizontally.`);
    const brokenImages = Array.from(document.images).filter((image) => image.complete && image.naturalWidth === 0);
    assert(brokenImages.length === 0, `${route.hash} has no broken images.`);
    if (route.hash === "#/home" && state.report) {
      assert(document.querySelectorAll("svg").length > 0, "Home has rendered SVG/chart/icon content.");
    }
  }

  function assertStudyReportShape(report) {
    assert(report && typeof report === "object", "Report is an object.");
    for (const key of ["metadata", "summary", "kpis", "answerDistribution", "activity", "decks", "forecast", "fsrs", "recommendations"]) {
      assert(Object.prototype.hasOwnProperty.call(report, key), `Report has ${key}.`);
    }
    assert(Array.isArray(report.kpis), "Report kpis is an array.");
    assert(Array.isArray(report.decks), "Report decks is an array.");
    assert(report.metadata && typeof report.metadata.createdAt === "string", "Report metadata has createdAt.");
    if (report.metadata && report.metadata.cardLevelSchemaVersion !== undefined) {
      assert(Number.isFinite(Number(report.metadata.cardLevelSchemaVersion)), "Report metadata cardLevelSchemaVersion is numeric when present.");
    }
    const cardRows = reportCardRows(report);
    const cardStatus = reportCardLevelStatus(report);
    rememberCardLevelCheck("payload-status", cardStatus);
    if (cardStatus.hasExplicitStatus) {
      assert(
        ["available", "unavailable", "skipped", "error"].includes(cardStatus.status),
        "Report attentionCardsStatus has a supported status.",
      );
      assert(["fresh", "cache", "mock", "unknown"].includes(cardStatus.source), "Report attentionCardsStatus has a supported source.");
      assertStatusNumberOrNull(cardStatus.scannedCards, "scannedCards");
      assertStatusNumberOrNull(cardStatus.returnedCards, "returnedCards");
      assertStatusNumberOrNull(cardStatus.revlogRows, "revlogRows");
      assertStatusNumberOrNull(cardStatus.candidateCards, "candidateCards");
      assertStatusNumberOrNull(cardStatus.revlogRowsInPeriod, "revlogRowsInPeriod");
      assertStatusNumberOrNull(cardStatus.revlogRowsAfterDeckFilter, "revlogRowsAfterDeckFilter");
      assertIssueCounts(cardStatus.issueCounts);
      assertThresholds(cardStatus.thresholds);
      pass(
        `Report card-level diagnostics: status=${cardStatus.status}, collectorRan=${String(cardStatus.collectorRan)}, collectionAvailable=${String(cardStatus.collectionAvailable)}, source=${cardStatus.source}, scanned=${String(cardStatus.scannedCards)}, returned=${String(cardStatus.returnedCards)}, revlogRows=${String(cardStatus.revlogRows)}, candidateCards=${String(cardStatus.candidateCards)}.`,
      );
    }
    if (cardRows) {
      assert(Array.isArray(cardRows), "Report card-level payload is an array when present.");
      if (cardRows.length > 0) {
        const sample = cardRows[0] || {};
        assert(sampleCardId(sample) !== undefined, "Report card-level sample has cardId.");
        assert(typeof sampleDeckName(sample) === "string" && sampleDeckName(sample).length > 0, "Report card-level sample has deckName.");
        assert(sampleFrontText(sample).length > 0, "Report card-level sample has front text via frontPreview/front/preview.primary.");
        if (sample.preview && typeof sample.preview === "object") {
          assert(typeof sample.preview.primary === "string" && sample.preview.primary.length > 0, "Report card-level sample has preview.primary.");
          assert(Array.isArray(sample.preview.mediaBadges || []), "Report card-level sample preview has mediaBadges array.");
        }
        assert(Array.isArray(sampleIssues(sample)), "Report card-level sample has issues array.");
        assert(sampleRiskScore(sample) === null || (sampleRiskScore(sample) >= 0 && sampleRiskScore(sample) <= 100), "Report card-level sample riskScore is within 0..100 when present.");
        assert(sampleBrowserSearch(sample).length > 0, "Report card-level sample can produce browser search.");
      }
    } else {
      pass("Report card-level payload is optional and absent in this report.");
    }
    assert(report.metadata && report.metadata.title === "Anki Study Report", "Report title is Anki Study Report.");
  }

  function assertCardLevelUi() {
    const cardRows = reportCardRows(state.report);
    const cardStatus = reportCardLevelStatus(state.report);
    rememberCardLevelCheck("ui-status", {
      ...cardStatus,
      rowsInPayload: cardRows ? cardRows.length : null,
      visibleKpis: appRoot().querySelectorAll(".kpi-card").length,
      visibleTables: appRoot().querySelectorAll("table").length,
      visibleDetails: appRoot().querySelectorAll("details").length,
    });
    if (cardStatus.status === "available" && cardRows && cardRows.length > 0) {
      const cardsText = appText();
      const kpiCards = Array.from(appRoot().querySelectorAll(".kpi-card"));
      assert(kpiCards.length >= 5, "Cards: KPI cards are visible with card-level data.");
      assert(kpiCards.slice(0, 5).every((card) => !/—|нет данных/i.test(card.textContent || "")), "Cards: card-level KPI values are populated.");
      assert(Boolean(appRoot().querySelector("table")), "Cards: risky cards table is visible.");
      const samplePreview = cardRows.find((row) => row.preview && (row.preview.frontText || row.preview.primary));
      if (samplePreview) {
        const frontText = sampleFrontText(samplePreview);
        assert(frontText.length > 0 && cardsText.includes(frontText), "Cards: frontText is visible in table.");
        if (samplePreview.preview.secondary) {
          assert(!cardsText.includes(samplePreview.preview.secondary), "Cards: preview secondary text is not shown in table front preview.");
        }
        if (samplePreview.preview.tertiary) {
          assert(!cardsText.includes(samplePreview.preview.tertiary), "Cards: preview tertiary text is not shown in table front preview.");
        }
      }
      const sampleWithSearch = cardRows.find((row) => sampleBrowserSearch(row));
      if (sampleWithSearch) {
        const sampleSearch = sampleBrowserSearch(sampleWithSearch);
        assert(sampleSearch.length > 0, "Cards: payload row can produce a browser search query.");
        assert(/^cid:\d+|^nid:\d+|^deck:"/.test(sampleSearch), "Cards: row search query uses cid/nid/deck fallback.");
        assert(!/\sOR\s/.test(sampleSearch), "Cards: row search query is not a giant OR query.");
      }
      assert(cardRows.some((row) => (row.issues || []).some((issue) => new RegExp(issueLabel(issue), "i").test(cardsText))), "Cards: Russian issue chips are visible.");
      assert(!/\bAUDIO\b|\bIMAGE\b|\bGIF\b/.test(cardsText), "Cards: raw AUDIO/IMAGE/GIF are not issue chips.");
      assert(!/Медиа\s*:/i.test(cardsText), "Cards: media text line is not shown.");
      assert(!/нет ударения/i.test(cardsText), "Cards: Japanese-specific missing pitch issue is hidden by default.");
      pass(`Cards: card-level UI rendered ${cardRows.length} payload rows.`);
      return;
    }
    if (cardStatus.status === "available") {
      const kpiCards = Array.from(appRoot().querySelectorAll(".kpi-card"));
      assert(/Нет проблемных карточек/i.test(appText()), "Cards: available empty scan shows no-problem empty state.");
      assert(!/В текущем отчёте нет данных уровня карточек/i.test(appText()), "Cards: available empty scan does not show absent-payload state.");
      assert(kpiCards.slice(0, 5).every((card) => /\b0\b/.test(card.textContent || "")), "Cards: available empty scan shows zero KPI values.");
      const diagnosticsToggle = buttonByText(/Показать диагностику|Скрыть диагностику/i);
      assert(Boolean(diagnosticsToggle), "Cards: available empty scan exposes diagnostics toggle.");
      if (diagnosticsToggle && /Показать диагностику/i.test(diagnosticsToggle.textContent || "")) {
        diagnosticsToggle.click();
      }
      assert(/Card-level collector|Revlog rows|Candidate cards|Scanned cards|Returned cards/i.test(appText()), "Cards: diagnostics counters are visible or available.");
      assert(/Revlog total rows|Revlog min id|Revlog max id|Revlog rows in period|Revlog rows after deck filter/i.test(appText()), "Cards: revlog self-probe diagnostics are visible.");
      assert(/Period start raw|Period end raw|Period start ms|Period end ms|Time unit normalized|Deck filter applied/i.test(appText()), "Cards: period and deck-filter diagnostics are visible.");
      assert(/Backend scope|UI filter/i.test(appText()), "Cards: backend scope and UI filter are visible.");
      assert(/Period mode|UI period|Backend recalculated|Note type profiles|Unknown note types|Detected kinds|Preview strategy|Missing field source/i.test(appText()), "Cards: note-intelligence and period diagnostics are visible.");
      assert(/Repeated Again|Slow answer seconds|Low pass rate|Leech lapses fallback|Max results/i.test(appText()), "Cards: issue thresholds are visible.");
      pass("Cards: card-level UI rendered available empty scan.");
      return;
    }
    assert(/В текущем отчёте нет данных уровня карточек/i.test(appText()), `Cards: honest fallback is visible for ${cardStatus.status} card-level status.`);
    assert(/Доступен fallback по колодам/i.test(appText()), `Cards: deck-level fallback remains visible for ${cardStatus.status} card-level status.`);
    assert(!/card-level данные доступны/i.test(appText()), "Cards: unavailable card-level state is not marked available.");
    const kpiCards = Array.from(appRoot().querySelectorAll(".kpi-card"));
    assert(kpiCards.slice(0, 5).every((card) => /—/.test(card.textContent || "")), "Cards: unavailable card-level KPI values stay blank.");
    if (cardStatus.reason) {
      assert(appText().includes(cardStatus.reason), "Cards: card-level status reason is visible.");
    }
    if (cardStatus.status === "error") {
      assert(/Не удалось собрать данные уровня карточек/i.test(appText()), "Cards: card-level error warning is visible.");
    }
    pass(`Cards: ${cardStatus.status} card-level status is treated as honest fallback, not a failure.`);
  }

  function reportCardRows(report) {
    if (!report || typeof report !== "object") return null;
    for (const key of ["cards", "cardIssues", "problemCards", "attentionCards"]) {
      if (Array.isArray(report[key])) return report[key];
    }
    return null;
  }

  function reportCardLevelStatus(report) {
    if (!report || typeof report !== "object") {
      return { status: "absent", hasExplicitStatus: false };
    }
    const status = report.attentionCardsStatus;
    const rows = reportCardRows(report);
    if (status && typeof status === "object") {
      const raw = String(status.status || "").toLowerCase();
      return {
        status: ["available", "unavailable", "skipped", "error"].includes(raw) ? raw : "unavailable",
        hasExplicitStatus: true,
        collectorRan: typeof status.collectorRan === "boolean" ? status.collectorRan : null,
        collectionAvailable: typeof status.collectionAvailable === "boolean" ? status.collectionAvailable : null,
        source: ["fresh", "cache", "mock", "unknown"].includes(String(status.source || "").toLowerCase())
          ? String(status.source || "").toLowerCase()
          : "unknown",
        scannedCards: finiteOrNull(status.scannedCards ?? status.scanned_cards),
        returnedCards: finiteOrNull(status.returnedCards ?? status.returned_cards),
        revlogRows: finiteOrNull(status.revlogRows ?? status.revlog_rows),
        candidateCards: finiteOrNull(status.candidateCards ?? status.candidate_cards),
        notesLoaded: finiteOrNull(status.notesLoaded ?? status.notes_loaded),
        fieldScanCards: finiteOrNull(status.fieldScanCards ?? status.field_scan_cards),
        cardsTotal: finiteOrNull(status.cardsTotal ?? status.cards_total),
        notesTotal: finiteOrNull(status.notesTotal ?? status.notes_total),
        periodStartRaw: finiteOrNull(status.periodStartRaw ?? status.period_start_raw),
        periodEndRaw: finiteOrNull(status.periodEndRaw ?? status.period_end_raw),
        periodStartMs: finiteOrNull(status.periodStartMs ?? status.period_start_ms),
        periodEndMs: finiteOrNull(status.periodEndMs ?? status.period_end_ms),
        timeUnitNormalized: Boolean(status.timeUnitNormalized ?? status.time_unit_normalized),
        selectedDeckIdsCount: finiteOrNull(status.selectedDeckIdsCount ?? status.selected_deck_ids_count),
        deckFilterApplied: Boolean(status.deckFilterApplied ?? status.deck_filter_applied),
        revlogTotalRows: finiteOrNull(status.revlogTotalRows ?? status.revlog_total_rows),
        revlogMinId: finiteOrNull(status.revlogMinId ?? status.revlog_min_id),
        revlogMaxId: finiteOrNull(status.revlogMaxId ?? status.revlog_max_id),
        revlogRowsInPeriod: finiteOrNull(status.revlogRowsInPeriod ?? status.revlog_rows_in_period),
        revlogRowsAfterDeckFilter: finiteOrNull(status.revlogRowsAfterDeckFilter ?? status.revlog_rows_after_deck_filter),
        noteTypeProfilesCount: finiteOrNull(status.noteTypeProfilesCount ?? status.note_type_profiles_count),
        unknownNoteTypesCount: finiteOrNull(status.unknownNoteTypesCount ?? status.unknown_note_types_count),
        detectedKinds: normalizeNumberRecord(status.detectedKinds ?? status.detected_kinds),
        previewStrategy: textOrEmpty(status.previewStrategy ?? status.preview_strategy),
        missingFieldRoleSource: textOrEmpty(status.missingFieldRoleSource ?? status.missing_field_role_source),
        reason: typeof status.reason === "string" && status.reason.trim() ? status.reason.trim() : "",
        issueCounts: normalizeNumberRecord(status.issueCounts || status.issue_counts || null),
        thresholds: normalizeNumberRecord(status.thresholds || null),
      };
    }
    if (rows && rows.length > 0) {
      return { status: "available", hasExplicitStatus: false, collectorRan: null, collectionAvailable: null, source: "unknown" };
    }
    if (rows) {
      return { status: "unavailable", hasExplicitStatus: false, collectorRan: null, collectionAvailable: null, source: "unknown" };
    }
    return { status: "absent", hasExplicitStatus: false, collectorRan: null, collectionAvailable: null, source: "unknown" };
  }

  function finiteOrNull(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  function issueLabel(value) {
    const key = String(value || "").replace(/-/g, "_").trim().toLowerCase();
    const labels = {
      leech: "частые провалы",
      repeated_again: "повторные ошибки",
      slow_answer: "долгий ответ",
      low_pass_rate: "низкая успешность",
      missing_audio: "нет аудио",
      missing_example: "нет примера",
      missing_image: "нет изображения",
      missing_meaning: "нет значения",
      missing_part_of_speech: "нет части речи",
    };
    return labels[key] || key.replace(/_/g, " ");
  }

  function sampleCardId(sample) {
    return sample.cardId ?? sample.card_id ?? sample.cid;
  }

  function sampleDeckName(sample) {
    return String(sample.deckName ?? sample.deck_name ?? sample.deck ?? "");
  }

  function sampleFrontText(sample) {
    return String(
      (sample.preview && typeof sample.preview === "object" ? sample.preview.frontText || sample.preview.front_text || sample.preview.frontOnly || sample.preview.front_only : "") ||
        sample.frontPreview ||
        sample.front_preview ||
        sample.front ||
        sample.question ||
        (sample.preview && typeof sample.preview === "object" ? sample.preview.primary : "") ||
        "",
    ).trim();
  }

  function sampleIssues(sample) {
    if (Array.isArray(sample.issues)) return sample.issues;
    if (Array.isArray(sample.problemTypes)) return sample.problemTypes;
    if (Array.isArray(sample.problem_types)) return sample.problem_types;
    if (Array.isArray(sample.missingFields)) return sample.missingFields;
    if (Array.isArray(sample.missing_fields)) return sample.missing_fields;
    return [];
  }

  function sampleRiskScore(sample) {
    const value = sample.riskScore ?? sample.risk_score;
    if (value === undefined || value === null || value === "") return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  function sampleBrowserSearch(sample) {
    const explicit = String(sample.browserSearch ?? sample.search ?? sample.searchQuery ?? sample.search_query ?? "").trim();
    if (explicit) return explicit;
    const cardId = sampleCardId(sample);
    if (cardId !== undefined && cardId !== null && String(cardId).trim()) return `cid:${String(cardId).trim()}`;
    const deckName = sampleDeckName(sample);
    return deckName ? `deck:"${deckName.replace(/"/g, '\\"')}"` : "";
  }

  function assertStatusNumberOrNull(value, label) {
    assert(value === null || Number.isFinite(value), `Report attentionCardsStatus ${label} is numeric/null.`);
  }

  function assertIssueCounts(value) {
    if (!value || typeof value !== "object") {
      warn("Report attentionCardsStatus issueCounts is absent.");
      return;
    }
    for (const key of [
      ["leech"],
      ["repeatedAgain", "repeated_again"],
      ["slowAnswer", "slow_answer"],
      ["lowPassRate", "low_pass_rate"],
      ["missingAudio", "missing_audio"],
      ["missingExample", "missing_example"],
      ["missingImage", "missing_image"],
      ["missingMeaning", "missing_meaning"],
      ["missingPartOfSpeech", "missing_part_of_speech"],
    ]) {
      const presentKey = key.find((item) => Object.prototype.hasOwnProperty.call(value, item));
      if (presentKey) {
        assert(Number.isFinite(Number(value[presentKey])) && Number(value[presentKey]) >= 0, `Report issueCounts.${presentKey} is non-negative numeric.`);
      }
    }
  }

  function assertThresholds(value) {
    if (!value || typeof value !== "object") {
      warn("Report attentionCardsStatus thresholds is absent.");
      return;
    }
    for (const key of [
      ["repeatedAgainThreshold", "repeated_again_threshold"],
      ["slowAnswerSeconds", "slow_answer_seconds"],
      ["lowPassRateThreshold", "low_pass_rate_threshold"],
      ["leechLapsesFallback", "leech_lapses_fallback"],
      ["maxResults", "max_results"],
    ]) {
      const presentKey = key.find((item) => Object.prototype.hasOwnProperty.call(value, item));
      if (presentKey) {
        assert(Number.isFinite(Number(value[presentKey])) && Number(value[presentKey]) >= 0, `Report thresholds.${presentKey} is non-negative numeric.`);
      }
    }
  }

  function normalizeNumberRecord(value) {
    const record = value && typeof value === "object" ? value : {};
    const result = {};
    for (const [key, raw] of Object.entries(record)) {
      const number = Number(raw);
      if (key && Number.isFinite(number)) {
        result[key] = number;
      }
    }
    return result;
  }

  function textOrEmpty(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  function assertNoConsoleErrors() {
    const relevant = unique(state.consoleErrors)
      .filter(Boolean)
      .filter((line) => !/ResizeObserver loop|favicon/i.test(line));
    if (relevant.length === 0) {
      pass("No captured console errors.");
      return;
    }
    for (const line of relevant.slice(0, 8)) {
      fail(`Console error: ${line}`);
    }
  }

  async function runStaticAssetChecks() {
    section("Static assets");
    const scripts = Array.from(document.scripts).filter((script) => script.src && sameOrigin(script.src));
    const styles = Array.from(document.querySelectorAll("link[rel='stylesheet']")).filter((link) => link.href && sameOrigin(link.href));
    assert(scripts.length >= 1, "Dashboard has at least one same-origin script asset.");
    assert(styles.length >= 1, "Dashboard has at least one same-origin stylesheet asset.");
    for (const element of [...scripts.slice(0, 3), ...styles.slice(0, 3)]) {
      const url = element.src || element.href;
      const response = await fetch(url, { method: "HEAD", cache: "no-store" }).catch(() => null);
      if (response && response.ok) {
        pass(`Asset responds: ${assetName(url)}.`);
      } else {
        warn(`Asset HEAD check failed or unsupported: ${assetName(url)}.`);
      }
    }
  }

  async function apiGet(path, options = {}) {
    return fetchJson(path, { tokenValue: options.tokenRequired === false ? null : token() });
  }

  async function fetchJson(path, options = {}) {
    const tokenValue = Object.prototype.hasOwnProperty.call(options, "tokenValue") ? options.tokenValue : token();
    const url = new URL(path, location.origin);
    if (tokenValue !== null) {
      url.searchParams.set("token", tokenValue || "");
    }
    const response = await fetch(url.toString(), { cache: "no-store" });
    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    return { ok: response.ok, status: response.status, data };
  }

  async function waitForApp() {
    await waitFor(() => Boolean(document.querySelector("main") || document.querySelector("h1")), "dashboard app", DEFAULT_TIMEOUT_MS);
    await delay(250);
  }

  async function restoreRoute() {
    if (window.location.hash !== state.originalHash) {
      window.location.hash = state.originalHash;
      await delay(100);
    }
  }

  function token() {
    return new URLSearchParams(window.location.search).get("token") || "";
  }

  function sameOrigin(url) {
    try {
      return new URL(url, location.href).origin === location.origin;
    } catch {
      return false;
    }
  }

  function assetName(url) {
    try {
      const parsed = new URL(url, location.href);
      return parsed.pathname.split("/").filter(Boolean).slice(-2).join("/");
    } catch {
      return String(url);
    }
  }

  function headlineText() {
    const h1 = document.querySelector("h1");
    return cleanLine(h1 ? h1.textContent || "" : "");
  }

  function appRoot() {
    return document.querySelector("main") || document.body;
  }

  function appText() {
    return appRoot().textContent || "";
  }

  function visibleButtons() {
    const appRoot = document.querySelector("main") || document.body;
    return Array.from(appRoot.querySelectorAll("button")).filter((button) => {
      const rect = button.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && button.offsetParent !== null;
    });
  }

  function buttonByText(pattern) {
    return visibleButtons().find((button) => pattern.test(button.textContent || "") || pattern.test(button.getAttribute("aria-label") || ""));
  }

  function inputByPlaceholder(pattern) {
    const appRoot = document.querySelector("main") || document.body;
    return Array.from(appRoot.querySelectorAll("input")).find((input) => pattern.test(input.placeholder || ""));
  }

  function selectWithOption(pattern) {
    return Array.from(appRoot().querySelectorAll("select")).find((select) =>
      Array.from(select.options).some((option) => pattern.test(option.textContent || "")),
    );
  }

  function cycleSelect(select) {
    if (!select || select.options.length < 2) {
      warn(`Select has no alternate option: ${selectLabel(select)}.`);
      return;
    }
    const original = select.value;
    const next = Array.from(select.options).find((option) => option.value !== original);
    if (!next) {
      warn(`Select has no distinct value: ${selectLabel(select)}.`);
      return;
    }
    setSelectValue(select, next.value);
    setSelectValue(select, original);
  }

  function setSelectByText(select, pattern) {
    const options = Array.from(select.options || []);
    const option = options.find((item) => pattern.test(item.textContent || ""));
    if (!option) {
      return false;
    }
    select.value = option.value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  function setSelectValue(select, value) {
    select.focus();
    const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, "value").set;
    setter.call(select, value);
    select.dispatchEvent(new Event("input", { bubbles: true }));
    select.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function setInputValue(input, value) {
    input.focus();
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function pressEscape() {
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  }

  function selectLabel(select) {
    if (!select) {
      return "unknown select";
    }
    return cleanLine(
      select.getAttribute("aria-label") ||
        select.closest("label")?.textContent ||
        select.options[select.selectedIndex]?.textContent ||
        "select",
    );
  }

  function controlLabel(control) {
    const rect = control.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0 || control.offsetParent === null) {
      return "hidden";
    }
    if (control instanceof HTMLInputElement && (control.type === "hidden" || control.classList.contains("sr-only"))) {
      return "hidden";
    }
    return cleanLine(
      control.textContent ||
        control.getAttribute("aria-label") ||
        control.getAttribute("title") ||
        control.getAttribute("placeholder") ||
        control.closest("label")?.textContent ||
        "",
    );
  }

  async function waitFor(predicate, label, timeoutMs) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      if (predicate()) {
        return;
      }
      await delay(80);
    }
    throw new Error(`Timed out waiting for ${label}.`);
  }

  function delay(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function assert(condition, message) {
    if (condition) {
      pass(message);
      return true;
    }
    fail(message);
    return false;
  }

  function section(message) {
    addRow("warn", `== ${message} ==`);
  }

  function info(message) {
    addRow("warn", message);
  }

  function pass(message) {
    state.passes.push(message);
    addRow("pass", message);
  }

  function warn(message) {
    state.warnings.push(message);
    addRow("warn", message);
  }

  function fail(message) {
    state.failures.push(message);
    addRow("fail", message);
  }

  function addRow(kind, message) {
    state.entries.push({
      kind,
      message,
      hash: window.location.hash || "",
      headline: headlineText(),
      at: new Date().toISOString(),
    });
    const body = document.querySelector(`#${TESTER_ID} [data-role="body"]`);
    if (!body) {
      return;
    }
    const icon = kind === "pass" ? "+" : kind === "fail" ? "x" : "!";
    const row = document.createElement("div");
    row.className = "asr-row";
    row.innerHTML = `<span class="${kind}">${icon}</span><pre></pre>`;
    row.querySelector("pre").textContent = message;
    body.appendChild(row);
    body.scrollTop = body.scrollHeight;
  }

  function renderSummary(mode) {
    const failed = state.failures.length;
    const warned = state.warnings.length;
    const passed = state.passes.length;
    const status = failed ? `FAILED ${failed}` : warned ? `PASS with ${warned} warnings` : "PASS";
    setStatus(`${status}: ${passed} ok`);
    section("Summary");
    addRow(failed ? "fail" : warned ? "warn" : "pass", `${mode}: ${status}; passed=${passed}; warnings=${warned}; failures=${failed}`);
  }

  function resetResults() {
    state.failures = [];
    state.warnings = [];
    state.passes = [];
    state.entries = [];
    state.routeSnapshots = [];
    state.apiChecks = [];
    state.cardLevelChecks = [];
    state.consoleErrors = [];
    state.report = null;
    state.startedAt = null;
    state.finishedAt = null;
    state.mode = null;
    state.originalHash = window.location.hash || "#/home";
    const body = document.querySelector(`#${TESTER_ID} [data-role="body"]`);
    if (body) {
      body.textContent = "";
    }
    setStatus("ready");
  }

  function setButtonsDisabled(disabled) {
    document.querySelectorAll(`#${TESTER_ID} button`).forEach((button) => {
      if (button.getAttribute("data-action") !== "toggle") {
        button.disabled = disabled;
      }
    });
  }

  function setStatus(message) {
    const status = document.querySelector(`#${TESTER_ID} [data-role="status"]`);
    if (status) {
      status.textContent = message;
    }
  }

  function rememberApi(name, result) {
    const data = result.data && typeof result.data === "object" ? result.data : {};
    state.apiChecks.push({
      name,
      ok: result.ok,
      status: result.status,
      keys: Object.keys(data).slice(0, 20),
      size: safeJsonSize(result.data),
    });
  }

  function rememberCardLevelCheck(name, value) {
    state.cardLevelChecks.push({
      name,
      status: value.status || "unknown",
      source: value.source || "unknown",
      rowsInPayload: value.rowsInPayload ?? null,
      collectorRan: value.collectorRan ?? null,
      collectionAvailable: value.collectionAvailable ?? null,
      scannedCards: value.scannedCards ?? null,
      returnedCards: value.returnedCards ?? null,
      revlogRows: value.revlogRows ?? null,
      candidateCards: value.candidateCards ?? null,
      revlogRowsInPeriod: value.revlogRowsInPeriod ?? null,
      revlogRowsAfterDeckFilter: value.revlogRowsAfterDeckFilter ?? null,
      visibleKpis: value.visibleKpis ?? null,
      visibleTables: value.visibleTables ?? null,
      visibleDetails: value.visibleDetails ?? null,
      reason: value.reason || "",
    });
  }

  function downloadLastReport() {
    const markdown = buildDetailedReport();
    const filename = `anki-study-report-dashboard-test-${timestampForFilename(new Date())}.md`;
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    if (typeof GM_download === "function") {
      GM_download({
        url,
        name: filename,
        saveAs: true,
        onload: () => {
          URL.revokeObjectURL(url);
          setStatus("report downloaded");
        },
        onerror: () => {
          URL.revokeObjectURL(url);
          fallbackDownload(markdown, filename);
        },
      });
      return;
    }
    fallbackDownload(markdown, filename);
  }

  function fallbackDownload(markdown, filename) {
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.documentElement.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    setStatus("report downloaded");
  }

  function buildDetailedReport() {
    const status = state.failures.length ? "FAILED" : state.warnings.length ? "PASS WITH WARNINGS" : "PASS";
    const lines = [
      "# Anki Study Report Dashboard Manual Test",
      "",
      `Status: ${status}`,
      `Mode: ${state.mode || "not run"}`,
      `Started: ${state.startedAt || "not recorded"}`,
      `Finished: ${state.finishedAt || new Date().toISOString()}`,
      `URL: ${location.origin}${location.pathname}?token=<hidden>${location.hash}`,
      `Viewport: ${window.innerWidth}x${window.innerHeight}`,
      `User agent: ${navigator.userAgent}`,
      "",
      "## Summary",
      "",
      `- Passed checks: ${state.passes.length}`,
      `- Warnings: ${state.warnings.length}`,
      `- Failures: ${state.failures.length}`,
      `- Console errors captured: ${unique(state.consoleErrors).length}`,
      `- Route snapshots: ${state.routeSnapshots.length}`,
      `- API checks: ${state.apiChecks.length}`,
      `- Card-level checks: ${state.cardLevelChecks.length}`,
      "",
      "## What This Script Checks",
      "",
      "- Local dashboard URL and token presence.",
      "- Public and token-protected API endpoints.",
      "- Dashboard report payload shape.",
      "- Optional card-level payload and Cards UI table/KPI/fallback behavior.",
      "- Route rendering for home, profile, decks, cards, stats, calendar, FSRS, browse, actions, integrations, logs, and server settings.",
      "- Visible text health: no raw undefined/null/NaN/Infinity/Invalid Date/Traceback markers.",
      "- Horizontal overflow and broken image checks.",
      "- Safe UI interactions: theme radio buttons, profile period and checkbox controls, deck filters, card tabs and selects, calendar metrics and day cells, logs filters, refresh buttons, details blocks, and placeholder navigation links.",
      "- Control labeling inventory for visible buttons, links, inputs, selects, and textareas.",
      "- Dangerous server/actions controls are detected for manual testing but are not auto-clicked.",
      "",
      "## Failures",
      "",
      ...listOrNone(state.failures, "FAIL"),
      "",
      "## Warnings",
      "",
      ...listOrNone(state.warnings, "WARN"),
      "",
      "## API Checks",
      "",
      ...table(
        ["Endpoint", "HTTP", "OK", "Payload size", "Top-level keys"],
        state.apiChecks.map((item) => [item.name, String(item.status), String(item.ok), String(item.size), item.keys.join(", ")]),
      ),
      "",
      "## Card-Level Checks",
      "",
      ...table(
        ["Name", "Status", "Source", "Rows", "Scanned", "Returned", "Revlog", "In period", "After deck", "UI KPI", "Tables", "Reason"],
        state.cardLevelChecks.map((item) => [
          item.name,
          item.status,
          item.source,
          String(item.rowsInPayload ?? ""),
          String(item.scannedCards ?? ""),
          String(item.returnedCards ?? ""),
          String(item.revlogRows ?? ""),
          String(item.revlogRowsInPeriod ?? ""),
          String(item.revlogRowsAfterDeckFilter ?? ""),
          String(item.visibleKpis ?? ""),
          String(item.visibleTables ?? ""),
          item.reason,
        ]),
      ),
      "",
      "## Route Snapshots",
      "",
      ...table(
        ["Route", "Headline", "Text", "Buttons", "Links", "Inputs", "Selects", "Details", "SVG", "Width"],
        state.routeSnapshots.map((item) => [
          item.hash,
          item.headline,
          String(item.textLength),
          String(item.buttons),
          String(item.links),
          String(item.inputs),
          String(item.selects),
          String(item.details),
          String(item.svgs),
          `${item.scrollWidth}/${item.viewportWidth}`,
        ]),
      ),
      "",
      "## Captured Console Errors",
      "",
      ...listOrNone(unique(state.consoleErrors), "CONSOLE"),
      "",
      "## Full Step Log",
      "",
      ...state.entries.map((entry, index) => `${index + 1}. [${entry.kind.toUpperCase()}] ${entry.message} (${entry.hash || "no hash"}; ${entry.headline || "no headline"}; ${entry.at})`),
      "",
      "## Raw Snapshot",
      "",
      "```json",
      JSON.stringify(
        {
          mode: state.mode,
          startedAt: state.startedAt,
          finishedAt: state.finishedAt,
          passes: state.passes,
          warnings: state.warnings,
          failures: state.failures,
          apiChecks: state.apiChecks,
          cardLevelChecks: state.cardLevelChecks,
          routeSnapshots: state.routeSnapshots,
          consoleErrors: unique(state.consoleErrors),
        },
        null,
        2,
      ),
      "```",
      "",
    ];
    return lines.join("\n");
  }

  function cleanLine(value) {
    const currentToken = token();
    const text = String(value).replace(/\s+/g, " ").trim();
    return currentToken ? text.replaceAll(currentToken, "<token>") : text;
  }

  function unique(values) {
    return Array.from(new Set(values));
  }

  function listOrNone(values, prefix) {
    if (!values.length) {
      return ["- none"];
    }
    return values.map((value) => `- ${prefix}: ${value}`);
  }

  function table(headers, rows) {
    if (!rows.length) {
      return ["No rows."];
    }
    const escapeCell = (value) => cleanLine(value).replace(/\|/g, "\\|");
    return [
      `| ${headers.map(escapeCell).join(" |")} |`,
      `| ${headers.map(() => "---").join(" |")} |`,
      ...rows.map((row) => `| ${row.map(escapeCell).join(" |")} |`),
    ];
  }

  function safeJsonSize(value) {
    try {
      return JSON.stringify(value).length;
    } catch {
      return 0;
    }
  }

  function timestampForFilename(date) {
    return date.toISOString().replace(/[:.]/g, "-");
  }
})();
