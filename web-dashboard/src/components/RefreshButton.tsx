import { RefreshCw } from "lucide-react";

interface RefreshButtonProps {
  label: string;
  pending: boolean;
  onClick: () => void;
  className?: string;
}

export default function RefreshButton({ label, pending, onClick, className = "secondary-button" }: RefreshButtonProps) {
  return (
    <button type="button" className={`${className} shared-refresh-button`} onClick={onClick} disabled={pending} aria-busy={pending}>
      <span className={`shared-refresh-icon${pending ? " is-pending" : ""}`} aria-hidden="true"><RefreshCw size={16} /></span>
      <span>{label}</span>
    </button>
  );
}
