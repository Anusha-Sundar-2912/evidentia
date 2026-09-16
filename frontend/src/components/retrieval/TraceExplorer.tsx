import { useState } from "react";
import { motion } from "framer-motion";
import type { AskResponse } from "../../types/api";
import { ms, Badge, JsonDetails } from "../ui/Common";
import { updateWorkspace } from "../../store/workspace";
const stages = [
  {
    name: "The question",
    description: "The input that entered retrieval.",
    state: "curious",
  },
  {
    name: "A clearer question",
    description: "Conversation context and rewritten intent.",
    state: "thinking",
  },
  {
    name: "Search paths",
    description: "The subqueries used to retrieve evidence.",
    state: "searching",
  },
  {
    name: "Selected evidence",
    description: "Final selection in backend order.",
    state: "retrieving",
  },
  {
    name: "Focused context",
    description: "Context before and after compression.",
    state: "verifying",
  },
  {
    name: "The checks",
    description: "Returned citation and grounding validation.",
    state: "success",
  },
] as const;
export function TraceExplorer({ result }: { result: AskResponse }) {
  const [stage, setStage] = useState(0);
  const [order, setOrder] = useState<"rank" | "score">("rank");
  const t = result.trace;
  const chunks = [...t.selected_chunks].sort((a, b) =>
    order === "rank"
      ? a.rank - b.rank
      : (b.reranker_score ?? -Infinity) - (a.reranker_score ?? -Infinity),
  );
  return (
    <>
      <motion.div layoutId="answer-evidence" className="trace-question">
        <span className="eyebrow">FOLLOWING THE EVIDENCE FOR</span>
        <h2>{t.sanitized_query}</h2>
        <div className="inline-meta">
          <Badge>{t.selected_chunks.length} selected chunks</Badge>
          <span>{ms(t.latency_ms.total)} total</span>
        </div>
      </motion.div>
      <div className="trace-explorer">
        <nav className="trace-stages" aria-label="Retrieval stages">
          {stages.map((s, i) => (
            <button
              key={s.name}
              aria-pressed={i === stage}
              className={i === stage ? "active" : ""}
              onClick={() => {
                setStage(i);
                updateWorkspace({ evi: s.state });
              }}
            >
              <span className="stage-number">0{i + 1}</span>
              <span>
                <strong>{s.name}</strong>
                <small>{s.description}</small>
              </span>
            </button>
          ))}
        </nav>
        <section className="trace-detail panel" aria-live="polite">
          <span className="eyebrow">
            0{stage + 1} / {stages[stage].name}
          </span>
          {stage === 0 && (
            <>
              <h2>A question with a starting point.</h2>
              <p className="large-copy">{t.sanitized_query}</p>
              <p className="caption">
                For privacy, both “original” and sanitized query fields contain
                the backend’s sanitized text. The raw input is not exposed.
              </p>
              <JsonDetails
                value={{
                  original_query: t.original_query,
                  sanitized_query: t.sanitized_query,
                }}
              />
            </>
          )}
          {stage === 1 && (
            <>
              <h2>Intent, brought into focus.</h2>
              <blockquote>{t.rewritten_query}</blockquote>
              <p>
                Rewriting can make a follow-up question understandable on its
                own.
              </p>
              <Badge>{ms(t.latency_ms.conversation_rewrite)}</Badge>
            </>
          )}
          {stage === 2 && (
            <>
              <h2>More than one way to look.</h2>
              <div className="subqueries">
                {t.subqueries.map((q, i) => (
                  <div key={i}>
                    <span>{i + 1}</span>
                    <p>{q}</p>
                  </div>
                ))}
              </div>
              <p className="caption">
                Architecture: semantic retrieval and BM25 feed rank fusion and
                reranking. Intermediate candidate sets are not exposed.
              </p>
            </>
          )}
          {stage === 3 && (
            <>
              <h2>The evidence that made it through.</h2>
              <label className="sort-label">
                Display order
                <select
                  value={order}
                  onChange={(e) => {
                    setOrder(e.target.value as "rank" | "score");
                    updateWorkspace({ evi: "reranking" });
                  }}
                >
                  <option value="rank">Backend selection order</option>
                  <option value="score">Reranker score</option>
                </select>
              </label>
              <p className="caption">
                Scores are model ranking values, not probabilities. Sorting
                changes only this view.
              </p>
              <div className="ranked-chunks">
                {chunks.map((c) => (
                  <motion.article
                    layout
                    key={c.chunk_id}
                    className="ranked-chunk"
                  >
                    <span className="source-number">{c.rank}</span>
                    <div>
                      <strong>{c.filename}</strong>
                      <p>
                        {c.page_number !== null
                          ? `Page ${c.page_number}`
                          : "Page not reported"}
                      </p>
                      <small>{c.chunk_id}</small>
                    </div>
                    <Badge>{c.reranker_score?.toFixed(3) ?? "No score"}</Badge>
                  </motion.article>
                ))}
              </div>
              {!chunks.length && <p>No chunks were selected.</p>}
            </>
          )}
          {stage === 4 && (
            <>
              <h2>Less noise. More context.</h2>
              <div className="compression">
                <div>
                  <span>Before</span>
                  <strong>
                    {t.compression.original_context_chars.toLocaleString()}
                  </strong>
                  <small>characters</small>
                </div>
                <span>→</span>
                <div>
                  <span>After</span>
                  <strong>
                    {t.compression.compressed_context_chars.toLocaleString()}
                  </strong>
                  <small>characters</small>
                </div>
              </div>
              <p>
                {t.compression.chars_saved.toLocaleString()} characters saved ·
                ratio {t.compression.compression_ratio.toFixed(4)}
              </p>
              <p className="caption">
                Compressed passages themselves are not returned by this
                endpoint.
              </p>
            </>
          )}
          {stage === 5 && (
            <>
              <h2>Trust, with qualifications.</h2>
              <dl className="checks">
                <div>
                  <dt>Production validator</dt>
                  <dd>{result.validation.valid ? "Passed" : "Needs review"}</dd>
                </div>
                <div>
                  <dt>Citations present</dt>
                  <dd>{result.validation.citations_present ? "Yes" : "No"}</dd>
                </div>
                <div>
                  <dt>Invalid citation numbers</dt>
                  <dd>
                    {result.validation.invalid_citations.join(", ") || "None"}
                  </dd>
                </div>
                <div>
                  <dt>Groundedness heuristic</dt>
                  <dd>{result.validation.groundedness_score.toFixed(4)}</dd>
                </div>
              </dl>
              <p className="caption">
                Groundedness uses word overlap with cited evidence. A correct
                insufficient-evidence refusal is marked valid by the backend,
                even without citations.
              </p>
            </>
          )}
        </section>
      </div>
      <section className="panel latency-panel">
        <div className="section-label">
          <span>TIME ALONG THE TRAIL</span>
          <span>{ms(t.latency_ms.total)} total</span>
        </div>
        <p className="caption">
          Retrieval subtimings are nested within retrieval. Do not add every row
          to calculate total time.
        </p>
        <div className="latency-grid">
          {Object.entries(t.latency_ms)
            .filter(([k]) => k !== "total")
            .map(([key, value]) => (
              <div className="latency-row" key={key}>
                <span>{key.replaceAll("_", " ")}</span>
                <div className="timing-track">
                  <i
                    style={{
                      width: `${Math.min(100, (value / (t.latency_ms.total || 1)) * 100)}%`,
                    }}
                  />
                </div>
                <strong>{ms(value)}</strong>
              </div>
            ))}
        </div>
      </section>
    </>
  );
}
