// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { defaultPublicSettings } from "../lib/settingsApi";
import type { StudyReport } from "../types/report";
import { deckOptionsFromReport, useSearchDeckOptions } from "./useSearchDeckOptions";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useSearchDeckOptions", () => {
  it("uses the scoped report only as a fallback", () => {
    const report = {
      deckHub: {
        nodes: {
          "10": { deckId: 10, fullName: "Scoped::Deck" },
        },
      },
      decks: [{ id: 11, name: "Legacy Deck" }],
    } as unknown as StudyReport;
    expect(deckOptionsFromReport(report)).toEqual([
      { id: 11, name: "Legacy Deck" },
      { id: 10, name: "Scoped::Deck" },
    ]);
  });

  it("replaces the scoped fallback with the all-collection settings catalog", async () => {
    window.history.replaceState(null, "", "/?token=settings-token#/search");
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      settings: defaultPublicSettings,
      deckOptions: [
        { id: 10, name: "Scoped::Deck" },
        { id: 20, name: "Outside Scope" },
      ],
    }), { status: 200, headers: { "Content-Type": "application/json" } })));

    const report = {
      deckHub: {
        nodes: {
          "10": { deckId: 10, fullName: "Scoped::Deck" },
        },
      },
    } as unknown as StudyReport;

    const { result } = renderHook(() => useSearchDeckOptions(report));
    await waitFor(() => expect(result.current).toEqual([
      { id: 10, name: "Scoped::Deck" },
      { id: 20, name: "Outside Scope" },
    ]));
  });
});
