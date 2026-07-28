import { forwardRef } from "react";
import { RefreshCw } from "lucide-react";

interface RefreshButtonProps {
  label: string;
  pending: boolean;
  onClick: () => void;
  className?: string;
}

const RefreshButton = forwardRef<HTMLButtonElement, RefreshButtonProps>(function RefreshButton(
  { label, pending, onClick, className = "secondary-button" },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      className={`${className} shared-refresh-button`}
      onClick={() => {
        if (!pending) onClick();
      }}
      aria-disabled={pending}
      aria-busy={pending}
      data-refresh-pending={pending ? "true" : "false"}
    >
      <span className={`shared-refresh-icon${pending ? " is-pending" : ""}`} aria-hidden="true"><RefreshCw size={16} /></span>
      <span>{label}</span>
    </button>
  );
});

export default RefreshButton;
