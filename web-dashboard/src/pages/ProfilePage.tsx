import {
  CalendarDays,
  ChevronDown,
  ChevronUp,
  Clock3,
  Layers3,
  RotateCcw,
  Settings2,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import i18n from "../i18n";
import { localeForLanguage } from "../i18n/language";
import { enumerateDateKeys, formatShortDate, isDateKey, todayDateKey } from "../lib/dateUtils";
import { formatDurationSeconds, formatInteger, formatPercent } from "../lib/formatters";
import { saveProfilePreferences, type ProfileApiResponse } from "../lib/profileApi";
import type { ProfileDeckSort, ProfileModel, StudyReport } from "../types/report";
import "../styles/profile.css";

type Props = {
  report: StudyReport | null;
  onReportUpdated?: (report: StudyReport) => void;
};

type ProfileDraft = {
  customStudyStartedOn: string;
  deckOverviewSort: ProfileDeckSort;
};

const RECENT_DAYS_COLLAPSED = 3;
const MAIN_DECKS_LIMIT = 4;
const HEATMAP_DAYS_LIMIT = 182;
const COMPACT_ACTIVITY_DAYS_LIMIT = 42;

function ProfilePage({ report, onReportUpdated }: Props) {
  const { t } = useTranslation("pages");
  const profile = report?.profile;
  const [dialogOpen, setDialogOpen] = useState(false);
  const [draft, setDraft] = useState<ProfileDraft>({ customStudyStartedOn: "", deckOverviewSort: "name" });
  const [fieldError, setFieldError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!profile) return;
    setDraft({
      customStudyStartedOn: profile.preferences.customStudyStartedOn ?? "",
      deckOverviewSort: profile.preferences.deckOverviewSort,
    });
  }, [profile]);

  if (!profile) {
    return (
      <div className="profile-page" data-testid="profile-page">
        <section className="profile-unavailable" aria-labelledby="profile-unavailable-title">
          <Settings2 aria-hidden="true" />
          <div>
            <h1 id="profile-unavailable-title">{t("profile.unavailableTitle")}</h1>
            <p>{t("profile.unavailableDescription")}</p>
          </div>
        </section>
      </div>
    );
  }

  const openDialog = () => {
    setDraft({
      customStudyStartedOn: profile.preferences.customStudyStartedOn ?? "",
      deckOverviewSort: profile.preferences.deckOverviewSort,
    });
    setFieldError("");
    setStatusMessage("");
    setDialogOpen(true);
  };

  const closeDialog = () => {
    if (savingRef.current) return;
    setDialogOpen(false);
    window.setTimeout(() => triggerRef.current?.focus(), 0);
  };

  const applyProfile = (next: ProfileModel) => {
    if (report && onReportUpdated) onReportUpdated({ ...report, profile: next });
  };

  const savePreferences = async () => {
    if (savingRef.current) return;
    const date = draft.customStudyStartedOn || null;
    if (date && (!isDateKey(date) || date > todayDateKey())) {
      setFieldError(date > todayDateKey() ? t("profile.futureDate") : t("profile.invalidDate"));
      return;
    }

    savingRef.current = true;
    setSaving(true);
    setFieldError("");
    setStatusMessage(t("profile.savingPreferences"));
    const result: ProfileApiResponse = await saveProfilePreferences({
      customStudyStartedOn: date,
      deckOverviewSort: draft.deckOverviewSort,
    }).catch(() => ({ ok: false }));
    savingRef.current = false;
    setSaving(false);

    if (result.ok && result.profile) {
      applyProfile(result.profile);
      setStatusMessage(t("profile.preferencesSaved"));
      setDialogOpen(false);
      window.setTimeout(() => triggerRef.current?.focus(), 0);
      return;
    }

    setFieldError(result.fieldErrors?.customStudyStartedOn ?? t("profile.preferencesFailed"));
    setStatusMessage("");
  };

  return (
    <div className="profile-page" data-testid="profile-page">
      <ProfileHero profile={profile} onOpenSettings={openDialog} triggerRef={triggerRef} />
      <MainDecks profile={profile} />
      <ProfileStatus profile={profile} />
      <ActivityHeatmap profile={profile} />
      <RecentHistory profile={profile} />
      <p className="sr-only" role="status" aria-live="polite">{statusMessage}</p>

      {dialogOpen ? createPortal(
        <ProfileSettingsDialog
          profile={profile}
          draft={draft}
          error={fieldError}
          saving={saving}
          onChange={setDraft}
          onSave={() => void savePreferences()}
          onClose={closeDialog}
        />,
        document.body,
      ) : null}
    </div>
  );
}

function ProfileHero({
  profile,
  onOpenSettings,
  triggerRef,
}: {
  profile: ProfileModel;
  onOpenSettings: () => void;
  triggerRef: RefObject<HTMLButtonElement>;
}) {
  const { t } = useTranslation("pages");
  const history = profile.studyHistory;
  const defaultLabels = (["ru", "en"] as const).map((language) => i18n.getFixedT(language, "pages")("profile.defaultLabel"));
  const identityLabel = defaultLabels.includes(profile.identity.label) ? t("profile.defaultLabel") : profile.identity.label;

  return (
    <header className="profile-hero" data-testid="profile-hero">
      <div className="profile-hero__backdrop" aria-hidden="true">
        <span className="profile-hero__orb profile-hero__orb--one" />
        <span className="profile-hero__orb profile-hero__orb--two" />
        <span className="profile-hero__line profile-hero__line--one" />
        <span className="profile-hero__line profile-hero__line--two" />
      </div>
      <div className="profile-hero__body">
        <div className="profile-avatar" aria-label={t("profile.avatarLabel", { initials: profile.identity.initials })} data-testid="profile-avatar">
          {profile.identity.initials}
        </div>
        <div className="profile-identity">
          <span className="profile-eyebrow">{identityLabel}</span>
          <h1 title={profile.identity.displayName}>{profile.identity.displayName}</h1>
          <div className="profile-identity__facts">
            {history.displayedStartedOn ? (
              <>
                <span>{t("profile.studyStarted", { date: formatMonthYear(history.displayedStartedOn) })}</span>
                <span>{t("profile.activityDaysFact", { days: formatDays(history.activeDays) })}</span>
              </>
            ) : (
              <span>{t("profile.historyMissing")}</span>
            )}
            {history.displayedStartedOn && history.statsAvailableFrom && history.displayedStartedOn !== history.statsAvailableFrom ? (
              <span>{t("profile.statsSince", { date: formatMonthYear(history.statsAvailableFrom) })}</span>
            ) : null}
          </div>
        </div>
        <button ref={triggerRef} type="button" className="profile-button profile-button--secondary" onClick={onOpenSettings}>
          <Settings2 size={17} aria-hidden="true" />
          {t("profile.openSettings")}
        </button>
      </div>
    </header>
  );
}

function MainDecks({ profile }: { profile: ProfileModel }) {
  const { t } = useTranslation("pages");
  const decks = profile.decks.overview.slice(0, MAIN_DECKS_LIMIT);
  const remaining = Math.max(0, profile.decks.total - decks.length);

  return (
    <section className="profile-section profile-decks" aria-labelledby="profile-decks-title" data-testid="profile-decks">
      <SectionHeading
        id="profile-decks-title"
        eyebrow={t("profile.decksEyebrow")}
        title={t("profile.mainDecks")}
        description={t("profile.mainDecksDescription")}
        action={<a href="#/decks">{t("profile.openAllDecks")}</a>}
      />
      {decks.length ? (
        <>
          <div className="profile-deck-grid">
            {decks.map((deck, index) => (
              <article key={deck.id} className={`profile-deck-card profile-deck-card--${(index % 4) + 1}`}>
                <span className="profile-deck-card__index" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                <DeckTitle name={deck.name} />
                <dl>
                  <div>
                    <dt>{t("profile.totalReviews")}</dt>
                    <dd>{formatInteger(deck.totalReviews)}</dd>
                  </div>
                  <div>
                    <dt>{t("profile.activeDays")}</dt>
                    <dd>{formatInteger(deck.activeDays)}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
          {remaining ? <p className="profile-section__note">{t("profile.moreDecks", { count: remaining })}</p> : null}
        </>
      ) : (
        <Empty icon={<Layers3 size={20} aria-hidden="true" />} text={t("profile.decksEmpty")} />
      )}
    </section>
  );
}

function DeckTitle({ name }: { name: string }) {
  const segments = name.split("::").map((segment) => segment.trim()).filter(Boolean);
  if (segments.length < 2) return <h3 title={name}>{name}</h3>;
  const leaf = segments[segments.length - 1];
  const parentPath = segments.slice(0, -1).join(" · ");

  return (
    <h3 title={name} aria-label={name} data-canonical-name={name}>
      <span className="profile-deck-card__path" aria-hidden="true">{parentPath}</span>
      <span className="profile-deck-card__name" aria-hidden="true">{leaf}</span>
    </h3>
  );
}

function ProfileStatus({ profile }: { profile: ProfileModel }) {
  const { t } = useTranslation("pages");
  const history = profile.studyHistory;
  const metrics = [
    { label: t("profile.totalReviews"), value: formatInteger(history.totalReviews), caption: t("profile.allHistory") },
    { label: t("profile.activeDays"), value: formatInteger(history.activeDays), caption: t("profile.reviewDays") },
    { label: t("profile.currentStreak"), value: formatDays(history.currentStreak), caption: t("profile.streakCaption") },
    { label: t("profile.bestStreak"), value: formatDays(history.bestStreak), caption: t("profile.availableHistory") },
    { label: t("profile.studyTime"), value: formatDurationSeconds(history.studyTimeSeconds), caption: studyTimeCaption(history.studyTimeSource) },
    { label: t("profile.averageSuccess"), value: formatPercent(history.averagePassRate), caption: t("profile.passCaption") },
  ];
  const primaryMetrics = metrics.slice(0, 2);
  const secondaryMetrics = metrics.slice(2);

  return (
    <section className="profile-status" aria-labelledby="profile-status-title" data-testid="profile-status">
      <SectionHeading
        id="profile-status-title"
        eyebrow={t("profile.statusEyebrow")}
        title={t("profile.statusTitle")}
        description={t("profile.statusDescription")}
      />
      <div className="profile-status-layout">
        <div className="profile-status-primary">
          {primaryMetrics.map((metric) => <StatusMetric key={metric.label} metric={metric} emphasis="primary" />)}
        </div>
        <div className="profile-status-secondary">
          {secondaryMetrics.map((metric) => <StatusMetric key={metric.label} metric={metric} emphasis="secondary" />)}
        </div>
      </div>
    </section>
  );
}

function StatusMetric({
  metric,
  emphasis,
}: {
  metric: { label: string; value: string; caption: string };
  emphasis: "primary" | "secondary";
}) {
  return (
    <article className={`profile-status-card profile-status-card--${emphasis}`} aria-label={`${metric.label}: ${metric.value}`}>
      <p>{metric.label}</p>
      <strong>{metric.value}</strong>
      <span>{metric.caption}</span>
    </article>
  );
}

function ActivityHeatmap({ profile }: { profile: ProfileModel }) {
  const { t } = useTranslation("pages");
  const activity = profile.activity;
  const dayMap = useMemo(() => new Map(activity.days.map((day) => [day.date, day])), [activity.days]);
  const allDates = activity.rangeStart && activity.rangeEnd ? enumerateDateKeys(activity.rangeStart, activity.rangeEnd) : [];
  const dates = allDates.slice(-HEATMAP_DAYS_LIMIT);
  const maxReviews = Math.max(1, ...dates.map((date) => dayMap.get(date)?.reviews ?? 0));
  const reviewsInRange = dates.reduce((total, date) => total + (dayMap.get(date)?.reviews ?? 0), 0);
  const activeDaysInRange = dates.filter((date) => (dayMap.get(date)?.reviews ?? 0) > 0).length;
  const presentation = dates.length <= COMPACT_ACTIVITY_DAYS_LIMIT ? "compact" : "full";

  return (
    <section
      className={`profile-section profile-activity profile-activity--${presentation}`}
      aria-labelledby="profile-activity-title"
      data-testid="profile-activity"
      data-activity-presentation={presentation}
    >
      <SectionHeading
        id="profile-activity-title"
        eyebrow={t("profile.activityEyebrow")}
        title={t("profile.activityHistory")}
        description={t("profile.activityHistoryDescription")}
        action={<a href="#/calendar">{t("profile.openCalendar")}</a>}
      />
      {dates.length ? (
        <div className="profile-activity__content">
          <div className="profile-activity__context">
            <div className="profile-activity__summary" aria-label={t("profile.activityRangeSummary", { reviews: reviewsInRange, days: activeDaysInRange })}>
              <span><strong>{formatInteger(reviewsInRange)}</strong>{t("profile.rangeReviews")}</span>
              <span><strong>{formatInteger(activeDaysInRange)}</strong>{t("profile.rangeActiveDays")}</span>
            </div>
            {presentation === "compact" ? <p>{t("profile.compactRange", { count: dates.length })}</p> : null}
          </div>
          <div className="profile-activity__visual">
            <div className="profile-heatmap-scroll">
              <div
                className="profile-heatmap"
                role="img"
                aria-label={t("profile.heatmapLabel", { start: dates[0], end: dates[dates.length - 1] })}
                data-testid="profile-heatmap"
              >
                {dates.map((date) => {
                  const reviews = dayMap.get(date)?.reviews ?? 0;
                  const intensity = reviews ? Math.min(4, Math.max(1, Math.ceil((reviews / maxReviews) * 4))) : 0;
                  return (
                    <span
                      key={date}
                      className={`profile-heatmap__day profile-heatmap__day--${intensity}`}
                      title={`${date}: ${t("profile.reviewCount", { count: reviews })}`}
                      aria-hidden="true"
                    />
                  );
                })}
              </div>
            </div>
            <div className="profile-heatmap-legend" aria-hidden="true">
              <span>{t("profile.lessActivity")}</span>
              {[0, 1, 2, 3, 4].map((intensity) => <i key={intensity} className={`profile-heatmap__day profile-heatmap__day--${intensity}`} />)}
              <span>{t("profile.moreActivity")}</span>
            </div>
          </div>
        </div>
      ) : (
        <Empty icon={<CalendarDays size={20} aria-hidden="true" />} text={t("profile.activityEmpty")} />
      )}
    </section>
  );
}

function RecentHistory({ profile }: { profile: ProfileModel }) {
  const { t } = useTranslation("pages");
  const [expanded, setExpanded] = useState(false);
  const recentDays = useMemo(
    () => [...profile.activity.recentActiveDays].sort((left, right) => right.date.localeCompare(left.date)),
    [profile.activity.recentActiveDays],
  );
  const visibleDays = expanded ? recentDays : recentDays.slice(0, RECENT_DAYS_COLLAPSED);

  return (
    <section className="profile-section profile-history" aria-labelledby="profile-history-title" data-testid="profile-history">
      <SectionHeading
        id="profile-history-title"
        eyebrow={t("profile.historyEyebrow")}
        title={t("profile.recentStudy")}
        description={t("profile.recentStudyDescription")}
      />
      {visibleDays.length ? (
        <>
          <ol className="profile-history-list" data-testid="profile-recent-days">
            {visibleDays.map((day) => (
              <li key={day.date}>
                <time dateTime={day.date}>{formatLongDate(day.date)}</time>
                <span>{recentDaySummary(day.reviews, day.studySeconds, day.passRate)}</span>
              </li>
            ))}
          </ol>
          {recentDays.length > RECENT_DAYS_COLLAPSED ? (
            <button
              type="button"
              className="profile-history-toggle"
              aria-expanded={expanded}
              onClick={() => setExpanded((value) => !value)}
            >
              {expanded ? <ChevronUp size={16} aria-hidden="true" /> : <ChevronDown size={16} aria-hidden="true" />}
              {expanded ? t("profile.showLessHistory") : t("profile.showAllHistory", { count: recentDays.length })}
            </button>
          ) : null}
        </>
      ) : (
        <Empty icon={<Clock3 size={20} aria-hidden="true" />} text={t("profile.recentEmpty")} />
      )}
    </section>
  );
}

function SectionHeading({
  id,
  eyebrow,
  title,
  description,
  action,
}: {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="profile-section-heading">
      <div>
        <span>{eyebrow}</span>
        <h2 id={id}>{title}</h2>
        <p>{description}</p>
      </div>
      {action ? <div className="profile-section-heading__action">{action}</div> : null}
    </div>
  );
}

function ProfileSettingsDialog({
  profile,
  draft,
  error,
  saving,
  onChange,
  onSave,
  onClose,
}: {
  profile: ProfileModel;
  draft: ProfileDraft;
  error: string;
  saving: boolean;
  onChange: (draft: ProfileDraft) => void;
  onSave: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation(["pages", "common"]);
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const dirty =
    draft.customStudyStartedOn !== (profile.preferences.customStudyStartedOn ?? "")
    || draft.deckOverviewSort !== profile.preferences.deckOverviewSort;

  useEffect(() => {
    titleRef.current?.focus();
  }, []);

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = Array.from(
      dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), select:not([disabled])',
      ) ?? [],
    );
    if (!focusable.length) {
      event.preventDefault();
      titleRef.current?.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && (document.activeElement === titleRef.current || document.activeElement === first)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <div
      className="profile-dialog-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !dirty && !saving) onClose();
      }}
    >
      <div
        ref={dialogRef}
        className="profile-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="profile-settings-title"
        aria-describedby="profile-settings-description"
        onKeyDown={handleKeyDown}
      >
        <header>
          <div>
            <span>{t("profile.settingsEyebrow")}</span>
            <h2 ref={titleRef} id="profile-settings-title" tabIndex={-1}>{t("profile.settingsTitle")}</h2>
            <p id="profile-settings-description">{t("profile.settingsDescription")}</p>
          </div>
          <button type="button" className="profile-icon-button" aria-label={t("actions.close", { ns: "common" })} disabled={saving} onClick={onClose}>
            <X size={19} aria-hidden="true" />
          </button>
        </header>

        <div className="profile-dialog__fields">
          <div className="profile-dialog__field">
            <label htmlFor="profile-study-start">{t("profile.startDateQuestion")}</label>
            <p>{t("profile.startDateDescription")}</p>
            <div className="profile-date-control">
              <input
                id="profile-study-start"
                type="date"
                value={draft.customStudyStartedOn}
                max={todayDateKey()}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? "profile-study-start-error" : "profile-study-start-help"}
                disabled={saving}
                onChange={(event) => onChange({ ...draft, customStudyStartedOn: event.target.value })}
              />
              <button
                type="button"
                className="profile-button profile-button--quiet"
                disabled={saving || !draft.customStudyStartedOn}
                onClick={() => onChange({ ...draft, customStudyStartedOn: "" })}
              >
                <RotateCcw size={15} aria-hidden="true" />
                {t("profile.resetDetected")}
              </button>
            </div>
            <p id="profile-study-start-help" className="profile-dialog__hint">
              {t("profile.detectedDate")} <strong>{profile.studyHistory.detectedStartedOn ? formatShortDate(profile.studyHistory.detectedStartedOn) : t("profile.notFound")}</strong>
            </p>
            {error ? <p id="profile-study-start-error" className="profile-dialog__error" role="alert">{error}</p> : null}
          </div>

          <div className="profile-dialog__field">
            <label htmlFor="profile-deck-sort">{t("profile.deckSort")}</label>
            <p>{t("profile.deckSortDescription")}</p>
            <select
              id="profile-deck-sort"
              value={draft.deckOverviewSort}
              disabled={saving}
              onChange={(event) => onChange({ ...draft, deckOverviewSort: event.target.value as ProfileDeckSort })}
            >
              <option value="name">{t("profile.sortName")}</option>
              <option value="reviews">{t("profile.sortReviews")}</option>
              <option value="active_days">{t("profile.sortActiveDays")}</option>
            </select>
          </div>
        </div>

        <footer>
          <button type="button" className="profile-button profile-button--quiet" disabled={saving} onClick={onClose}>
            {t("actions.cancel", { ns: "common" })}
          </button>
          <button type="button" className="profile-button profile-button--primary" disabled={saving || !dirty} onClick={onSave}>
            {saving ? t("actions.saving", { ns: "common" }) : t("actions.save", { ns: "common" })}
          </button>
        </footer>
      </div>
    </div>
  );
}

function Empty({ icon, text }: { icon: ReactNode; text: string }) {
  return <div className="profile-empty">{icon}<p>{text}</p></div>;
}

function formatDays(value: number) {
  const count = Math.max(0, Math.round(value));
  return i18n.t("units.day", { ns: "common", count });
}

function formatMonthYear(value: string) {
  const date = new Date(`${value}T12:00:00`);
  return Number.isNaN(date.getTime())
    ? i18n.t("profile.unknownDate", { ns: "pages" })
    : new Intl.DateTimeFormat(localeForLanguage(i18n.resolvedLanguage || i18n.language), { month: "long", year: "numeric" }).format(date);
}

function formatLongDate(value: string) {
  const date = new Date(`${value}T12:00:00`);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(localeForLanguage(i18n.resolvedLanguage || i18n.language), { day: "numeric", month: "long" });
}

function studyTimeCaption(source: ProfileModel["studyHistory"]["studyTimeSource"]) {
  if (source === "study_time_stats") return i18n.t("profile.sourceStudyTime", { ns: "pages" });
  if (source === "session_tracker") return i18n.t("profile.sourceTracker", { ns: "pages" });
  if (source === "revlog_estimate") return i18n.t("profile.sourceEstimate", { ns: "pages" });
  return i18n.t("profile.sourceUnavailable", { ns: "pages" });
}

function recentDaySummary(reviews: number, seconds: number | null, passRate: number | null) {
  return [
    i18n.t("units.review", { ns: "common", count: reviews }),
    seconds ? formatDurationSeconds(seconds) : null,
    passRate === null ? null : formatPercent(passRate),
  ].filter(Boolean).join(" · ");
}

export default ProfilePage;
