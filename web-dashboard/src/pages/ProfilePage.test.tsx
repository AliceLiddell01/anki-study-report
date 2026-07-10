// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockReport } from "../data/mockReport";
import { saveProfilePreferences } from "../lib/profileApi";
import type { ProfileModel, StudyReport } from "../types/report";
import ProfilePage from "./ProfilePage";

vi.mock("../lib/profileApi", () => ({ saveProfilePreferences: vi.fn() }));

const saveMock = vi.mocked(saveProfilePreferences);

describe("Profile MVP", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    saveMock.mockReset();
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("renders identity, default visual fallbacks and exactly six lifetime KPI", () => {
    const markup = renderToStaticMarkup(<ProfilePage report={mockReport} />);
    expect(markup).toContain('data-testid="profile-banner"');
    expect(markup).toContain('data-testid="profile-avatar"');
    expect(markup).toContain(">E2E</h1>");
    for (const label of ["Всего повторений", "Активных дней", "Текущая серия", "Лучшая серия", "Время учёбы", "Средняя успешность"]) {
      expect(markup).toContain(label);
    }
    expect((markup.match(/<article class="rounded-xl border border-ink-700 bg-ink-850 p-4 shadow-panel"/g) ?? []).length).toBe(6);
    expect(markup).not.toContain("опасно");
    expect(markup).not.toContain("рекомендац");
    expect(markup).not.toContain("Overview");
  });

  it("shows unavailable study time honestly and complete low-data states", () => {
    const report = withProfile({
      ...mockReport.profile!,
      identity: { ...mockReport.profile!.identity, ankiProfileName: null, displayName: "Пользователь Anki", initials: "ПА" },
      studyHistory: { ...mockReport.profile!.studyHistory, studyTimeSeconds: null, studyTimeSource: null },
      activity: { days: [], recentActiveDays: [], rangeStart: null, rangeEnd: null },
      decks: { ...mockReport.profile!.decks, overview: [], total: 0 },
    });
    const markup = renderToStaticMarkup(<ProfilePage report={report} />);
    expect(markup).toContain("Пользователь Anki");
    expect(markup).toContain("Нет данных");
    expect(markup).toContain("История активности появится после первых повторений");
    expect(markup).toContain("Недавних активных дней пока нет");
    expect(markup).toContain("Колоды появятся здесь после первых повторений");
  });

  it("renders newest recent activity first and global section links", () => {
    const markup = renderToStaticMarkup(<ProfilePage report={mockReport} />);
    expect(markup.indexOf("29 июня")).toBeLessThan(markup.indexOf("28 июня"));
    expect(markup).toContain('href="#/calendar"');
    expect(markup).toContain('href="#/decks"');
  });

  it("opens the accessible date dialog, validates input, closes on Escape and restores focus", async () => {
    await act(async () => root.render(<ProfilePage report={mockReport} />));
    const trigger = button("Изменить дату начала");
    await act(async () => trigger.click());
    const dialog = container.querySelector<HTMLElement>('[role="dialog"]')!;
    const input = container.querySelector<HTMLInputElement>('#profile-study-start')!;
    expect(dialog).not.toBeNull();
    expect(document.activeElement).toBe(input);

    await act(async () => {
      setNativeValue(input, "2099-01-01");
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      button("Сохранить").click();
      await Promise.resolve();
    });
    expect(container.textContent).toContain("Дата начала не может быть в будущем");
    expect(saveMock).not.toHaveBeenCalled();

    await act(async () => dialog.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
    await act(async () => new Promise((resolve) => window.setTimeout(resolve, 0)));
    expect(container.querySelector('[role="dialog"]')).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });

  it("saves and resets the study date through the narrow profile request", async () => {
    const changed = { ...mockReport.profile!, preferences: { ...mockReport.profile!.preferences, customStudyStartedOn: "2021-03-01" }, studyHistory: { ...mockReport.profile!.studyHistory, customStartedOn: "2021-03-01", displayedStartedOn: "2021-03-01" } };
    saveMock.mockResolvedValueOnce({ ok: true, profile: changed });
    const onUpdated = vi.fn();
    await act(async () => root.render(<ProfilePage report={mockReport} onReportUpdated={onUpdated} />));
    await act(async () => button("Изменить дату начала").click());
    const input = container.querySelector<HTMLInputElement>('#profile-study-start')!;
    await act(async () => {
      setNativeValue(input, "2021-03-01");
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await act(async () => { button("Сохранить").click(); await Promise.resolve(); });
    expect(saveMock).toHaveBeenCalledWith({ customStudyStartedOn: "2021-03-01" });
    expect(onUpdated).toHaveBeenCalled();

    saveMock.mockResolvedValueOnce({ ok: true, profile: { ...changed, preferences: { ...changed.preferences, customStudyStartedOn: null } } });
    await act(async () => root.render(<ProfilePage report={withProfile(changed)} onReportUpdated={onUpdated} />));
    await act(async () => button("Изменить дату начала").click());
    await act(async () => { button("Сбросить к найденной дате").click(); await Promise.resolve(); });
    expect(saveMock).toHaveBeenLastCalledWith({ customStudyStartedOn: null });
  });

  it.each([
    ["reviews", "По числу повторений"],
    ["active_days", "По активным дням"],
  ] as const)("persists %s deck sorting", async (sort, label) => {
    const nextProfile = { ...mockReport.profile!, preferences: { ...mockReport.profile!.preferences, deckOverviewSort: sort } };
    saveMock.mockResolvedValue({ ok: true, profile: nextProfile });
    await act(async () => root.render(<ProfilePage report={mockReport} onReportUpdated={vi.fn()} />));
    const select = container.querySelector<HTMLSelectElement>('#profile-deck-sort')!;
    await act(async () => {
      select.value = sort;
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(saveMock).toHaveBeenCalledWith({ deckOverviewSort: sort });
    expect(select.querySelector(`option[value="${sort}"]`)?.textContent).toBe(label);
  });

  function button(text: string): HTMLButtonElement {
    const found = Array.from(container.querySelectorAll("button")).find((item) => item.textContent?.includes(text));
    if (!found) throw new Error(`Button not found: ${text}`);
    return found;
  }
});

function withProfile(profile: ProfileModel): StudyReport {
  return { ...mockReport, profile };
}

function setNativeValue(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  setter?.call(input, value);
}
