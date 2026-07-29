// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockReport } from "../data/mockReport";
import i18n from "../i18n";
import { saveProfilePreferences } from "../lib/profileApi";
import type { ProfileModel, StudyReport } from "../types/report";
import ProfilePage from "./ProfilePage";

vi.mock("../lib/profileApi", () => ({ saveProfilePreferences: vi.fn() }));

const saveMock = vi.mocked(saveProfilePreferences);

describe("Profile production foundation", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    await i18n.changeLanguage("ru");
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    saveMock.mockReset();
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("renders the required hierarchy from factual profile data without speculative systems", () => {
    const report = withProfile({
      ...mockReport.profile!,
      identity: { ...mockReport.profile!.identity, displayName: "Очень длинное имя локального профиля 文法", initials: "ДИ" },
      decks: {
        ...mockReport.profile!.decks,
        overview: [
          { id: 9, name: "Japanese::Grammar N3", totalReviews: 410, activeDays: 12 },
          { id: 10, name: "Medical terminology", totalReviews: 305, activeDays: 9 },
          { id: 11, name: "История искусства", totalReviews: 204, activeDays: 7 },
          { id: 12, name: "Mathematics", totalReviews: 188, activeDays: 6 },
        ],
        total: 7,
      },
    });
    const markup = renderToStaticMarkup(<ProfilePage report={report} />);
    const order = [
      'data-testid="profile-hero"',
      'data-testid="profile-learning"',
      'data-testid="profile-status"',
      'data-testid="profile-activity"',
      'data-testid="profile-history"',
    ].map((marker) => markup.indexOf(marker));

    expect(order.every((position) => position >= 0)).toBe(true);
    expect(order).toEqual([...order].sort((left, right) => left - right));
    expect(markup).toContain("Очень длинное имя локального профиля 文法");
    expect(markup).toContain("Japanese::Grammar N3");
    expect(markup).toContain("410");
    expect(markup).toContain("12");
    expect(markup).toContain("Ещё 3 области");
    expect((markup.match(/class="profile-status-card"/g) ?? [])).toHaveLength(6);
    expect(markup).not.toMatch(/\bXP\b|достижен|achievement|mastery|уров(ень|ня)/i);
  });

  it("renders honest unavailable and low-data states without fabricated profile values", () => {
    const unavailable = renderToStaticMarkup(<ProfilePage report={{ ...mockReport, profile: undefined }} />);
    expect(unavailable).toContain("Профиль пока недоступен");
    expect(unavailable).not.toContain("Пользователь Anki");

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

  it("keeps global navigation links bounded to existing routes", () => {
    const markup = renderToStaticMarkup(<ProfilePage report={mockReport} />);
    expect(markup).toContain('href="#/calendar"');
    expect(markup).toContain('href="#/decks"');
    expect(markup.match(/href=/g)).toHaveLength(2);
  });

  it("does not add a nested main landmark inside the application shell", () => {
    const markup = renderToStaticMarkup(<main><ProfilePage report={mockReport} /></main>);
    expect(markup.match(/<main(?:\s|>)/g)).toHaveLength(1);
  });

  it("shows three newest history rows by default and expands existing recent data", async () => {
    await act(async () => root.render(<ProfilePage report={mockReport} />));
    const list = () => container.querySelectorAll('[data-testid="profile-recent-days"] li');
    expect(list()).toHaveLength(3);
    expect(list()[0].textContent).toContain("29 июня");
    expect(list()[1].textContent).toContain("28 июня");

    await act(async () => button("Показать все дни").click());
    expect(list()).toHaveLength(mockReport.profile!.activity.recentActiveDays.length);
    expect(button("Свернуть историю").getAttribute("aria-expanded")).toBe("true");
  });

  it("opens an accessible unified dialog, validates future dates, traps Tab and restores focus on Escape", async () => {
    await act(async () => root.render(<ProfilePage report={mockReport} />));
    const trigger = button("Настроить профиль");
    await act(async () => trigger.click());
    const dialog = document.querySelector<HTMLElement>('[role="dialog"]')!;
    const heading = document.querySelector<HTMLElement>("#profile-settings-title")!;
    const input = document.querySelector<HTMLInputElement>("#profile-study-start")!;
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(document.activeElement).toBe(heading);
    expect(document.querySelector("#profile-deck-sort")).not.toBeNull();

    await changeInput(input, "2021-03-01");
    const firstControl = dialog.querySelector<HTMLButtonElement>(".profile-icon-button")!;
    firstControl.focus();
    await act(async () => dialog.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", shiftKey: true, bubbles: true })));
    expect(document.activeElement).toBe(button("Сохранить"));

    await changeInput(input, "2099-01-01");
    await act(async () => button("Сохранить").click());
    expect(document.body.textContent).toContain("Дата начала не может быть в будущем");
    expect(saveMock).not.toHaveBeenCalled();

    await act(async () => dialog.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
    await act(async () => new Promise((resolve) => window.setTimeout(resolve, 0)));
    expect(document.querySelector('[role="dialog"]')).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });

  it("saves the date and learning-area order in one existing profile request", async () => {
    const changed = {
      ...mockReport.profile!,
      preferences: { customStudyStartedOn: "2021-03-01", deckOverviewSort: "reviews" as const },
      studyHistory: { ...mockReport.profile!.studyHistory, customStartedOn: "2021-03-01", displayedStartedOn: "2021-03-01" },
    };
    saveMock.mockResolvedValue({ ok: true, profile: changed });
    const onUpdated = vi.fn();
    await act(async () => root.render(<ProfilePage report={mockReport} onReportUpdated={onUpdated} />));
    await act(async () => button("Настроить профиль").click());
    await changeInput(document.querySelector<HTMLInputElement>("#profile-study-start")!, "2021-03-01");
    await changeSelect(document.querySelector<HTMLSelectElement>("#profile-deck-sort")!, "reviews");
    await act(async () => {
      button("Сохранить").click();
      await Promise.resolve();
    });

    expect(saveMock).toHaveBeenCalledTimes(1);
    expect(saveMock).toHaveBeenCalledWith({ customStudyStartedOn: "2021-03-01", deckOverviewSort: "reviews" });
    expect(onUpdated).toHaveBeenCalledWith(expect.objectContaining({ profile: changed }));
  });

  it("makes reset an explicit draft change and persists null only after Save", async () => {
    const current = {
      ...mockReport.profile!,
      preferences: { ...mockReport.profile!.preferences, customStudyStartedOn: "2021-03-01" },
      studyHistory: { ...mockReport.profile!.studyHistory, customStartedOn: "2021-03-01", displayedStartedOn: "2021-03-01" },
    };
    saveMock.mockResolvedValue({ ok: true, profile: { ...current, preferences: { ...current.preferences, customStudyStartedOn: null } } });
    await act(async () => root.render(<ProfilePage report={withProfile(current)} onReportUpdated={vi.fn()} />));
    await act(async () => button("Настроить профиль").click());
    await act(async () => button("Сбросить к найденной дате").click());
    expect(document.querySelector<HTMLInputElement>("#profile-study-start")!.value).toBe("");
    expect(saveMock).not.toHaveBeenCalled();
    await act(async () => {
      button("Сохранить").click();
      await Promise.resolve();
    });
    expect(saveMock).toHaveBeenCalledWith({ customStudyStartedOn: null, deckOverviewSort: "name" });
  });

  it("prevents duplicate saves and recovers in place after a failed request", async () => {
    let resolveRequest: ((value: { ok: false }) => void) | undefined;
    saveMock.mockImplementationOnce(() => new Promise((resolve) => { resolveRequest = resolve; }));
    await act(async () => root.render(<ProfilePage report={mockReport} />));
    await act(async () => button("Настроить профиль").click());
    await changeSelect(document.querySelector<HTMLSelectElement>("#profile-deck-sort")!, "active_days");
    const save = button("Сохранить");
    await act(async () => {
      save.click();
      save.click();
    });
    expect(saveMock).toHaveBeenCalledTimes(1);
    expect(document.querySelector<HTMLButtonElement>(".profile-dialog .profile-button--primary")!.disabled).toBe(true);

    await act(async () => {
      resolveRequest?.({ ok: false });
      await Promise.resolve();
    });
    expect(document.querySelector('[role="dialog"]')).not.toBeNull();
    expect(document.body.textContent).toContain("Не удалось сохранить настройки профиля");

    saveMock.mockResolvedValueOnce({ ok: true, profile: { ...mockReport.profile!, preferences: { ...mockReport.profile!.preferences, deckOverviewSort: "active_days" } } });
    await act(async () => {
      button("Сохранить").click();
      await Promise.resolve();
    });
    expect(saveMock).toHaveBeenCalledTimes(2);
  });

  it("does not discard dirty settings through a backdrop click", async () => {
    await act(async () => root.render(<ProfilePage report={mockReport} />));
    await act(async () => button("Настроить профиль").click());
    await changeSelect(document.querySelector<HTMLSelectElement>("#profile-deck-sort")!, "reviews");
    const backdrop = document.querySelector<HTMLElement>(".profile-dialog-backdrop")!;
    await act(async () => backdrop.dispatchEvent(new MouseEvent("mousedown", { bubbles: true })));
    expect(document.querySelector('[role="dialog"]')).not.toBeNull();
  });

  it("renders the production composition in English", async () => {
    await i18n.changeLanguage("en");
    const markup = renderToStaticMarkup(<ProfilePage report={mockReport} />);
    expect(markup).toContain("What you study");
    expect(markup).toContain("Your history in numbers");
    expect(markup).toContain("Activity history");
    expect(markup).toContain("Profile settings");
  });

  function button(text: string): HTMLButtonElement {
    const found = Array.from(document.querySelectorAll("button")).find((item) => item.textContent?.includes(text));
    if (!found) throw new Error(`Button not found: ${text}`);
    return found;
  }
});

function withProfile(profile: ProfileModel): StudyReport {
  return { ...mockReport, profile };
}

async function changeInput(input: HTMLInputElement, value: string) {
  await act(async () => {
    setNativeValue(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

async function changeSelect(select: HTMLSelectElement, value: string) {
  await act(async () => {
    select.value = value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function setNativeValue(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  setter?.call(input, value);
}
