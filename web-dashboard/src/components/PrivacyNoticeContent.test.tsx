// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import i18n from "../i18n";
import PrivacyNoticeContent, { PRIVACY_NOTICE_VERSION } from "./PrivacyNoticeContent";

describe("production privacy notice", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it("renders the exact English production storage and processor contract", async () => {
    await i18n.changeLanguage("en");
    await act(async () => root.render(<PrivacyNoticeContent />));
    expect(PRIVACY_NOTICE_VERSION).toBe("2026-07-15-production");
    expect(container.textContent).toContain("AliceLiddell01");
    expect(container.textContent).toContain("Cloudflare D1 created with EU jurisdiction");
    expect(container.textContent).toContain("60 days");
    expect(container.textContent).toContain("24 months");
    expect(container.textContent).toContain("R2 and independent 30-day backups are not used");
    expect(container.textContent).toContain("not synchronized through AnkiWeb Sync");
  });

  it("renders the corresponding Russian production contract", async () => {
    await i18n.changeLanguage("ru");
    await act(async () => root.render(<PrivacyNoticeContent />));
    expect(container.textContent).toContain("Версия Privacy Notice: 2026-07-15-production");
    expect(container.textContent).toContain("EU jurisdiction");
    expect(container.textContent).toContain("R2 и независимые 30-дневные бэкапы не используются");
    expect(container.textContent).toContain("не синхронизируется через AnkiWeb Sync");
  });
});
