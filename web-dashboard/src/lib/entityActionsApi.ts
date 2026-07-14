import { dashboardToken } from "./actionsApi";
import type {
  CardEntityActionRequest,
  EntityActionResponse,
  EntityActionResultCode,
  NoteEntityActionRequest,
} from "../types/entityActions";

export class EntityActionApiError extends Error {
  code: string;
  status: number;
  fieldErrors?: Record<string, string>;

  constructor(message: string, options: { code: string; status: number; fieldErrors?: Record<string, string> }) {
    super(message);
    this.name = "EntityActionApiError";
    this.code = options.code;
    this.status = options.status;
    this.fieldErrors = options.fieldErrors;
  }
}

export function runCardEntityAction(request: CardEntityActionRequest, signal?: AbortSignal) {
  return runEntityAction("cards", request, signal);
}

export function runNoteEntityAction(request: NoteEntityActionRequest, signal?: AbortSignal) {
  return runEntityAction("notes", request, signal);
}

async function runEntityAction(
  entityType: "cards" | "notes",
  request: CardEntityActionRequest | NoteEntityActionRequest,
  signal?: AbortSignal,
): Promise<EntityActionResponse> {
  const token = dashboardToken();
  const response = await fetch(`/api/entities/${entityType}/actions?token=${encodeURIComponent(token)}`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });
  const data = await safeJson(response);
  if (!response.ok) throw errorFromResponse(data, response.status);
  const envelope = record(data);
  if (envelope.ok !== true) throw errorFromResponse(data, response.status);
  return normalizeResponse(envelope.response, entityType);
}

function normalizeResponse(value: unknown, expectedType: "cards" | "notes"): EntityActionResponse {
  const data = record(value);
  const keys = Object.keys(data);
  const requiredKeys = ["schemaVersion", "entityType", "action", "requestedCount", "affectedCount", "unchangedCount", "undoable", "resultCode", "args"];
  const exactShape = requiredKeys.every((key) => keys.includes(key)) &&
    keys.every((key) => requiredKeys.includes(key) || key === "requestId");
  const allowedActions = expectedType === "cards"
    ? ["suspend", "unsuspend", "set_flag", "clear_flag", "bury", "unbury", "move_to_deck"]
    : ["add_tags", "remove_tags"];
  const requestedCount = count(data.requestedCount);
  const affectedCount = count(data.affectedCount);
  const unchangedCount = count(data.unchangedCount);
  const action = typeof data.action === "string" && allowedActions.includes(data.action) ? data.action : undefined;
  const expectedResultCode = action ? resultCodeForAction(action) : undefined;
  const resultCodeValid = typeof data.resultCode === "string" && (
    affectedCount === 0
      ? data.resultCode === "action.no_changes"
      : data.resultCode === expectedResultCode
  );
  if (
    !exactShape || data.schemaVersion !== 1 || data.entityType !== expectedType || !action ||
    requestedCount === undefined || affectedCount === undefined || unchangedCount === undefined ||
    affectedCount + unchangedCount !== requestedCount || typeof data.undoable !== "boolean" ||
    data.undoable !== (affectedCount > 0) || !resultCodeValid ||
    !isActionArgs(data.args, action) || !optionalRequestId(data.requestId)
  ) {
    throw new EntityActionApiError("Dashboard received an invalid entity action response.", {
      code: "invalid_entity_action_response",
      status: 0,
    });
  }
  return data as EntityActionResponse;
}

function resultCodeForAction(action: string): EntityActionResultCode | undefined {
  return ({
    suspend: "cards.suspended",
    unsuspend: "cards.unsuspended",
    set_flag: "cards.flag_set",
    clear_flag: "cards.flag_cleared",
    bury: "cards.buried",
    unbury: "cards.unburied",
    move_to_deck: "cards.moved",
    add_tags: "notes.tags_added",
    remove_tags: "notes.tags_removed",
  } as Record<string, EntityActionResultCode>)[action];
}

function isActionArgs(value: unknown, action: string): value is Record<string, number | string> {
  const args = record(value);
  const keys = Object.keys(args);
  if (action === "set_flag") {
    return keys.length === 1 && keys[0] === "flag" && integerInRange(args.flag, 1, 7);
  }
  if (action === "move_to_deck") {
    return keys.length === 1 && keys[0] === "deckId" && positiveSafeInteger(args.deckId);
  }
  if (action === "add_tags" || action === "remove_tags") {
    return keys.length === 1 && keys[0] === "tagCount" && integerInRange(args.tagCount, 1, 20);
  }
  return keys.length === 0;
}

function errorFromResponse(value: unknown, status: number): EntityActionApiError {
  const data = record(value);
  const fieldErrors = isStringRecord(data.fieldErrors) ? data.fieldErrors : undefined;
  return new EntityActionApiError(
    typeof data.message === "string" && data.message ? data.message : "The Anki action failed.",
    { code: typeof data.error === "string" ? data.error : "entity_action_failed", status, fieldErrors },
  );
}

async function safeJson(response: Response): Promise<unknown> {
  try { return await response.json(); } catch { return null; }
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function count(value: unknown): number | undefined {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0 ? value : undefined;
}

function integerInRange(value: unknown, minimum: number, maximum: number): boolean {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= minimum && value <= maximum;
}

function positiveSafeInteger(value: unknown): boolean {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0;
}

function optionalRequestId(value: unknown): boolean {
  return value === undefined || (typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value));
}

function isStringRecord(value: unknown): value is Record<string, string> {
  return value !== null && typeof value === "object" && !Array.isArray(value) &&
    Object.values(value).every((item) => typeof item === "string");
}
