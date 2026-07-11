import type { DeckHubModel, DeckHubNode } from "../types/report";

export type DeckHubFilter = "all" | "attention" | "danger" | "insufficient";
export type DeckHubSort = "name" | "status" | "reviews" | "success";

export interface VisibleDeckRow {
  node: DeckHubNode;
  level: number;
  contextOnly: boolean;
}

const severity: Record<DeckHubNode["aggregateHealth"], number> = {
  danger: 4,
  warning: 3,
  neutral: 2,
  good: 1,
};

export function visibleDeckRows(
  hub: DeckHubModel,
  expandedIds: ReadonlySet<number>,
  query: string,
  filter: DeckHubFilter,
  sort: DeckHubSort,
): VisibleDeckRow[] {
  const nodes = validNodes(hub);
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const activeTransform = Boolean(normalizedQuery) || filter !== "all";
  const matched = new Set<number>();
  const included = new Set<number>();

  for (const node of nodes.values()) {
    if (node.structuralOnly) continue;
    const queryMatches = !normalizedQuery || `${node.fullName}\n${node.shortName}`.toLocaleLowerCase().includes(normalizedQuery);
    if (queryMatches && nodeMatchesFilter(node, filter)) {
      matched.add(node.deckId);
      includeAncestors(node, nodes, included);
      included.add(node.deckId);
    }
  }

  const rows: VisibleDeckRow[] = [];
  const visit = (deckId: number, level: number) => {
    const node = nodes.get(deckId);
    if (!node || (activeTransform && !included.has(deckId))) return;
    rows.push({ node, level, contextOnly: activeTransform && !matched.has(deckId) });
    const expanded = activeTransform ? included.has(deckId) : expandedIds.has(deckId);
    if (!expanded) return;
    for (const childId of sortedChildren(node, nodes, sort)) visit(childId, level + 1);
  };
  for (const rootId of sortedIds(hub.rootIds, nodes, sort)) visit(rootId, 1);
  return rows;
}

export function sortedRootIds(hub: DeckHubModel, sort: DeckHubSort): number[] {
  return sortedIds(hub.rootIds, validNodes(hub), sort);
}

export function exactDeckMatch(hub: DeckHubModel, query: string): number | null {
  const normalized = query.trim().toLocaleLowerCase();
  if (!normalized) return null;
  const matches = [...validNodes(hub).values()]
    .filter((node) => !node.structuralOnly && (node.fullName.toLocaleLowerCase() === normalized || node.shortName.toLocaleLowerCase() === normalized))
    .sort((a, b) => compareNodes(a, b, "name"));
  return matches[0]?.deckId ?? null;
}

export function nearestVisibleSelection(
  hub: DeckHubModel,
  visibleIds: ReadonlySet<number>,
  selectedId: number | null,
): number | null {
  if (selectedId !== null && visibleIds.has(selectedId)) return selectedId;
  const nodes = validNodes(hub);
  let current = selectedId === null ? null : nodes.get(selectedId)?.parentId ?? null;
  const seen = new Set<number>();
  while (current !== null && !seen.has(current)) {
    if (visibleIds.has(current)) return current;
    seen.add(current);
    current = nodes.get(current)?.parentId ?? null;
  }
  return visibleIds.values().next().value ?? null;
}

export function nodeMatchesFilter(node: DeckHubNode, filter: DeckHubFilter): boolean {
  if (filter === "attention") return node.aggregateHealth === "warning" || node.aggregateHealth === "danger";
  if (filter === "danger") return node.aggregateHealth === "danger";
  if (filter === "insufficient") return node.dataConfidence !== "sufficient";
  return true;
}

function validNodes(hub: DeckHubModel): Map<number, DeckHubNode> {
  const nodes = new Map<number, DeckHubNode>();
  for (const value of Object.values(hub.nodes ?? {})) {
    if (!value || !Number.isFinite(value.deckId) || typeof value.fullName !== "string") continue;
    nodes.set(value.deckId, value);
  }
  return nodes;
}

function includeAncestors(node: DeckHubNode, nodes: Map<number, DeckHubNode>, included: Set<number>) {
  let parentId = node.parentId;
  const seen = new Set<number>();
  while (parentId !== null && !seen.has(parentId)) {
    const parent = nodes.get(parentId);
    if (!parent) break;
    included.add(parentId);
    seen.add(parentId);
    parentId = parent.parentId;
  }
}

function sortedChildren(node: DeckHubNode, nodes: Map<number, DeckHubNode>, sort: DeckHubSort) {
  return sortedIds(node.childIds ?? [], nodes, sort);
}

function sortedIds(ids: number[], nodes: Map<number, DeckHubNode>, sort: DeckHubSort) {
  return [...new Set(ids)].filter((id) => nodes.has(id)).sort((left, right) => compareNodes(nodes.get(left)!, nodes.get(right)!, sort));
}

function compareNodes(left: DeckHubNode, right: DeckHubNode, sort: DeckHubSort): number {
  let result = 0;
  if (sort === "status") result = severity[right.aggregateHealth] - severity[left.aggregateHealth];
  if (sort === "reviews") result = right.subtreeMetrics.reviews - left.subtreeMetrics.reviews;
  if (sort === "success") {
    const leftRate = left.subtreeMetrics.passRate;
    const rightRate = right.subtreeMetrics.passRate;
    if (leftRate === null && rightRate !== null) result = 1;
    else if (leftRate !== null && rightRate === null) result = -1;
    else result = (leftRate ?? 0) - (rightRate ?? 0);
  }
  if (result !== 0) return result;
  const byName = left.shortName.localeCompare(right.shortName, undefined, { sensitivity: "base", numeric: false });
  if (byName !== 0) return byName;
  const byFullName = left.fullName.localeCompare(right.fullName, undefined, { sensitivity: "base", numeric: false });
  return byFullName || left.deckId - right.deckId;
}
