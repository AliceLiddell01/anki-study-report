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
  const allowedCodes: EntityActionResultCode[] = [
    "cards.suspended", "cards.unsuspended", "cards.flag_set", "cards.flag_cleared", "cards.buried", "cards.unburied", "cards.moved",
    "notes.tags_added", "notes.tags_removed", "action.no_changes",
  ];
  const allowedActions = expectedType === "cards"
    ? ["suspend", "unsuspend", "set_flag", "clear_flag", "bury", "unbury", "move_to_deck"]
    : ["add_tags", "remove_tags"];
  const requestedCount = count(data.requestedCount);
  const affectedCount = count(data.affectedCount);
  const unchangedCount = count(data.unchangedCount);
  if (
    !exactShape || data.schemaVersion !== 1 || data.entityType !== expectedType ||
    typeof data.action !== "string" || !allowedActions.includes(data.action) ||
    requestedCount === undefined || affectedCount === undefined || unchangedCount === undefined ||
    affectedCount + unchangedCount !== requestedCount || typeof data.undoable !== "boolean" ||
    typeof data.resultCode !== "string" || !allowedCodes.includes(data.resultCode as EntityActionResultCode) ||
    !isSafeArgs(data.args) || (data.requestId !== undefined && typeof data.requestId !== "string")
  ) {
    throw new EntityActionApiError("Dashboard received an invalid entity action response.", {
      code: "invalid_entity_action_response",
      status: 0,
    });
  }
  return data as EntityActionResponse;
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
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : undefined;
}

function isSafeArgs(value: unknown): value is Record<string, number | string> {
  return value !== null && typeof value === "object" && !Array.isArray(value) &&
    Object.values(value).every((item) => typeof item === "string" || (typeof item === "number" && Number.isFinite(item)));
}

function isStringRecord(value: unknown): value is Record<string, string> {
  return value !== null && typeof value === "object" && !Array.isArray(value) &&
    Object.values(value).every((item) => typeof item === "string");
}
