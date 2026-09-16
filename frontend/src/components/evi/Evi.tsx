import { useState } from "react";
import { motion } from "framer-motion";
import { useLocation } from "react-router-dom";
import { X } from "lucide-react";
import { useWorkspace, type EviState } from "../../store/workspace";
export function EviRobot({
  state = "idle",
  large = false,
}: {
  state?: EviState;
  large?: boolean;
}) {
  return (
    <div
      className={`evi-robot ${large ? "large" : ""} state-${state}`}
      role="img"
      aria-label={`Evi, ${state}`}
    >
      <svg viewBox="0 0 160 170" fill="none" aria-hidden="true">
        <defs>
          <linearGradient
            id={large ? "shell-lg" : "shell-sm"}
            x1="25"
            y1="25"
            x2="140"
            y2="140"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#fff" />
            <stop offset=".55" stopColor="#eeedf7" />
            <stop offset="1" stopColor="#b8bdd8" />
          </linearGradient>
        </defs>
        <ellipse
          className="evi-shadow"
          cx="80"
          cy="155"
          rx="34"
          ry="6"
          fill="#474768"
          opacity=".12"
        />
        <g className="evi-body">
          <path d="M80 30V19" stroke="#9699b8" strokeWidth="3" />
          <circle cx="80" cy="15" r="5" fill="#a3afa3" />
          <rect x="19" y="55" width="15" height="38" rx="7" fill="#bbbfd6" />
          <rect x="126" y="55" width="15" height="38" rx="7" fill="#bbbfd6" />
          <rect
            x="29"
            y="31"
            width="102"
            height="89"
            rx="33"
            fill={`url(#${large ? "shell-lg" : "shell-sm"})`}
            stroke="#c4c5d4"
          />
          <rect x="41" y="49" width="78" height="49" rx="20" fill="#303748" />
          <g
            className="evi-eyes"
            stroke="#dcf0ea"
            strokeWidth="6"
            strokeLinecap="round"
          >
            <path className="eye-left" d="M61 67V78" />
            <path className="eye-right" d="M98 67V78" />
          </g>
          <path
            className="evi-smile"
            d="M73 85Q80 89 87 85"
            stroke="#dcf0ea"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <path d="M60 120L65 134Q80 142 95 134L100 120" fill="#d6d8e8" />
          <path
            d="M70 126H90"
            stroke="#929cba"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle cx="80" cy="108" r="3" fill="#7f998e" />
        </g>
      </svg>
    </div>
  );
}
const guidance: Record<string, string> = {
  "/ask": "A good question is the beginning of an evidence trail.",
  "/knowledge": "Give me something to investigate. PDF and DOCX work here.",
  "/retrieval":
    "Follow the thread. Every returned detail comes from the backend.",
  "/guardrails": "Trust requires boundaries. Let’s see what was checked.",
  "/evaluations":
    "Let’s test how well your knowledge can answer questions about itself.",
  "/system": "A clear view of the dependencies behind your knowledge.",
};
export function EviGuide() {
  const { pathname } = useLocation();
  const w = useWorkspace();
  const [closed, setClosed] = useState(false);
  const text =
    w.operation === "query"
      ? "I’m waiting for your answer and its evidence trail."
      : w.operation === "upload"
        ? "Your document is being uploaded and processed."
        : w.operation === "evaluation"
          ? "This investigation takes a little longer. Results arrive together."
          : w.evi === "blocked"
            ? "This request was held by input protection. You can rephrase it."
            : w.evi === "error"
              ? "Something interrupted the request. The error details can help."
              : w.evi === "success"
                ? "The result is ready. Take a closer look at its evidence."
                : guidance[pathname];
  return (
    <motion.aside
      layout
      className={`evi-guide anchor-${pathname.slice(1)} ${closed ? "minimized" : ""}`}
      aria-label="Evi guidance"
    >
      <EviRobot state={closed ? "sleeping" : w.evi} />
      {!closed && (
        <div>
          <span className="eyebrow">EVI · YOUR EVIDENCE GUIDE</span>
          <p>{text}</p>
        </div>
      )}
      <button
        className="icon-button"
        aria-label={closed ? "Show Evi guidance" : "Minimize Evi guidance"}
        onClick={() => setClosed(!closed)}
      >
        {closed ? "✧" : <X size={15} />}
      </button>
    </motion.aside>
  );
}
