import { describe, expect, it } from "vitest";
import { resources } from ".";

function leafKeys(value: unknown, prefix = ""): string[] {
  if (typeof value === "string") return [prefix];
  if (Array.isArray(value)) return value.flatMap((item, index) => leafKeys(item, `${prefix}.${index}`));
  if (!value || typeof value !== "object") return [];
  return Object.entries(value).flatMap(([key, item]) => leafKeys(item, prefix ? `${prefix}.${key}` : key));
}

describe("localization resources", () => {
  it("keeps Russian and English resource keys in exact parity", () => {
    expect(leafKeys(resources.en).sort()).toEqual(leafKeys(resources.ru).sort());
  });

  it("contains no empty translated values", () => {
    for (const language of [resources.ru, resources.en]) {
      const values = leafKeys(language).map((key) => key.split(".").reduce<unknown>((value, part) => Array.isArray(value) ? value[Number(part)] : (value as Record<string, unknown>)[part], language));
      expect(values.every((value) => typeof value === "string" && value.trim().length > 0)).toBe(true);
    }
  });
});
