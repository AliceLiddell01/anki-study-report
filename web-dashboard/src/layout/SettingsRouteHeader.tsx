import { createContext, type ReactNode, useContext } from "react";
import { createPortal } from "react-dom";

const SettingsRouteHeaderTargetContext = createContext<HTMLElement | null>(null);

export function SettingsRouteHeaderTargetProvider({
  target,
  children,
}: {
  target: HTMLElement | null;
  children: ReactNode;
}) {
  return (
    <SettingsRouteHeaderTargetContext.Provider value={target}>
      {children}
    </SettingsRouteHeaderTargetContext.Provider>
  );
}

export function SettingsRouteHeader({ children }: { children: ReactNode }) {
  const target = useContext(SettingsRouteHeaderTargetContext);
  return target ? createPortal(children, target) : <>{children}</>;
}
