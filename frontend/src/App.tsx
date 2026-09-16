import { lazy, Suspense, Component, type ReactNode } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { MotionConfig } from "framer-motion";
import { Shell } from "./components/Shell";
import { Pending } from "./components/ui/Common";
const Home = lazy(() => import("./pages/Home"));
const Ask = lazy(() => import("./pages/Ask"));
const Knowledge = lazy(() => import("./pages/Knowledge"));
const Retrieval = lazy(() => import("./pages/Retrieval"));
const Guardrails = lazy(() => import("./pages/Guardrails"));
const Evaluations = lazy(() => import("./pages/Evaluations"));
const System = lazy(() => import("./pages/System"));
class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <main className="fatal">
        <h1>The workspace couldn’t render.</h1>
        <p>
          Reload to start a fresh session. Upload receipts remain in this
          browser.
        </p>
        <button
          className="button primary"
          onClick={() => window.location.reload()}
        >
          Reload workspace
        </button>
      </main>
    ) : (
      this.props.children
    );
  }
}
export default function App() {
  return (
    <ErrorBoundary>
      <MotionConfig reducedMotion="user">
        <BrowserRouter>
          <Suspense
            fallback={
              <div className="route-loading">
                <Pending text="Opening the workspace" />
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<Home />} />
              <Route element={<Shell />}>
                <Route path="ask" element={<Ask />} />
                <Route path="knowledge" element={<Knowledge />} />
                <Route path="retrieval" element={<Retrieval />} />
                <Route path="guardrails" element={<Guardrails />} />
                <Route path="evaluations" element={<Evaluations />} />
                <Route path="system" element={<System />} />
                <Route
                  path="*"
                  element={
                    <div className="empty">
                      <h1>This trail ends here.</h1>
                      <Link to="/ask" className="button primary">
                        Return to Ask
                      </Link>
                    </div>
                  }
                />
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
      </MotionConfig>
    </ErrorBoundary>
  );
}
