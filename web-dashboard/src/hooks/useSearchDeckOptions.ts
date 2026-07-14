import { useEffect, useMemo, useState } from "react";
import { loadPublicSettings } from "../lib/settingsApi";
import type { StudyReport } from "../types/report";
import type { DeckOption } from "../types/settings";

export function useSearchDeckOptions(report: StudyReport | null): DeckOption[] {
  const fallback = useMemo(() => deckOptionsFromReport(report), [report]);
  const [loadedOptions, setLoadedOptions] = useState<DeckOption[] | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    loadPublicSettings(controller.signal)
      .then((response) => {
        if (!controller.signal.aborted) {
          setLoadedOptions(response.deckOptions);
        }
      })
      .catch((error: Error) => {
        if (error.name !== "AbortError") {
          // Search remains usable with the report-backed fallback.
        }
      });
    return () => controller.abort();
  }, []);

  return loadedOptions ?? fallback;
}

export function deckOptionsFromReport(report: StudyReport | null): DeckOption[] {
  const options = new Map<number, string>();
  if (report?.deckHub) {
    Object.values(report.deckHub.nodes).forEach((node) => {
      options.set(Number(node.deckId), node.fullName);
    });
  }
  (report?.decks ?? []).forEach((deck) => {
    options.set(Number(deck.id), deck.name);
  });
  return [...options.entries()]
    .filter(([id, name]) => Number.isInteger(id) && id > 0 && name.trim().length > 0)
    .map(([id, name]) => ({ id, name }))
    .sort((left, right) => left.name.localeCompare(right.name));
}
