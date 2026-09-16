import { Link } from "react-router-dom";
import { ArrowUpRight, FileText, ShieldCheck } from "lucide-react";
import { motion } from "framer-motion";
import type { AskResponse } from "../../types/api";
import { Badge, ms, percent } from "../ui/Common";
import { useWorkspace, updateWorkspace } from "../../store/workspace";
export function Answer({ result }: { result: AskResponse }) {
  const { selectedCitation } = useWorkspace();
  const refusal =
    result.answer.trim() ===
    "I could not find enough evidence in the available documents.";
  const safe = result.guardrails.output.safe;
  function select(n: number, scroll = false) {
    updateWorkspace({ selectedCitation: n });
    if (scroll)
      document
        .getElementById(`source-${n}`)
        ?.scrollIntoView({
          block: "nearest",
          behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
            .matches
            ? "instant"
            : "smooth",
        });
  }
  return (
    <motion.section
      layoutId="answer-evidence"
      className="answer-section"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="answer-meta">
        <span className="eyebrow">THE FINDING</span>
        <Badge
          tone={
            !safe
              ? "warn"
              : refusal
                ? "neutral"
                : result.validation.valid
                  ? "good"
                  : "warn"
          }
        >
          <ShieldCheck size={13} />
          {!safe
            ? "Privacy review required"
            : refusal
              ? "Insufficient evidence"
              : result.validation.valid
                ? "Validator passed"
                : "Review this answer"}
        </Badge>
        <span className="muted">{ms(result.trace.latency_ms.total)}</span>
      </div>
      <h2 className="query-title">{result.query}</h2>
      <div className="answer-prose">
        {safe ? (
          result.answer.split(/(\[\d+\]|【\d+】)/g).map((text, i) => {
            const match = text.match(/^(?:\[(\d+)\]|【(\d+)】)$/);
            const n = Number(match?.[1] || match?.[2]);
            return match &&
              result.citations.some((c) => c.source_number === n) ? (
              <button
                key={i}
                className={`citation ${selectedCitation === n ? "selected" : ""}`}
                onMouseEnter={() => select(n)}
                onFocus={() => select(n)}
                onClick={() => select(n, true)}
                aria-label={`View source ${n}`}
              >
                {text}
              </button>
            ) : (
              <span key={i}>{text}</span>
            );
          })
        ) : (
          <p className="notice warning">
            The backend flagged sensitive information in this answer. Its text
            is hidden here. See Guardrails for the returned privacy report.
          </p>
        )}
      </div>
      <div className="answer-actions">
        <Link className="button primary" to="/retrieval">
          Inspect evidence trail <ArrowUpRight size={16} />
        </Link>
        <Link className="text-link" to="/guardrails">
          View trust checks
        </Link>
      </div>
      {!refusal && (
        <p className="caption">
          Groundedness heuristic:{" "}
          {percent(result.validation.groundedness_score)} word overlap. This is
          not model confidence or a factual accuracy guarantee.
        </p>
      )}
      <div className="section-label">
        <span>SUPPORTING SOURCES</span>
        <span>{result.citations.length} cited</span>
      </div>
      {result.citations.length === 0 ? (
        <p className="muted">No supporting citations were returned.</p>
      ) : (
        <div className="source-grid">
          {result.citations.map((c) => (
            <article
              tabIndex={0}
              id={`source-${c.source_number}`}
              key={c.source_number}
              onFocus={() => select(c.source_number)}
              onMouseEnter={() => select(c.source_number)}
              className={`source-card ${selectedCitation === c.source_number ? "highlighted" : ""}`}
            >
              <span className="source-number">
                {String(c.source_number).padStart(2, "0")}
              </span>
              <FileText size={19} />
              <h3>{c.filename}</h3>
              <p>
                {c.page_number !== null
                  ? `Page ${c.page_number}`
                  : "Page not reported"}
              </p>
              <small>Chunk {c.chunk_id}</small>
              <p className="caption">
                Passage text is not included in the answer response.
              </p>
            </article>
          ))}
        </div>
      )}
    </motion.section>
  );
}
