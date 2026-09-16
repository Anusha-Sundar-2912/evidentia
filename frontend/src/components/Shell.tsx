import { useEffect, useState } from "react";
import { NavLink, Link, Outlet, useLocation } from "react-router-dom";
import {
  MessageSquare,
  BookOpen,
  Route,
  ShieldCheck,
  FlaskConical,
  Activity,
  Menu,
  X,
  ArrowUpRight,
} from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { EviGuide } from "./evi/Evi";
import { useWorkspace } from "../store/workspace";
const nav = [
  ["/ask", "Ask", MessageSquare],
  ["/knowledge", "Knowledge", BookOpen],
  ["/retrieval", "Retrieval Lab", Route],
  ["/guardrails", "Guardrails", ShieldCheck],
  ["/evaluations", "Evaluations", FlaskConical],
  ["/system", "System", Activity],
] as const;
export function Shell() {
  const reduced = useReducedMotion();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const { operation } = useWorkspace();
  useEffect(() => {
    setOpen(false);
    window.scrollTo(0, 0);
    document.getElementById("workspace-main")?.focus();
  }, [pathname]);
  return (
    <div className={`app-shell atmosphere-${operation || "idle"}`}>
      <a className="skip-link" href="#workspace-main">
        Skip to content
      </a>
      <header className="mobile-header">
        <Link className="brand" to="/">
          <span className="brand-mark">e.</span>Evidentia
        </Link>
        <button
          className="icon-button"
          onClick={() => setOpen(!open)}
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
        >
          {open ? <X /> : <Menu />}
        </button>
      </header>
      {open && (
        <button
          className="nav-scrim"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      )}
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <Link className="brand" to="/">
          <span className="brand-mark">e.</span>Evidentia
        </Link>
        <div className="workspace-label">
          <span className="tiny-dot" /> KNOWLEDGE WORKSPACE
        </div>
        <nav aria-label="Primary navigation">
          {nav.map(([to, label, Icon]) => (
            <NavLink to={to} key={to}>
              <Icon size={18} />
              <span>{label}</span>
              {pathname === to && (
                <motion.span layoutId="nav-indicator" className="nav-dot" />
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-manifesto">
            <span>✳</span>
            <p>
              Every answer
              <br />
              deserves evidence.
            </p>
          </div>
          <Link to="/" className="sidebar-home">
            Back to the beginning <ArrowUpRight size={14} />
          </Link>
          <small>EVIDENTIA / V.01</small>
        </div>
      </aside>
      <div className="workspace-content">
        <div className="workspace-topline">
          <span>
            {nav.find((n) => n[0] === pathname)?.[1] || "Workspace"}
            <span className="breadcrumb-divider">/</span> Enterprise Knowledge
            Intelligence
          </span>
          <span className="topline-note">A clearer way to know.</span>
        </div>
        <main id="workspace-main" tabIndex={-1}>
          <motion.div
            key={pathname}
            initial={reduced ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22 }}
          >
            <Outlet />
          </motion.div>
          <EviGuide />
        </main>
        <footer className="workspace-footer">
          <span>Grounded in your knowledge.</span>
          <span>Designed for a closer look. ↗</span>
        </footer>
      </div>
    </div>
  );
}
