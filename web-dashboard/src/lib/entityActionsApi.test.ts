// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import { EntityActionApiError, runCardEntityAction, runNoteEntityAction } from "./entityActionsApi";

const response = {
  schemaVersion: 1,
  entityType: "cards",
  action: "suspend",
  requestedCount: 2,
  affectedCount: 1,
  unchangedCount: 1,
  undoable: true,
  resultCode: "cards.suspended",
  args: {},
  requestId: "cards-1",
};

afterEach(() => vi.unstubAllGlobals());

describe("entity actions API", () => {
  it("posts card and note actions to separate token-protected endpoints", async () => {
    window.history.replaceState(null, "", "/?token=entity-token#/search");
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => new Response(JSON.stringify({
      ok: true,
      response: String(input).includes("/cards/") ? response : {
        ...response,
        entityType: "notes",
        action: "add_tags",
        resultCode: "notes.tags_added",
      },
    }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await runCardEntityAction({ action: "suspend", cardIds: ["1", "2"], requestId: "cards-1" });
    await runNoteEntityAction({ action: "add_tags", noteIds: ["10"], tags: ["Japanese::Grammar"], requestId: "notes-1" });
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/entities/cards/actions?token=entity-token");
    expect(fetchMock.mock.calls[1]?.[0]).toBe("/api/entities/notes/actions?token=entity-token");
    expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body))).toEqual({
      action: "add_tags", noteIds: ["10"], tags: ["Japanese::Grammar"], requestId: "notes-1",
    });
  });

  it("rejects malformed successful envelopes", async () => {
    window.history.replaceState(null, "", "/?token=x#/search");
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      ok: true,
      response: { ...response, affectedCount: 2, unchangedCount: 2 },
    }), { status: 200 })));
    await expect(runCardEntityAction({ action: "suspend", cardIds: ["1", "2"] })).rejects.toMatchObject({
      code: "invalid_entity_action_response",
    });
  });

  it("preserves typed backend errors without leaking an invalid payload", async () => {
    window.history.replaceState(null, "", "/?token=x#/search");
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      ok: false,
      error: "entity_action_stale",
      message: "Selection changed.",
      fieldErrors: { cardIds: "Refresh." },
    }), { status: 409 })));
    const promise = runCardEntityAction({ action: "clear_flag", cardIds: ["1"] });
    await expect(promise).rejects.toBeInstanceOf(EntityActionApiError);
    await expect(promise).rejects.toMatchObject({ code: "entity_action_stale", status: 409, fieldErrors: { cardIds: "Refresh." } });
  });
});
