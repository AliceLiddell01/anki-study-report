export type CardEntityAction = "suspend" | "unsuspend" | "set_flag" | "clear_flag" | "bury" | "unbury" | "move_to_deck";
export type NoteEntityAction = "add_tags" | "remove_tags";
export type EntityActionResultCode =
  | "cards.suspended"
  | "cards.unsuspended"
  | "cards.flag_set"
  | "cards.flag_cleared"
  | "cards.buried"
  | "cards.unburied"
  | "cards.moved"
  | "notes.tags_added"
  | "notes.tags_removed"
  | "action.no_changes";

export type EntityActionResponse = {
  schemaVersion: 1;
  entityType: "cards" | "notes";
  action: CardEntityAction | NoteEntityAction;
  requestedCount: number;
  affectedCount: number;
  unchangedCount: number;
  undoable: boolean;
  resultCode: EntityActionResultCode;
  args: Record<string, number | string>;
  requestId?: string;
};

export type CardEntityActionRequest = {
  action: CardEntityAction;
  cardIds: string[];
  flag?: number;
  deckId?: string;
  requestId?: string;
};

export type NoteEntityActionRequest = {
  action: NoteEntityAction;
  noteIds: string[];
  tags: string[];
  requestId?: string;
};
