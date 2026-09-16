import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowUp, Plus, SlidersHorizontal, BookOpen } from "lucide-react";
import { api, ApiError } from "../api/client";
import {
  useWorkspace,
  updateWorkspace,
  newInvestigation,
} from "../store/workspace";
import { useReceipts } from "../hooks/useReceipts";
import { Answer } from "../components/evidence/Answer";
import { ErrorNotice, Pending } from "../components/ui/Common";
export default function Ask() {
  const w = useWorkspace();
  const { receipts } = useReceipts();
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [filename, setFilename] = useState("");
  const mutation = useMutation({
    mutationKey: ["ask"],
    mutationFn: api.ask,
    onMutate: () =>
      updateWorkspace({
        taskError: undefined,
        operation: "query",
        evi: "thinking",
        result: undefined,
        blocked: undefined,
      }),
    onSuccess: (r) => {
      updateWorkspace({
        result: r,
        conversationId: r.conversation_id,
        evi: r.guardrails.output.safe ? "success" : "warning",
      });
      setQuery("");
    },
    onError: (e) =>
      updateWorkspace({
        taskError: { task: "query", error: e },
        evi: e instanceof ApiError && e.guardrails ? "blocked" : "error",
        blocked: e instanceof ApiError ? e.guardrails : undefined,
      }),
    onSettled: () => updateWorkspace({ operation: undefined }),
  });
  const busy = w.operation !== undefined;
  return (
    <>
      <header className="ask-top">
        <span className="eyebrow">THE INQUIRY WORKSPACE</span>
        <button
          className="button ghost"
          disabled={busy}
          onClick={() => {
            newInvestigation();
            mutation.reset();
            setQuery("");
          }}
        >
          <Plus size={16} /> New investigation
        </button>
      </header>
      <div className={`ask-intro ${w.result ? "compact" : ""}`}>
        <span className="little-star">✳</span>
        <h1>
          What would you like
          <br />
          to <em>verify?</em>
        </h1>
        <p>Ask a question. Find the evidence. See the whole story.</p>
      </div>
      <form
        className="question-box"
        onSubmit={(e) => {
          e.preventDefault();
          if (query.trim().length >= 2 && !busy)
            mutation.mutate({
              query: query.trim(),
              top_k: topK,
              conversation_id: w.conversationId,
              filters: filename ? { filenames: [filename] } : undefined,
            });
        }}
      >
        <label htmlFor="question" className="sr-only">
          Your question
        </label>
        <textarea
          id="question"
          placeholder="What can your knowledge tell us?"
          value={query}
          minLength={2}
          required
          disabled={busy}
          onFocus={() => {
            if (!busy) updateWorkspace({ evi: "listening" });
          }}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="question-toolbar">
          <span>
            <BookOpen size={15} />
            {filename || "All available knowledge"}
          </span>
          <button
            className="send-button"
            aria-label="Ask Evidentia"
            disabled={query.trim().length < 2 || busy}
          >
            <ArrowUp size={21} />
          </button>
        </div>
        <details className="query-options">
          <summary>
            <SlidersHorizontal size={14} /> Retrieval options
          </summary>
          <div className="form-row">
            <label>
              Evidence limit
              <input
                type="number"
                min={1}
                max={10}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
              />
            </label>
            <label>
              Exact filename (optional)
              <input
                list="known-files"
                placeholder="All documents"
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
              />
              <datalist id="known-files">
                {receipts.map((r) => (
                  <option key={r.id} value={r.filename} />
                ))}
              </datalist>
            </label>
          </div>
        </details>
      </form>
      <div className="question-footnote">
        <span>Evidence first. Always.</span>
        <span>
          {w.conversationId
            ? "Conversation context active"
            : "A fresh investigation"}
        </span>
      </div>
      {w.operation === "query" && <Pending />}
      <ErrorNotice
        error={
          w.taskError?.task === "query" ? w.taskError.error : mutation.error
        }
      />
      {w.result ? (
        <Answer result={w.result} />
      ) : (
        w.operation !== "query" &&
        !mutation.error &&
        !w.taskError && (
          <div className="ask-start">
            <div>
              <span className="eyebrow">START WITH WHAT YOU KNOW</span>
              <h3>Your next insight begins with a document.</h3>
              <p>
                Upload a report, policy or research paper, then ask a specific
                question about it.
              </p>
            </div>
            <Link to="/knowledge" className="button ghost">
              Open knowledge <span>↗</span>
            </Link>
          </div>
        )
      )}
    </>
  );
}
