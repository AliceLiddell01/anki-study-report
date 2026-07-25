import type { RenderedCardPreview } from "./report";

export type SearchMode = "cards" | "notes";
export type SearchSortDirection = "asc" | "desc";
export type SearchCardState = "new" | "learning" | "review" | "due" | "suspended" | "buried";
export type CardDisplaySource = "browser_question" | "reviewer_front" | "none";
export type CardDisplayStatus = "available" | "media_only" | "unavailable";

export interface CardDisplayIdentity {
  displayText: string;
  displaySource: CardDisplaySource;
  displayStatus: CardDisplayStatus;
  displayTruncated: boolean;
}

export type SearchFilter =
  | { type: "deck"; deckId: string }
  | { type: "note_type"; noteTypeId: string }
  | { type: "tag"; tag: string }
  | { type: "state"; state: SearchCardState }
  | { type: "flag"; flag: 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 };

export interface SearchQueryRequest {
  schemaVersion: 2;
  mode: SearchMode;
  query: string;
  filters: SearchFilter[];
  sort: { key: "entity_id"; direction: SearchSortDirection };
  page: number;
  pageSize: 25 | 50 | 100;
  requestId?: string;
}

export type SearchInspectRequest =
  | { schemaVersion: 2; mode: "cards"; cardId: string; noteId?: never; requestId?: string }
  | { schemaVersion: 2; mode: "notes"; noteId: string; cardId?: never; requestId?: string };

export interface SearchMetadataRequest {
  kind: "metadata";
  requestId?: string;
}

export interface SearchMetadataDeck {
  deckId: string;
  deckName: string;
  filtered: boolean;
}

export interface SearchMetadataNoteType {
  noteTypeId: string;
  noteTypeName: string;
}

export interface SearchMetadataResponse {
  schemaVersion: 1;
  kind: "metadata";
  decks: SearchMetadataDeck[];
  noteTypes: SearchMetadataNoteType[];
  decksTruncated: boolean;
  noteTypesTruncated: boolean;
  requestId?: string;
}

export interface SearchDeckSummary {
  deckId: string;
  deckName: string;
}

export interface SearchCardRow extends CardDisplayIdentity {
  cardId: string;
  noteId: string;
  deckId: string;
  deckName: string;
  noteTypeId: string;
  noteTypeName: string;
  templateOrdinal: number;
  templateName: string;
  state: SearchCardState;
  due: number;
  interval: number;
  repetitions: number;
  lapses: number;
  flag: number;
  tagSummary: string[];
}

export interface SearchNoteRow {
  noteId: string;
  noteTypeId: string;
  noteTypeName: string;
  primaryText: string;
  tagSummary: string[];
  cardCount: number;
  deckSummary: SearchDeckSummary[];
}

export interface SearchQueryResponse<M extends SearchMode = SearchMode> {
  schemaVersion: 2;
  mode: M;
  items: M extends "cards" ? SearchCardRow[] : SearchNoteRow[];
  page: number;
  pageSize: 25 | 50 | 100;
  pageCount: number;
  pageLimit: number;
  returnedCount: number;
  boundedTotal: number;
  hasNext: boolean;
  truncated: boolean;
  sort: { key: "entity_id"; direction: SearchSortDirection };
  requestId?: string;
}

export interface SearchCardDetails extends SearchCardRow {
  deck: SearchDeckSummary;
  noteType: { noteTypeId: string; noteTypeName: string };
  template: { ordinal: number; name: string };
  queue: number;
  tags: string[];
  renderedPreview: RenderedCardPreview;
}

export interface SearchNoteDetails extends SearchNoteRow {
  noteType: { noteTypeId: string; noteTypeName: string };
  fields: Array<{ name: string; value: string }>;
  tags: string[];
  cardReferences: Array<{ cardId: string; deckId: string; templateOrdinal: number }>;
  cardsTruncated: boolean;
  fieldsTruncated: boolean;
  deckSummaries: SearchDeckSummary[];
}

export interface SearchInspectResponse<M extends SearchMode = SearchMode> {
  schemaVersion: 2;
  mode: M;
  details: M extends "cards" ? SearchCardDetails : SearchNoteDetails;
  requestId?: string;
}
