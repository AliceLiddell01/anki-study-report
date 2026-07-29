import type { KeyboardEvent } from "react";

export type InspectionEditorMode = "basic" | "advanced";

interface EditorModeTabsProps {
  mode: InspectionEditorMode;
  label: string;
  basicLabel: string;
  advancedLabel: string;
  advancedErrorCount: number;
  changed: boolean;
  changedLabel: string;
  advancedErrorsLabel: (count: number) => string;
  onChange: (mode: InspectionEditorMode) => void;
}

const modes: InspectionEditorMode[] = ["basic", "advanced"];

export default function EditorModeTabs({
  mode,
  label,
  basicLabel,
  advancedLabel,
  advancedErrorCount,
  changed,
  changedLabel,
  advancedErrorsLabel,
  onChange,
}: EditorModeTabsProps) {
  const selectAndFocus = (nextMode: InspectionEditorMode) => {
    onChange(nextMode);
    window.requestAnimationFrame(() => document.getElementById(`inspection-mode-${nextMode}`)?.focus());
  };

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    let nextMode: InspectionEditorMode | null = null;
    const currentIndex = modes.indexOf(mode);
    if (event.key === "ArrowRight") nextMode = modes[(currentIndex + 1) % modes.length];
    if (event.key === "ArrowLeft") nextMode = modes[(currentIndex - 1 + modes.length) % modes.length];
    if (event.key === "Home") nextMode = modes[0];
    if (event.key === "End") nextMode = modes[modes.length - 1];
    if (!nextMode) return;
    event.preventDefault();
    selectAndFocus(nextMode);
  };

  return (
    <div className="inspection-mode-switch" role="tablist" aria-label={label}>
      <button
        id="inspection-mode-basic"
        type="button"
        role="tab"
        aria-selected={mode === "basic"}
        aria-controls="inspection-basic-mode-panel"
        tabIndex={mode === "basic" ? 0 : -1}
        className={mode === "basic" ? "is-active" : ""}
        onClick={() => onChange("basic")}
        onKeyDown={onKeyDown}
      >
        {basicLabel}
      </button>
      <button
        id="inspection-mode-advanced"
        type="button"
        role="tab"
        aria-selected={mode === "advanced"}
        aria-controls="inspection-advanced-panel"
        tabIndex={mode === "advanced" ? 0 : -1}
        className={mode === "advanced" ? "is-active" : ""}
        onClick={() => onChange("advanced")}
        onKeyDown={onKeyDown}
      >
        <span>{advancedLabel}</span>
        {advancedErrorCount ? (
          <span className="inspection-mode-error-count" aria-label={advancedErrorsLabel(advancedErrorCount)}>
            {advancedErrorCount}
          </span>
        ) : null}
        {changed ? <span className="inspection-mode-dirty">{changedLabel}</span> : null}
      </button>
    </div>
  );
}
