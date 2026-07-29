export type CardDisplayFormatterStoredState = "enabled" | "disabled";
export type CardDisplayFormatterInputSource = "browser_question" | "reviewer_front";
export type CardDisplayFormatterTextMode = "preserve" | "omit";
export type CardDisplayFormatterMediaMode = "omit" | "filename" | "stem" | "marker";
export type CardDisplayFormatterStoreStatus = "empty" | "available" | "corrupt" | "future_schema" | "unavailable";

export interface CardDisplayFormatter {
  noteTypeId: string;
  noteTypeName: string;
  templateOrdinal: number | null;
  templateName: string | null;
  storedState: CardDisplayFormatterStoredState;
  inputSource: CardDisplayFormatterInputSource;
  textMode: CardDisplayFormatterTextMode;
  imageMode: CardDisplayFormatterMediaMode;
  audioMode: CardDisplayFormatterMediaMode;
  maxLines: number;
  lineSeparator: string;
  maxCharacters: number;
  updatedAt: string;
}

export interface CardDisplayFormatterStoreSnapshot {
  schemaVersion: 1;
  status: CardDisplayFormatterStoreStatus;
  revision: number;
  formatters: CardDisplayFormatter[];
  errorCode: string | null;
  quarantined: boolean;
}

export type CardDisplayFormatterQueryRequest = { schemaVersion: 1 };
export type CardDisplayFormatterValidateRequest = { schemaVersion: 1; formatter: CardDisplayFormatter };
export interface CardDisplayFormatterValidateResponse {
  schemaVersion: 1;
  valid: true;
  formatter: CardDisplayFormatter;
  fieldErrors: Record<string, string>;
}

export type CardDisplayFormatterUpdateRequest =
  | { schemaVersion: 1; action: "save"; expectedRevision: number; formatter: CardDisplayFormatter }
  | { schemaVersion: 1; action: "delete"; expectedRevision: number; noteTypeId: string; templateOrdinal: number | null };

export interface CardDisplayFormatterUpdateResponse {
  schemaVersion: 1;
  action: "save" | "delete";
  store: CardDisplayFormatterStoreSnapshot;
  formatter: CardDisplayFormatter | null;
}
