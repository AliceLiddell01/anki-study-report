export interface GenerationBoundOperation {
  operationId: number;
  itemId: string;
  cardId: string;
  queryGeneration: number;
}

export const MAX_INSPECT_CACHE_ENTRIES = 50;

export function canApplyOperationCompletion(
  operation: GenerationBoundOperation,
  currentQueryGeneration: number,
): boolean {
  return operation.queryGeneration === currentQueryGeneration;
}

export function inspectCacheKey(queryGeneration: number, cardId: string): string {
  return `${queryGeneration}:${cardId}`;
}

export function putBoundedInspectCache<T>(cache: Map<string, T>, key: string, value: T): void {
  cache.delete(key);
  cache.set(key, value);
  while (cache.size > MAX_INSPECT_CACHE_ENTRIES) {
    const oldest = cache.keys().next().value;
    if (typeof oldest !== "string") break;
    cache.delete(oldest);
  }
}
