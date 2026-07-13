import { AlertTriangle, LoaderCircle, RefreshCw } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";

interface RouteDeliveryBoundaryProps {
  children: ReactNode;
}

interface RouteDeliveryBoundaryState {
  failed: boolean;
}

export class RouteDeliveryBoundary extends Component<RouteDeliveryBoundaryProps, RouteDeliveryBoundaryState> {
  state: RouteDeliveryBoundaryState = { failed: false };

  static getDerivedStateFromError(): RouteDeliveryBoundaryState {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Keep diagnostics useful without recording the token-bearing dashboard URL.
    console.error("Dashboard route chunk failed to load", {
      name: error.name,
      message: error.message,
      componentStack: info.componentStack,
    });
  }

  render() {
    if (this.state.failed) return <RouteLoadError />;
    return this.props.children;
  }
}

export function RouteLoading() {
  return (
    <section className="route-delivery-state panel-surface" role="status" data-testid="route-loading">
      <span className="route-delivery-icon is-loading" aria-hidden="true"><LoaderCircle size={24} /></span>
      <div>
        <span className="statistics-section-marker">Anki Study Report</span>
        <h1>Открываем раздел</h1>
        <p>Загружаем только необходимые для этой страницы компоненты.</p>
      </div>
    </section>
  );
}

export function RouteLoadError() {
  return (
    <section className="route-delivery-state is-error panel-surface" role="alert" data-testid="route-load-error">
      <span className="route-delivery-icon" aria-hidden="true"><AlertTriangle size={24} /></span>
      <div>
        <span className="statistics-section-marker">Раздел не загружен</span>
        <h1>Не удалось открыть страницу</h1>
        <p>Один из файлов dashboard недоступен. Перезагрузите страницу, чтобы запросить его снова.</p>
        <button className="primary-button" type="button" onClick={() => window.location.reload()}>
          <RefreshCw size={16} /> Перезагрузить dashboard
        </button>
      </div>
    </section>
  );
}
