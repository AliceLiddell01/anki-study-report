import { Suspense, useEffect, useRef, useState } from "react";
import AppLayout from "../layout/AppLayout";
import type { LoadState } from "../pages/HomePage";
import type { StudyReport } from "../types/report";
import { compatibilityRedirectForHash, getRouteFromHash, renderRoute } from "./router";
import { RouteDeliveryBoundary, RouteLoading } from "./RouteDeliveryBoundary";
import ProductNoticeCoordinator from "../components/ProductNoticeCoordinator";
import { durationBucket, emitTelemetryEvent, telemetryOccurredAt } from "../lib/telemetryApi";

function App() {
  const [route, setRoute] = useState(() => getRouteFromHash(window.location.hash));
  const [report, setReport] = useState<StudyReport | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [noticeOpenRequest, setNoticeOpenRequest] = useState(0);
  const startupStartedAt = useRef(performance.now());
  const startupEventSent = useRef(false);

  useEffect(() => {
    void emitTelemetryEvent({ eventCode: "dashboard.opened", occurredAt: telemetryOccurredAt() });
  }, []);

  useEffect(() => {
    const pageCode = telemetryPageCode(route);
    if (pageCode) void emitTelemetryEvent({ eventCode: "page.opened", pageCode, occurredAt: telemetryOccurredAt() });
  }, [route]);

  useEffect(() => {
    const updateRoute = () => {
      const redirect = compatibilityRedirectForHash(window.location.hash);
      if (redirect) {
        window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}#${redirect}`);
      }
      setRoute(getRouteFromHash(redirect ? `#${redirect}` : window.location.hash));
    };
    updateRoute();
    window.addEventListener("hashchange", updateRoute);
    return () => window.removeEventListener("hashchange", updateRoute);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const token = new URLSearchParams(window.location.search).get("token") || "";
    fetch(`/api/report?token=${encodeURIComponent(token)}`, { cache: "no-store" })
      .then((response) => {
        if (response.status === 403) {
          throw new Error("forbidden");
        }
        if (!response.ok) {
          throw new Error(response.status === 404 ? "empty" : "error");
        }
        return response.json() as Promise<StudyReport>;
      })
      .then((loadedReport) => {
        if (!cancelled) {
          setReport(loadedReport);
          setLoadState("ready");
          if (!startupEventSent.current) {
            startupEventSent.current = true;
            void emitTelemetryEvent({
              eventCode: "dashboard_startup.completed",
              resultCode: "success",
              durationBucket: durationBucket(performance.now() - startupStartedAt.current),
              occurredAt: telemetryOccurredAt(),
            });
          }
        }
      })
      .catch((error: Error) => {
        if (!cancelled && import.meta.env.DEV && error.message !== "forbidden") {
          import("../data/mockReport").then(({ mockReport }) => {
            if (!cancelled) {
              setReport(mockReport);
              setLoadState("ready");
            }
          });
          return;
        }
        if (!cancelled) {
          setReport(null);
          setLoadState(error.message === "empty" ? "empty" : error.message === "forbidden" ? "forbidden" : "error");
          if (!startupEventSent.current) {
            startupEventSent.current = true;
            void emitTelemetryEvent({
              eventCode: "dashboard_startup.completed",
              resultCode: "failed",
              durationBucket: durationBucket(performance.now() - startupStartedAt.current),
              occurredAt: telemetryOccurredAt(),
            });
            void emitTelemetryEvent({
              eventCode: "api_operation.failed",
              featureCode: "report_load",
              errorCode: error.message === "forbidden" ? "http_error" : "unavailable",
              occurredAt: telemetryOccurredAt(),
            });
          }
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const updateReport = (nextReport: StudyReport) => {
    setReport(nextReport);
    setLoadState("ready");
  };

  return (
    <>
      <div id="dashboard-app-shell">
        <AppLayout activeRoute={route} onOpenWhatsNew={() => setNoticeOpenRequest((value) => value + 1)}>
          <RouteDeliveryBoundary key={route}>
            <Suspense fallback={<RouteLoading />}>
              {renderRoute(route, report, loadState, updateReport, () => setNoticeOpenRequest((value) => value + 1))}
            </Suspense>
          </RouteDeliveryBoundary>
        </AppLayout>
      </div>
      <ProductNoticeCoordinator manualOpenSignal={noticeOpenRequest} />
    </>
  );
}

export default App;

export function telemetryPageCode(route: ReturnType<typeof getRouteFromHash>): string | null {
  if (route === "/notifications") return null;
  if (route.startsWith("/stats")) return "statistics";
  const pageCodes: Partial<Record<ReturnType<typeof getRouteFromHash>, string>> = {
    "/home": "home",
    "/calendar": "activity",
    "/decks": "decks",
    "/search": "search",
    "/cards": "cards",
    "/profile": "profile",
    "/actions": "tools",
    "/settings": "settings_report",
    "/settings/data": "settings_data",
    "/settings/privacy": "settings_privacy",
    "/settings/server": "settings_server",
    "/settings/sources": "settings_sources",
    "/settings/logs": "settings_logs",
  };
  return pageCodes[route] ?? "home";
}
