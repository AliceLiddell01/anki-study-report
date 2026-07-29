// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  CardDisplayFormattersApiError,
  fetchCardDisplayFormatters,
  parseCardDisplayFormatterStoreSnapshot,
  parseCardDisplayFormatterUpdateResponse,
  parseCardDisplayFormatterValidateResponse,
  updateCardDisplayFormatter,
  validateCardDisplayFormatter,
} from "./cardDisplayFormattersApi";
import type { CardDisplayFormatter } from "../types/cardDisplayFormatters";

const formatter: CardDisplayFormatter = {
  noteTypeId: "123",
  noteTypeName: "Japanese Vocabulary",
  templateOrdinal: null,
  templateName: null,
  storedState: "enabled",
  inputSource: "reviewer_front",
  textMode: "preserve",
  imageMode: "stem",
  audioMode: "omit",
  maxLines: 1,
  lineSeparator: " ",
  maxCharacters: 240,
  updatedAt: "2026-07-19T00:00:00Z",
};
const snapshot = {
  schemaVersion: 1 as const,
  status: "available" as const,
  revision: 1,
  formatters: [formatter],
  errorCode: null,
  quarantined: false,
};

afterEach(() => vi.unstubAllGlobals());

describe("card display formatter API", () => {
  it("parses strict query, validate, and update responses", () => {
    expect(parseCardDisplayFormatterStoreSnapshot(snapshot)).toEqual(snapshot);
    expect(parseCardDisplayFormatterValidateResponse({
      schemaVersion: 1, valid: true, formatter, fieldErrors: {},
    })).toEqual({ schemaVersion: 1, valid: true, formatter, fieldErrors: {} });
    expect(parseCardDisplayFormatterUpdateResponse({
      schemaVersion: 1, action: "save", store: snapshot, formatter,
    })).toEqual({ schemaVersion: 1, action: "save", store: snapshot, formatter });
    expect(() => parseCardDisplayFormatterUpdateResponse({
      schemaVersion: 1, action: "delete", store: snapshot, formatter,
    })).toThrowError(CardDisplayFormattersApiError);
    expect(() => parseCardDisplayFormatterUpdateResponse({
      schemaVersion: 1, action: "save", store: { ...snapshot, formatters: [{ ...formatter, maxLines: 2 }] }, formatter,
    })).toThrowError(CardDisplayFormattersApiError);
  });

  it("fails closed on schema, unknown fields, duplicate keys, invalid enums, limits, and nullable template mismatch", () => {
    const invalid = [
      { ...snapshot, schemaVersion: 2 },
      { ...snapshot, extra: true },
      { ...snapshot, revision: true },
      { ...snapshot, status: "other" },
      { ...snapshot, formatters: [formatter, formatter] },
      { ...snapshot, formatters: [{ ...formatter, imageMode: "regex" }] },
      { ...snapshot, formatters: [{ ...formatter, maxCharacters: 241 }] },
      { ...snapshot, formatters: [{ ...formatter, lineSeparator: "\n" }] },
      { ...snapshot, formatters: [{ ...formatter, templateOrdinal: 0, templateName: null }] },
      { ...snapshot, formatters: [{ ...formatter, noteTypeId: "01" }] },
      { ...snapshot, formatters: [{ ...formatter, updatedAt: "2026-02-30T00:00:00Z" }] },
      { ...snapshot, status: "empty", formatters: [formatter] },
    ];
    for (const value of invalid) {
      expect(() => parseCardDisplayFormatterStoreSnapshot(value)).toThrowError(CardDisplayFormattersApiError);
    }
  });

  it("posts exact JSON bodies to token-protected endpoints", async () => {
    window.history.replaceState(null, "", "/?token=secret#/settings");
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(
      JSON.stringify({ ok: true, response: snapshot }), { status: 200 },
    ));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchCardDisplayFormatters({ schemaVersion: 1 })).resolves.toEqual(snapshot);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/card-display-formatters/query?token=secret");
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({ schemaVersion: 1 });

    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async () => new Response(JSON.stringify({
      ok: true, response: { schemaVersion: 1, valid: true, formatter, fieldErrors: {} },
    }), { status: 200 })));
    await expect(validateCardDisplayFormatter({ schemaVersion: 1, formatter })).resolves.toMatchObject({ valid: true });

    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async () => new Response(JSON.stringify({
      ok: true, response: { schemaVersion: 1, action: "save", store: snapshot, formatter },
    }), { status: 200 })));
    const save = { schemaVersion: 1 as const, action: "save" as const, expectedRevision: 0, formatter };
    await expect(updateCardDisplayFormatter(save)).resolves.toMatchObject({ action: "save" });
  });

  it("rejects malformed error envelopes and exposes bounded conflict metadata", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async () => new Response(JSON.stringify({
      ok: false,
      error: "card_display_formatter_revision_conflict",
      currentRevision: 7,
    }), { status: 409 })));
    await expect(updateCardDisplayFormatter({
      schemaVersion: 1, action: "delete", expectedRevision: 1,
      noteTypeId: "123", templateOrdinal: null,
    })).rejects.toMatchObject({ code: "card_display_formatter_revision_conflict", currentRevision: 7 });

    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async () => new Response(JSON.stringify({
      ok: false, error: { private: "path" }, path: "C:/secret",
    }), { status: 500 })));
    await expect(fetchCardDisplayFormatters({ schemaVersion: 1 })).rejects.toMatchObject({
      code: "card_display_formatters_failed",
      fieldErrors: undefined,
      currentRevision: undefined,
    });

    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async () => new Response(JSON.stringify({
      ok: false, error: "card_display_formatters_failed", unexpected: "private",
    }), { status: 500 })));
    await expect(fetchCardDisplayFormatters({ schemaVersion: 1 })).rejects.toMatchObject({
      code: "card_display_formatters_failed",
    });
  });
});
