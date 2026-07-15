import { Suspense, useEffect, useState } from "react";
import AppLayout from "../layout/AppLayout";
import type { LoadState } from "../pages/HomePage";
import type { StudyReport } from "../types/report";
import { compatibilityRedirectForHash, getRouteFromHash, renderRoute } from "./router";
import { RouteDeliveryBoundary, RouteLoading } from "./RouteDeliveryBoundary";
import ProductNoticeCoordinator from "../components/ProductNoticeCoordinator";

function App() {
  const [route, setRoute] = useState(() => getRouteFromHash(window.location.hash));
  const [report, setReport] = useState<StudyReport | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [noticeOpenRequest, setNoticeOpenRequest] = useState(0);

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
