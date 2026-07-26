# Семантика предпросмотра карточки

## Контракт

Компактная идентичность карточки в Search и Cards и полный предпросмотр карточки — разные системы.

- Строки очереди используют только компактную идентичность.
- Для одной активной карточки Inspector получает один payload просмотра Search.
- Inspector отображает санитизированную нативную **лицевую сторону**.
- Расширенный диалог отображает санитизированный нативный **ответ или обратную сторону**.
- Frontend никогда не объединяет лицевую и обратную стороны вручную. Anki подставляет `{{FrontSide}}` при рендере ответа.

## Нативный источник

Для Anki 26.05+ полный предпросмотр один раз вызывает `Card.render_output(reload=True, browser=False)`. Его question, answer, CSS, AV-tags вопроса и AV-tags ответа преобразуются в существующий payload `RenderedCardPreview`. Режим Browser Appearance используется только для компактной идентичности отображения.

Если `render_output()` недоступен, явный adapter использует reviewer-вызовы `card.question(reload=True, browser=False)` и `card.answer()`. Неподдерживаемые сигнатуры безопасно переводят обработку на существующий санитизированный renderer шаблона.

## Media и безопасность

На лицевой стороне заменяются AV-маркеры вопроса. На стороне ответа заменяются AV-маркеры вопроса и ответа, поскольку ответ может содержать `FrontSide`. `mediaRefs` представляет дедуплицированное объединение ссылок обеих сторон. Рендер никогда не читает байты media-файлов.

Allowlist sanitizer, проверка URL и путей, очистка CSS и изоляция Shadow DOM остаются обязательными. Запрещены JavaScript карточек, `iframe`, `object`, `embed`, удалённые URL и URL `file:`, а также раскрытие токена или локального пути.

## Компоновка и доступность

Compact preview вписывает содержимое по ширине, обрезает собственный overflow и не перехватывает колесо: в широком workspace вертикально прокручивается страница, а слева независимо прокручивается только очередь. Drawer и диалог ответа сохраняют собственную ограниченную прокрутку. После готовности изображений и шрифтов компоновка измеряется повторно.

Корневые Anki-selectors переписываются parser-backed policy без строковых подстановок: `.card` становится preview-root `:scope`, `.card.card1` — `:scope.card1`, `.card.nightMode` — `:scope.nightMode`, а `.nightMode .child` — `:scope.nightMode .child`. Descendant selectors остаются внутри preview-root.

Resolved dashboard theme выбирает нативный Anki day/night rendering context, но не подменяет CSS шаблона:

- `light` передаёт `nightMode=false`;
- `dark` передаёт `nightMode=true`;
- при night mode класс `nightMode` присутствует и на Shadow DOM shell, и на корневом `card`;
- фактические background, foreground и дочерние цвета определяются санитизированным CSS конкретного шаблона;
- dashboard surfaces не задают native card background после template CSS и не используют глобальный `!important` override.

Один и тот же explicit boolean используется в wide preview, 1024 drawer и expanded answer modal. Переключение `light → dark → light` обновляет rendering context реактивно, не выполняет новый `/api/search/inspect`, не заменяет HTML/CSS payload и не сбрасывает selection или resolution state.

Compact preview использует непрерывную dashboard-owned outer frame и template-owned native canvas. Width-fit рассчитывается по внутренней ширине после равномерного `10 px` gap; короткая карточка увеличивает только canvas height до видимой высоты, а glyph scale остаётся width-driven. Длинный контент сохраняет тот же width-fit и обрезается compact viewport. Expanded answer остаётся auto-height и не наследует compact clipping.

Font authority:

- отсутствующий root `font-family` использует `Arial, "Noto Sans JP", sans-serif`;
- canonical Anki defaults `Arial`, `Arial, sans-serif` и `sans-serif` нормализуются parser-backed только на root `.card`;
- custom stacks, `@font-face`, child-specific fonts, platform Japanese fonts и monospace/code declarations не переписываются;
- remote font requests не добавляются, крупный font asset в package не включается.

Pre-template safe fallback задаёт default unstyled card: light — светлый фон/тёмный текст, dark — тёмный фон/светлый текст. Sanitized template CSS применяется позже и сохраняет право переопределить fallback без post-template `!important`.

Общий модальный диалог делает оболочку приложения неактивной, переводит фокус на видимый заголовок, удерживает `Tab` и `Shift+Tab`, закрывается по `Escape` и возвращает фокус вызвавшему элементу управления, если он всё ещё существует.

## Чтения

Открытие диалога ответа переиспользует payload активного просмотра Search. Строки очереди не получают данные полного предпросмотра и не инициируют чтение media.
