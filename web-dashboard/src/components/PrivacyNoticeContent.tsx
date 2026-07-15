import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

export const PRIVACY_NOTICE_VERSION = "2026-07-15-production";

const copy = {
  en: {
    technicalStatus: "This Privacy Notice describes the implemented technical contract. It is not legal advice or a compliance certification.",
    controllerTitle: "Controller and contact",
    controller: "Anki Study Report is developed and controlled by AliceLiddell01. Privacy and security contact: leaf.fairy@proton.me.",
    choiceTitle: "Optional collection and purposes",
    choice: "Telemetry remains off until you explicitly allow at least one purpose. Reliability diagnostics uses bounded result, error, and duration codes. Feature usage uses allowlisted page, feature, and action codes. Declining does not disable any add-on feature.",
    dataTitle: "Data that may be sent",
    data: [
      "Add-on, Anki, telemetry-schema, consent-schema, and Privacy Notice versions.",
      "Operating-system family, interface locale and theme.",
      "Allowlisted event, page, feature, action, result, and error codes.",
      "Broad duration, result-count, and collection-size buckets, plus event time rounded to a UTC minute.",
    ],
    neverTitle: "Data that is never sent",
    never: [
      "Card or note content, field names or values, deck names, note-type names, template names, tags, or search queries.",
      "Card, note, deck, or note-type identifiers; Anki profile name, user name, email, or AnkiWeb identity.",
      "Dashboard token, token-bearing URLs, report payloads, clipboard content, paths, media filenames, free-form text, raw exceptions, or stack traces.",
    ],
    processorTitle: "Infrastructure and connection metadata",
    processor: "The Python runtime sends HTTPS requests to a separate Cloudflare Worker. Cloudflare provides the Worker and D1 infrastructure and may technically process connection metadata such as IP address and User-Agent while delivering requests. The telemetry service does not store those fields in application D1 or normal application logs. React receives neither the remote endpoint credential nor the installation write token and never calls Cloudflare directly.",
    storageTitle: "Storage, retention, and recovery",
    storage: "Primary telemetry storage is Cloudflare D1 created with EU jurisdiction. Raw event rows are retained for 60 days and daily aggregates for 24 months. Provider-managed D1 Time Travel covers 7 days. Recovery portability is periodically tested with an ephemeral D1 export/import drill inside a GitHub runner; exported SQL is deleted in the same job and is not uploaded as an artifact. R2 and independent 30-day backups are not used.",
    identityTitle: "Pseudonymous installation and sync",
    identity: "Enrollment creates a random pseudonymous installation separately for each Anki profile and device. It is not linked to AnkiWeb and is not synchronized through AnkiWeb Sync.",
    controlTitle: "Withdrawal and deletion",
    control: "You may change the selected purposes at any time. Withdrawal disables delivery and clears the local queue. Previously collected installation data can be deleted through an authenticated remote deletion request; delivery stays blocked while an offline deletion is pending.",
    version: "Privacy Notice version: 2026-07-15-production. A material change to purposes, recipients, allowed data, or retention requires a new explicit choice.",
  },
  ru: {
    technicalStatus: "Это уведомление описывает реализованный технический контракт. Оно не является юридической консультацией или сертификатом соответствия.",
    controllerTitle: "Контроллер и контакт",
    controller: "Разработчик и контроллер Anki Study Report — AliceLiddell01. Контакт по вопросам приватности и безопасности: leaf.fairy@proton.me.",
    choiceTitle: "Необязательный сбор и цели",
    choice: "Телеметрия остаётся выключенной, пока вы явно не разрешите хотя бы одну цель. Диагностика надёжности использует только ограниченные коды результата, ошибки и длительности. Статистика использования использует только разрешённые коды страниц, функций и действий. Отказ не отключает функции расширения.",
    dataTitle: "Какие данные могут отправляться",
    data: [
      "Версии расширения, Anki, telemetry schema, consent schema и Privacy Notice.",
      "Семейство операционной системы, язык и тема интерфейса.",
      "Только заранее разрешённые коды событий, страниц, функций, действий, результатов и ошибок.",
      "Широкие диапазоны длительности, количества результатов и размера коллекции, а также время события, округлённое до минуты UTC.",
    ],
    neverTitle: "Какие данные никогда не отправляются",
    never: [
      "Содержимое карточек и записей, имена или значения полей, названия колод, типов записей, шаблонов, теги и поисковые запросы.",
      "Идентификаторы карточек, записей, колод и типов записей; имя профиля Anki, имя пользователя, email и идентификатор AnkiWeb.",
      "Dashboard token, URL с токеном, отчёты, буфер обмена, пути, имена media-файлов, произвольный текст, raw exceptions и stack traces.",
    ],
    processorTitle: "Инфраструктура и метаданные соединения",
    processor: "Python runtime отправляет HTTPS-запросы в отдельный Cloudflare Worker. Cloudflare предоставляет Worker и D1 и при доставке запросов может технически обрабатывать метаданные соединения, например IP-адрес и User-Agent. Telemetry service не сохраняет эти поля в application D1 или обычных application logs. React не получает внешний credential или installation write token и не обращается к Cloudflare напрямую.",
    storageTitle: "Хранение, сроки и восстановление",
    storage: "Основное хранилище — Cloudflare D1, созданная с EU jurisdiction. Raw events хранятся 60 дней, суточные агрегаты — 24 месяца. Provider-managed D1 Time Travel покрывает 7 дней. Переносимость восстановления периодически проверяется временным D1 export/import внутри GitHub runner; SQL удаляется в том же job и не загружается в artifacts. R2 и независимые 30-дневные бэкапы не используются.",
    identityTitle: "Псевдонимная установка и синхронизация",
    identity: "Enrollment создаёт случайную псевдонимную installation отдельно для каждого профиля Anki и устройства. Она не связана с AnkiWeb и не синхронизируется через AnkiWeb Sync.",
    controlTitle: "Отзыв согласия и удаление",
    control: "Вы можете изменить разрешённые цели в любое время. Отзыв блокирует отправку и очищает локальную очередь. Уже собранные данные installation можно удалить authenticated remote request; пока offline-удаление ожидает подтверждения, отправка остаётся заблокированной.",
    version: "Версия Privacy Notice: 2026-07-15-production. Материальное изменение целей, получателей, разрешённых данных или сроков хранения требует нового явного выбора.",
  },
} as const;

export default function PrivacyNoticeContent() {
  const { i18n } = useTranslation();
  const locale = i18n.resolvedLanguage?.toLowerCase().startsWith("ru") ? "ru" : "en";
  const text = copy[locale];
  return (
    <div data-testid="privacy-notice-content" className="grid gap-4 text-sm leading-6 text-report-secondary">
      <p>{text.technicalStatus}</p>
      <NoticeSection title={text.controllerTitle}><p>{text.controller}</p></NoticeSection>
      <NoticeSection title={text.choiceTitle}><p>{text.choice}</p></NoticeSection>
      <NoticeSection title={text.dataTitle}><NoticeList items={text.data} /></NoticeSection>
      <NoticeSection title={text.neverTitle}><NoticeList items={text.never} /></NoticeSection>
      <NoticeSection title={text.processorTitle}><p>{text.processor}</p></NoticeSection>
      <NoticeSection title={text.storageTitle}><p>{text.storage}</p></NoticeSection>
      <NoticeSection title={text.identityTitle}><p>{text.identity}</p></NoticeSection>
      <NoticeSection title={text.controlTitle}><p>{text.control}</p></NoticeSection>
      <p className="font-medium text-report-text">{text.version}</p>
    </div>
  );
}

function NoticeSection({ title, children }: { title: string; children: ReactNode }) {
  return <section className="grid gap-1"><h4 className="font-semibold text-report-text">{title}</h4>{children}</section>;
}

function NoticeList({ items }: { items: readonly string[] }) {
  return <ul className="list-disc space-y-1 pl-5">{items.map((item) => <li key={item}>{item}</li>)}</ul>;
}
